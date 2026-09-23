# 🐘 PostgreSQL Internals & High-Scale Optimization: The Senior Engineer's Handbook
### *From Disk Pages and TOASTing to GIN Mechanics, Query Plans, and Scaling 100 Million JSONB Rows*

---

## 📑 Table of Contents
1. [Physical Storage & The Anatomy of an 8KB Page Buffer](#1-physical-storage--the-8kb-page)
2. [TOASTing Demystified (The Oversized-Attribute Storage Technique)](#2-toasting-demystified)
   - [Page Thresholds & Chunking](#page-thresholds--chunking)
   - [The 4 Storage Strategies (`PLAIN`, `EXTENDED`, `EXTERNAL`, `MAIN`)](#the-4-storage-strategies)
   - [Compression: PGLZ vs. LZ4](#compression-pglz-vs-lz4)
   - [The TOAST Read/Write Traps](#the-toast-performance-traps)
3. [EXPLAIN Deep-Dive: Reading the Mind of the Query Planner](#3-explain-deep-dive)
   - [Demystifying the Cost Formula (`cost=startup..total`)](#the-cost-formula-demystified)
   - [Why `EXPLAIN (ANALYZE, BUFFERS)` is Mandatory](#why-explain-analyze-buffers-is-mandatory)
   - [The 4 Scan Engines: Seq, Index, Index-Only, Bitmap](#the-4-scan-engines)
   - [The 3 Join Algorithms: Nested Loop, Hash Join, Merge Join](#the-3-join-algorithms)
4. [GIN Indexes & JSONB Internals](#4-gin-indexes--jsonb-internals)
   - [JSON vs. JSONB (Physical Layout)](#json-vs-jsonb-physical-layout)
   - [How GIN Works Under the Hood (Posting Lists & Trees)](#how-gin-works-under-the-hood)
   - [`jsonb_ops` vs. `jsonb_path_ops`](#jsonb_ops-vs-jsonb_path_ops)
   - [The GIN `fastupdate` Buffer Trade-off](#the-gin-fastupdate-buffer)
5. [The 100-Million Row Blueprint (2KB–20KB JSON Payloads)](#5-the-100-million-row-blueprint)
   - [The Physical Math & The RAM Trap](#the-physical-math--the-ram-trap)
   - [Architectural Pillar 1: Declarative Partitioning](#pillar-1-declarative-partitioning)
   - [Architectural Pillar 2: Storage Strategy & LZ4 Compression](#pillar-2-storage-strategy--lz4-compression)
   - [Architectural Pillar 3: Zero-TOAST Query Discipline](#pillar-3-zero-toast-query-discipline)
   - [Architectural Pillar 4: Surgical Indexing](#pillar-4-surgical-indexing)
   - [Architectural Pillar 5: Autovacuum Tuning for Heavy JSON Tables](#pillar-5-autovacuum-tuning-for-heavy-json-tables)
6. [Complete Production SQL Blueprint (Copy-Paste Ready)](#6-complete-production-sql-blueprint)
7. [Master PostgreSQL Internals Reference Cheat Sheet](#7-master-reference-cheat-sheet)

---

<a id="1-physical-storage--the-8kb-page"></a>
## 🧱 1. Physical Storage & The Anatomy of an 8KB Page Buffer

PostgreSQL does not read or write single rows from disk. Everything moves in **8 Kilobyte Pages** (also called Blocks).

When Postgres loads a table into memory (`shared_buffers`), it loads 8KB pages. When it writes to WAL or flushes dirty buffers to disk, it does so in 8KB pages.

### Inside an 8KB Page:

```
┌────────────────────────────────────────────────────────────────────────┐
│ PageHeaderData (24 bytes)                                              │
│ [ LSN | Checksum | Flags | Lower Offset | Upper Offset | Special ]     │
├────────────────────────────────────────────────────────────────────────┤
│ Line Pointers / ItemIds (Array of 4-byte pointers: offset + length)    │
│ [ ItemId 1 ] ──▶ points to Tuple 1 at bottom                           │
│ [ ItemId 2 ] ──▶ points to Tuple 2                                     │
│ [ ItemId 3 ] ──▶ points to Tuple 3                                     │
│                     ▼                                                  │
│             (Free Space Grows Downward)                                │
│                                                                        │
│             (Free Space Grows Upward)                                  │
│                     ▲                                                  │
├────────────────────────────────────────────────────────────────────────┤
│ Tuple Data (Rows stored from the bottom of the page upward)            │
│ [ HeapTupleHeaderData (23 bytes: xmin, xmax, t_ctid, infomask) ]       │
│ [ Tuple 3 Data ]                                                       │
│ [ Tuple 2 Data ]                                                       │
│ [ Tuple 1 Data ]                                                       │
├────────────────────────────────────────────────────────────────────────┤
│ Special Space (Index-specific page data, if applicable)                │
└────────────────────────────────────────────────────────────────────────┘
```

### The Crucial Takeaway:
* A single row's address in Postgres is its **`ctid`** (e.g., `(page_number, item_number)`: `(42, 3)` means Page 42, Line Pointer 3).
* Because a page is strictly **8192 bytes**, and Postgres requires that at least **4 rows** must fit in a single page under normal conditions, what happens when a single row has a 10KB JSON or text column?
* **Answer:** It triggers **TOAST**.

---

<a id="2-toasting-demystified"></a>
## 🍞 2. TOASTing Demystified (The Oversized-Attribute Storage Technique)

**TOAST** is PostgreSQL's built-in mechanism to store large attributes without violating the 8KB page boundary.

### Page Thresholds & Chunking
* **`TOAST_TUPLE_THRESHOLD` (Default: ~2KB / 2048 bytes):** If a row's total size exceeds ~2KB, Postgres triggers the TOAST mechanism.
* **`TOAST_TUPLE_TARGET` (Default: ~2KB):** Postgres attempts to compress or move columns out-of-line until the main table row drops below this target.

```
WHAT HAPPENS WHEN YOU INSERT A 15 KB JSON OBJECT:

1. COMPRESSION PHASE:
   Postgres attempts to compress the 15 KB JSON in memory.
   • If compressed size < 2 KB: It stays INLINE in the normal 8KB page.
   • If compressed size >= 2 KB: It moves to the OUT-OF-LINE phase.

2. OUT-OF-LINE PHASE:
   Postgres creates a hidden auxiliary table: "pg_toast_<table_oid>".
   • The 15 KB payload is chopped into ~2 KB chunks.
   • Stored as individual rows in the toast table:
     - chunk_id (OID)
     - chunk_seq (0, 1, 2, 3...)
     - chunk_data (bytea up to ~2000 bytes)

3. POINTER REPLACEMENT:
   In the main table, the 15 KB column is replaced by an 18-byte TOAST Pointer!
   [ va_header | toast_table_oid | chunk_id | raw_size | compressed_size ]
```

---

### The 4 Storage Strategies

Every column type has an internal storage strategy. You can inspect it via `\d+ table_name` or `SELECT attname, attstorage FROM pg_attribute`:

| Strategy | Description | Allows Compression? | Allows Out-of-Line TOAST? | Best Used For |
| :--- | :--- | :---: | :---: | :--- |
| **`PLAIN`** | Must fit inline in the main 8KB page. No compression, no out-of-line storage. | ❌ No | ❌ No | Fixed types (`int`, `bigint`, `uuid`, `timestamp`). |
| **`EXTENDED`** *(Default for JSONB/TEXT)* | Tries compression first. If still too big, moves out-of-line to TOAST table. | ✅ Yes | ✅ Yes | Default for large text, JSON, JSONB. |
| **`EXTERNAL`** | Moves out-of-line **without compression**. | ❌ No | ✅ Yes | Already compressed data (e.g. JPEGs, ZIPs, or pre-compressed JSON). |
| **`MAIN`** | Tries compression first, but avoids out-of-line storage unless strictly necessary. | ✅ Yes | ⚠️ Last Resort | Fast inline access for columns that hover around 1-3KB. |

#### Changing Storage Strategy via SQL:
```sql
ALTER TABLE events ALTER COLUMN payload SET STORAGE EXTERNAL;
```

---

### Compression: PGLZ vs. LZ4 (PostgreSQL 14+)

* **`pglz` (Default legacy engine):** Built-in to Postgres. Good compression ratio, but CPU-intensive during decompression.
* **`lz4` (Available from Postgres 14+):** **2x to 4x faster decompression** with almost the same compression ratio.

> 🚀 **Senior Optimization Tip:** For heavy JSONB workloads, always switch column compression to LZ4!
```sql
ALTER TABLE events ALTER COLUMN payload SET COMPRESSION lz4;
```

---

### The TOAST Performance Traps

1. **The `SELECT *` Penalty:**  
   If your table has 5 columns and column 5 is a 20KB TOASTed JSON, running `SELECT id, status FROM events` reads **only the main table's 8KB pages**. Postgres **never opens the TOAST table**!  
   Running `SELECT *` forces Postgres to make random read I/O calls to `pg_toast` for every single row!
2. **The Re-Toasting on UPDATE Trap:**  
   If you update a non-TOASTed column (`UPDATE events SET status = 'DONE' WHERE id = 1`), Postgres is smart: it creates a new heap row pointing to the **existing TOAST pointer**. It does **not** duplicate the 20KB payload.  
   However, if you touch or re-assign the JSON column (`UPDATE events SET payload = jsonb_set(...)`), Postgres must decompress, modify, re-compress, and write brand new chunks to the TOAST table!

---

<a id="3-explain-deep-dive"></a>
## 🔍 3. EXPLAIN Deep-Dive: Reading the Mind of the Query Planner

When you execute a query, the PostgreSQL **Query Optimizer (Planner)** evaluates thousands of execution paths and picks the one with the lowest calculated **cost**.

### The Cost Formula Demystified

When you run `EXPLAIN SELECT ...`, you see:
```text
Seq Scan on users  (cost=0.00..35.50 rows=1000 width=32)
```

* **`cost=0.00` (Startup Cost):** The estimated cost to fetch the **very first row**. (For an un-ordered Seq Scan, this is `0.00`. For an Index Scan or Hash Join, it's higher because the index must be traversed or the hash table built first).
* **`cost=35.50` (Total Cost):** The estimated cost to return **all rows**.
* **`rows=1000`:** Estimated rows returned based on `pg_statistic`.
* **`width=32`:** Estimated average byte width of the returned columns.

#### What is 1.0 "Cost"?
PostgreSQL measures cost in arbitrary units calibrated to I/O and CPU:
* `seq_page_cost = 1.0`: The cost of reading 1 sequential 8KB page from disk.
* `random_page_cost = 4.0` (Default, change to `1.1` for NVMe/SSDs!): Cost of reading 1 random 8KB page.
* `cpu_tuple_cost = 0.01`: Cost of processing 1 row.
* `cpu_operator_cost = 0.0025`: Cost of evaluating 1 `WHERE` condition.

---

### Why `EXPLAIN (ANALYZE, BUFFERS)` is Mandatory

Never use plain `EXPLAIN` to diagnose performance. Plain `EXPLAIN` only shows estimates.  
`EXPLAIN (ANALYZE, BUFFERS)` actually runs the query and shows **hardware reality**:

```text
Bitmap Heap Scan on events  (cost=12.50..850.20 rows=500 width=64) (actual time=0.450..2.120 rows=480 loops=1)
  Buffers: shared hit=120 read=14 dirtied=2 written=0
```

#### How to Read the Buffers Line:
* **`shared hit=120`:** 120 pages (8KB × 120 = 960 KB) were found directly in RAM (`shared_buffers`). Sub-microsecond access!
* **`read=14`:** 14 pages were not in Postgres RAM. Postgres had to issue an OS disk read (I/O latency).
* **`dirtied=2`:** 2 pages were modified in memory by this query.
* **`written=0`:** Pages flushed directly to disk.

---

### The 4 Scan Engines

```
1. SEQUENTIAL SCAN (Seq Scan)
   • Reads every single 8KB page of the table from start to finish.
   • Optimal when reading > 15-20% of the entire table.

2. INDEX SCAN
   • Reads the B-Tree index to find row pointers (ctid: page, line).
   • Jumps to the table heap page to fetch row data.
   • Fast for small row counts (< 5%), but causes random I/O for large row counts.

3. INDEX-ONLY SCAN (The Holy Grail)
   • All requested columns are found inside the index itself (Covering Index / INCLUDE).
   • NEVER visits the table heap, IF the page is marked clean in the Visibility Map!

4. BITMAP INDEX SCAN + BITMAP HEAP SCAN
   • Step A (Bitmap Index Scan): Scans the index and builds a binary bitmap of physical page numbers.
   • Step B (Bitmap Heap Scan): Reads the table heap sequentially based on the sorted bitmap!
   • Eliminates random I/O; optimal when fetching between 5% and 20% of rows.
```

---

### The 3 Join Algorithms

When joining Table A and Table B:

```
                                    POSTGRES JOIN ENGINES
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. NESTED LOOP                                                                         │
│    For each row in Outer Table A:                                                      │
│        Search for matching rows in Inner Table B (via Index).                          │
│    • Best when Outer table is tiny (< 100 rows) and Inner table has a fast index!      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. HASH JOIN                                                                           │
│    1. Reads Table A into memory and builds an in-memory Hash Table (keyed on join ID). │
│    2. Streams Table B row-by-row and probes the Hash Table for instant matches.        │
│    • Best for medium-to-large un-indexed tables that fit in work_mem!                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. MERGE JOIN                                                                          │
│    1. Both tables must be sorted on the join key (or read via ordered B-Trees).        │
│    2. Zips through both tables in parallel like two zippers coming together.           │
│    • Best for massive tables where both are already ordered by the join key!           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

<a id="4-gin-indexes--jsonb-internals"></a>
## 🌲 4. GIN Indexes & JSONB Internals

### JSON vs. JSONB (Physical Layout)
* **`JSON`:** Stored as exact plain text (including whitespace and duplicate keys). Postgres must parse the text on **every single query**.
* **`JSONB`:** Deconstructed binary format. Whitespace is stripped, duplicate keys are dropped, and keys are sorted alphabetically.

```
JSONB INTERNAL BINARY LAYOUT:
[ 4-byte Header (Container Info & Element Count) ]
[ JEntry Array (Offset and data type flags for every key/value) ]
[ Keys Table (Alphabetically sorted, enabling binary search!) ]
[ Values Table (Raw binary values) ]
```

Because keys are sorted in binary, Postgres can look up `payload->'user'->'id'` via binary search without scanning the entire text!

---

### How GIN Works Under the Hood

A **GIN (Generalized Inverted Index)** is an "index of search terms", similar to a book index or a search engine like Lucene.

Instead of mapping `Row ──▶ Values`, GIN maps `Key/Value ──▶ List of Row IDs (TIDs)`.

```
                    GIN (GENERALIZED INVERTED INDEX) LAYOUT
                      ┌─────────────────────────────────┐
                      │    Entry Tree (B-Tree of Keys)  │
                      └────────────────┬────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
   "status: 'active'"           "country: 'US'"              "role: 'admin'"
         │                             │                             │
         ▼                             ▼                             ▼
   Posting List                  Posting List                  Posting Tree
   [ ctid (1,4), (1,9) ]         [ ctid (1,4), (2,1) ]         (If > 1 page of TIDs,
                                                                becomes an internal
                                                                sub B-Tree!)
```

When you query `WHERE payload @> '{"status": "active", "country": "US"}'`:
1. GIN looks up the posting list for `"status: 'active'"`: `[(1,4), (1,9)]`.
2. GIN looks up the posting list for `"country: 'US'"`: `[(1,4), (2,1)]`.
3. GIN performs a **Bitwise AND intersection** in memory $\rightarrow$ Result: `(1,4)`.
4. Jumps straight to Page 1, Row 4!

---

### `jsonb_ops` vs. `jsonb_path_ops`

When creating a GIN index on a JSONB column, you have two operator classes:

| Feature | `jsonb_ops` (Default) | `jsonb_path_ops` (Optimized) |
| :--- | :--- | :--- |
| **Indexing Strategy** | Indexes **every separate key and value**. | Hashes the **entire root-to-leaf path** into a single 32-bit hash! |
| **Supported Operators** | `@>`, `?` (key exists), `?\|` (any key exists), `?&` (all keys exist) | **Only `@>`** (containment queries) |
| **Index Size** | Large (often 50% to 100% of table size). | **Up to 3x smaller!** |
| **Search Speed** | Fast for key checks. | **2x to 3x faster** for containment `@>` searches! |

> 🚀 **Senior Optimization Tip:** If you only query JSONB using the containment operator `@>`, **always use `jsonb_path_ops`**!

```sql
-- High-performance, compact GIN index
CREATE INDEX idx_events_payload ON events USING gin (payload jsonb_path_ops);
```

---

### The GIN `fastupdate` Buffer

Building a GIN index in real time on high-throughput inserts is expensive because every insert adds entries to hundreds of posting lists.
* By default, GIN uses a **`fastupdate` pending list** in memory.
* Inserts are written to a temporary flat list (fast).
* When the pending list exceeds `gin_pending_list_limit` (default: 4MB), or when `VACUUM` runs, the list is cleaned and merged into the main GIN tree.
* **The Downside:** If the pending list is full, an ad-hoc query will stall while flushing it! For predictable low-latency systems with heavy writes, set `WITH (fastupdate = off)` or tune `gin_pending_list_limit`.

---

<a id="5-the-100-million-row-blueprint"></a>
## 🚀 5. The 100-Million Row Blueprint (2KB–20KB JSON Payloads)

### The Physical Math & The RAM Trap
Let's do the engineering calculations:
* **Rows:** 100,000,000
* **Average Payload:** 10 KB (TOASTed)
* **Raw Table Size:** $100{,}000{,}000 \times 10\text{ KB} \approx \mathbf{1\text{ Terabyte}}$!
* **A standard GIN index on full payloads:** $\sim \mathbf{300\text{ GB}}$!

**Why Naive Postgres Dies at This Scale:**
1. **Cache Thrashing:** Your server has 64GB or 128GB of RAM. A 1TB table cannot fit in `shared_buffers`. Every query causes disk reads!
2. **Autovacuum Freezes:** Vacuuming a 1TB monolithic table takes 12 hours, consuming I/O and locking pages.
3. **Bloat:** Updating rows creates dead tuples. A 1TB table with 20% bloat wastes 200 GB of NVMe disk.

Here is the architectural blueprint to make 100M rows with 2-20KB JSON fly at sub-millisecond speeds:

---

### Pillar 1: Declarative Partitioning
**Never store 100 million heavy rows in a single table.**  
Partition by Date (Range) or Tenant/Region (List/Hash):

```
                                  MASTER TABLE (events)
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               ▼                            ▼                            ▼
       events_2024_q1               events_2024_q2               events_2024_q3
         (25M rows)                   (25M rows)                   (25M rows)
```

**Why Partitioning Saves You:**
* **Partition Pruning:** When a query specifies `WHERE created_at >= '2024-07-01'`, Postgres ignores Q1 and Q2 completely.
* **Working Set Fits in RAM:** The active quarter's table and indexes (~200 GB) can fit in OS cache and `shared_buffers`!
* **Independent Vacuuming:** Autovacuum processes smaller 25M-row partitions in parallel without blocking the whole system.

---

### Pillar 2: Storage Strategy & LZ4 Compression
* By default, Postgres tries to keep things in the main table until 2KB. For heavy JSON, force TOASTing and set compression to **LZ4**:

```sql
-- Use fast LZ4 compression
ALTER TABLE events ALTER COLUMN payload SET COMPRESSION lz4;

-- Tune toast threshold so main table stays lean
ALTER TABLE events ALTER COLUMN payload SET STORAGE EXTENDED;
```

---

### Pillar 3: Zero-TOAST Query Discipline
The main table contains only small scalar columns (`id`, `created_at`, `event_type`, `user_id`, and the 18-byte TOAST pointer).
* A query like:
  ```sql
  SELECT id, event_type, created_at FROM events WHERE created_at > now() - interval '1 day';
  ```
  **Never touches the 1TB TOAST table!** It reads only the compact main table.
* **Strict Rule:** Never write `SELECT *`. Only select `payload` when displaying the full JSON to the end-user.

---

### Pillar 4: Surgical Indexing (Do NOT Index the Entire JSON Object!)
A full GIN index on 100M rows with 20KB objects will consume 300GB+ of RAM and disk.

Instead, extract the 2 or 3 keys you actually search on, and build **B-Tree Expression Indexes**:

```sql
-- ❌ BAD: 300 GB GIN index covering every arbitrary JSON field
CREATE INDEX idx_bad ON events USING gin (payload);

-- ✅ GOOD: 2 GB B-Tree index on the exact field you query!
CREATE INDEX idx_surgical_user_id ON events (((payload->>'user_id')::bigint));

-- ✅ GOOD: Partial GIN index only for active events!
CREATE INDEX idx_partial_active ON events USING gin (payload jsonb_path_ops)
WHERE status = 'ACTIVE';
```

---

### Pillar 5: Autovacuum Tuning for Heavy JSON Tables
The default Postgres autovacuum settings are designed for small 10MB tables from 2005. For 100M rows, autovacuum will run too late and choke I/O:

```sql
-- Tune specific table autovacuum aggressiveness
ALTER TABLE events SET (
    autovacuum_vacuum_scale_factor = 0.05,       -- Trigger vacuum after 5% rows change (default is 20%)
    autovacuum_vacuum_cost_limit = 2000,         -- Give vacuum 10x more I/O budget
    autovacuum_vacuum_cost_delay = 2             -- Lower sleep delay between vacuum chunks
);
```

---

<a id="6-complete-production-sql-blueprint"></a>
## 💻 6. Complete Production SQL Blueprint (Copy-Paste Ready)

Here is the complete, battle-tested schema combining Partitioning, LZ4 Compression, TOAST optimization, and Surgical Indexing for 100M rows:

```sql
-- ============================================================================
-- 1. PARENT PARTITIONED TABLE
-- ============================================================================
CREATE TABLE events (
    event_id        BIGINT GENERATED ALWAYS AS IDENTITY,
    tenant_id       INT NOT NULL,
    event_type      VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    payload         JSONB NOT NULL,
    CONSTRAINT pk_events PRIMARY KEY (created_at, event_id)
) PARTITION BY RANGE (created_at);

-- ============================================================================
-- 2. PARTITION DEFINITION (Monthly or Quarterly Partitions)
-- ============================================================================
CREATE TABLE events_2024_m01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01 00:00:00+00') TO ('2024-02-01 00:00:00+00');

CREATE TABLE events_2024_m02 PARTITION OF events
    FOR VALUES FROM ('2024-02-01 00:00:00+00') TO ('2024-03-01 00:00:00+00');

-- ============================================================================
-- 3. STORAGE & COMPRESSION TUNING (PostgreSQL 14+)
-- ============================================================================
-- Set compression to LZ4 for 3x faster decompression
ALTER TABLE events ALTER COLUMN payload SET COMPRESSION lz4;

-- Ensure EXTENDED storage (compress, then move out-of-line to TOAST)
ALTER TABLE events ALTER COLUMN payload SET STORAGE EXTENDED;

-- ============================================================================
-- 4. SURGICAL INDEXES (High performance, low footprint)
-- ============================================================================
-- A. Standard B-Tree for time-series range pruning
CREATE INDEX idx_events_tenant_time ON events (tenant_id, created_at DESC);

-- B. B-Tree Expression Index on a critical extracted JSON field
CREATE INDEX idx_events_customer_id ON events (((payload->'customer'->>'id')::bigint));

-- C. Compact GIN Path-Ops Index (ONLY for containment queries, avoiding full GIN bloat)
CREATE INDEX idx_events_payload_path ON events USING gin (payload jsonb_path_ops);

-- ============================================================================
-- 5. AUTOVACUUM HARDENING
-- ============================================================================
ALTER TABLE events SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_vacuum_cost_limit = 2000,
    autovacuum_vacuum_cost_delay = 2
);

-- ============================================================================
-- 6. VERIFYING QUERY PLANS & BUFFER EFFICIENCY
-- ============================================================================
-- Test query using EXPLAIN (ANALYZE, BUFFERS)
-- Notice: Partition Pruning will skip unused months, and only hit RAM buffers!
EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE)
SELECT 
    event_id, 
    event_type, 
    payload->'customer'->>'name' AS customer_name
FROM events
WHERE created_at >= '2024-01-15' AND created_at < '2024-01-20'
  AND (payload->'customer'->>'id')::bigint = 987654;
```

---

<a id="7-master-reference-cheat-sheet"></a>
## 📊 7. Master PostgreSQL Internals Reference Cheat Sheet

| Mechanism | What It Does (Simple English) | Senior Optimization Rule |
| :--- | :--- | :--- |
| **8KB Page Buffer** | The atomic unit of I/O in Postgres memory and disk. | Tune `shared_buffers` to 25% of server RAM to maximize page hits. |
| **TOAST** | Moves attributes $> 2\text{ KB}$ out-of-line into an auxiliary table. | Never do `SELECT *` on TOASTed tables. Only select non-TOAST columns to skip disk I/O. |
| **`EXTENDED` Storage** | Tries compression; moves out-of-line if still $> 2\text{ KB}$. | Default for JSONB and TEXT. |
| **`LZ4` Compression** | Modern compression engine available in Postgres 14+. | Always set `COMPRESSION lz4` for JSONB columns to double query decompression speed. |
| **`EXPLAIN BUFFERS`** | Shows exact RAM buffer cache hits vs physical disk reads. | Look at `Buffers: shared hit vs read`. If `read` is high, your working set exceeds RAM! |
| **Index-Only Scan** | Retrieves data directly from B-Tree without touching table heap. | Ensure all queried columns are in the index; keep Visibility Map clean via vacuuming. |
| **Bitmap Scan** | Builds a sorted bitmap of page IDs before fetching data. | Bridges the gap between Index Scan and Seq Scan for medium-size filters (5-20% of rows). |
| **`jsonb_ops`** | GIN operator class indexing all keys and values separately. | Avoid on massive tables; produces huge index bloat. |
| **`jsonb_path_ops`** | GIN operator class hashing root-to-leaf paths. | **3x smaller, 2x faster**; use whenever queries only use the containment operator `@>`. |
| **B-Tree Expression Index**| Indexes a specific extracted JSON key (`(payload->>'id')`). | Best strategy for 100M rows: 100x smaller and 10x faster than a full GIN index! |
| **Declarative Partitioning**| Slices a 100M-row table into smaller 25M-row chunks. | Enables partition pruning; ensures the active working set fits in `shared_buffers`. |

---

### 🎓 Summary for Senior Engineering & System Design Interviews
> *"When scaling PostgreSQL to 100 million rows with 2-20KB JSONB documents, the secret is **avoiding unneeded I/O**: We use **declarative range partitioning** to keep the active working set in `shared_buffers`, configure **`STORAGE EXTENDED` with `lz4` compression** to accelerate TOAST decompression, maintain **Zero-TOAST projection discipline** (never `SELECT *`), and replace monolithic GIN indexes with **compact `jsonb_path_ops`** or **surgical B-Tree expression indexes** on hot extracted keys."*
