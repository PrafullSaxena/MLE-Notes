# 🕵️ Demystifying PostgreSQL EXPLAIN: The In-Depth Field Guide
### *How to Read, Interpret, and Diagnose Query Execution Plans Like a Database Engine*

---

## 📑 Table of Contents
1. [The Big Picture: How Postgres Executes a Query](#1-the-big-picture)
2. [The Execution Model: The Volcano Iterator (Inside-Out Flow)](#2-the-volcano-iterator-model)
3. [The Flavors of EXPLAIN: Syntax, Flags & Safety](#3-the-flavors-of-explain)
4. [Anatomy of a Plan Line: Decoding Every Number & String](#4-anatomy-of-a-plan-line)
   - [Cost Units & Formulas (`cost=startup..total`)](#cost-units--formulas)
   - [Rows & The Estimation Ratio (`rows` vs. `actual rows`)](#rows--the-estimation-ratio)
   - [Loops & Actual Time Multiplication](#loops--actual-time-multiplication)
5. [The Buffers Line: The Absolute Truth of I/O](#5-the-buffers-line)
6. [Complete Catalog of Plan Nodes](#6-complete-catalog-of-plan-nodes)
   - [Scan Nodes (Seq, Index, Index-Only, Bitmap)](#scan-nodes)
   - [Join Nodes (Nested Loop, Hash Join, Merge Join)](#join-nodes)
   - [Sort, Aggregate, and Materialize Nodes](#sort-aggregate--materialize-nodes)
   - [Parallel Query Nodes (Gather & Workers)](#parallel-query-nodes)
7. [4 Real-World Case Studies (Annotated Dissections)](#7-four-real-world-case-studies)
   - [Case 1: The Healthy Index-Only Scan](#case-1-the-healthy-index-only-scan)
   - [Case 2: The Stale Statistics Trap (Nested Loop Disaster)](#case-2-the-stale-statistics-trap)
   - [Case 3: Memory Spills to Disk (`work_mem` Starvation)](#case-3-memory-spills-to-disk)
   - [Case 4: The Filter Drop Trap (Late Filtering)](#case-4-the-filter-drop-trap)
8. [The Senior Engineer's 6-Step EXPLAIN Diagnostic Checklist](#8-the-6-step-diagnostic-checklist)
9. [Master EXPLAIN Quick Reference Table](#9-master-reference-table)

---

<a id="1-the-big-picture"></a>
## 🌍 1. The Big Picture: How Postgres Executes a Query

When you send an SQL string to PostgreSQL, it goes through four distinct phases before any rows reach your terminal:

```
[ SQL Query String ]
        │
        ▼
 1. PARSER           ──▶ Validates SQL syntax and converts to Parse Tree.
        │
        ▼
 2. REWRITER         ──▶ Applies system rules and expands Views.
        │
        ▼
 3. OPTIMIZER        ──▶ THE BRAIN: Evaluates combinations of joins, scans,
    (PLANNER)            and indexes using database statistics (pg_statistic).
                         Picks the plan with the lowest estimated COST.
        │
        ▼
 4. EXECUTOR         ──▶ THE MUSCLE: Traverses the plan tree and physically
                         fetches/computes data from RAM (shared_buffers) or disk.
```

* **`EXPLAIN`** asks the **Planner** to show you the blueprint it formulated.
* **`EXPLAIN ANALYZE`** asks the **Executor** to physically run the blueprint, timing every step and counting actual rows.

---

<a id="2-the-volcano-iterator-model"></a>
## 🌋 2. The Volcano Iterator Model (Inside-Out Flow)

PostgreSQL executes query plans using the classic **Volcano Iterator Model** (also called the Pipeline Model).

### The Golden Rule of Reading Plans:
> **Postgres plans are trees. Execution flows from the deepest leaves UPWARD and from INSIDE-OUT.**

Every node in an EXPLAIN output implements three fundamental methods:
1. `Init()`: Prepares the node (allocates memory, opens indexes).
2. `Next()`: Pulls **one tuple at a time** (or a batch of tuples) from child nodes.
3. `Close()`: Cleans up memory.

### Visualizing the Tree:

```text
Sort  (cost=150.00..152.00 ...)                         [TOP NODE: Delivers final output]
  ->  Hash Join  (cost=20.00..120.00 ...)               [MIDDLE: Joins rows as they arrive]
        Hash Cond: (orders.user_id = users.id)
        ->  Seq Scan on orders  (...)                   [PULLS from orders stream]
        ->  Hash  (...)                                 [BUILDS in-memory hash table]
              ->  Index Scan on users  (...)            [BOTTOM LEAF: Reads index first!]
```

**How data moves:**
1. The `Index Scan on users` executes first.
2. The `Hash` node takes those rows and builds an in-memory hash table.
3. The `Seq Scan on orders` streams orders one-by-one.
4. The `Hash Join` checks each order against the hash table.
5. The `Sort` node sorts the joined rows and delivers the final result.

---

<a id="3-the-flavors-of-explain"></a>
## 🎛️ 3. The Flavors of EXPLAIN: Syntax, Flags & Safety

PostgreSQL provides multiple flags inside `EXPLAIN (...)`. Choosing the right flags changes whether you see rough guesses or exact hardware reality:

```sql
EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE, SETTINGS, WAL) SELECT ...;
```

### The Crucial Options Explained:

| Option | What It Does | Why You Need It |
| :--- | :--- | :--- |
| **`ANALYZE`** *(Default: false)* | **Actually runs the query!** Measures real execution time and real row counts. | Without this, all numbers are theoretical planner estimates. |
| **`BUFFERS`** *(Default: false)* | Requires `ANALYZE`. Shows exact RAM buffer cache hits vs physical disk reads. | **The single most important flag for diagnosing I/O performance!** |
| **`VERBOSE`** *(Default: false)* | Shows output column lists, schema qualifiers, and internal table aliases. | Helps identify which expression or column projection is causing bloat. |
| **`COSTS`** *(Default: true)* | Shows startup and total cost numbers. | Useful for understanding *why* the planner chose a path. |
| **`SETTINGS`** *(Default: false)* | Displays non-default configuration parameters (e.g. `work_mem`, `random_page_cost`). | Critical for identifying misconfigured connection pools. |
| **`WAL`** *(Available in PG 13+)* | Shows Write-Ahead Log bytes and records generated by writes/updates. | Essential for optimizing `INSERT`, `UPDATE`, and `DELETE` queries. |

### ⚠️ THE PRODUCTION WARNING: `EXPLAIN ANALYZE` WITH WRITES
Because `ANALYZE` **actually executes the query**, running:
```sql
EXPLAIN ANALYZE DELETE FROM users WHERE active = false; -- ❌ DANGER: ROWS ARE DELETED!
```
**will permanently delete your data!**  
To safely analyze a write query, wrap it in a transaction and roll it back:
```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) DELETE FROM users WHERE active = false;
ROLLBACK; -- ✅ Safe: changes are never committed
```

---

<a id="4-anatomy-of-a-plan-line"></a>
## 🔬 4. Anatomy of a Plan Line: Decoding Every Number & String

Let’s take a realistic plan node and dissect every single token:

```text
->  Index Scan using idx_orders_created on orders  (cost=0.42..84.50 rows=120 width=36) (actual time=0.045..1.230 rows=115 loops=3)
```

Here is what every component means:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ -> Index Scan using idx_orders_created on orders                                                                                │
│    • Node Type: "Index Scan"                                                                                                    │
│    • Target Index: "idx_orders_created"                                                                                         │
│    • Target Relation: "orders"                                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ (cost=0.42..84.50 rows=120 width=36)  <── ESTIMATES (The Planner's Guess BEFORE Running)                                        │
│    • 0.42    : Startup Cost (cost units to fetch the very first row)                                                            │
│    • 84.50   : Total Cost (cost units to fetch ALL rows matching this node)                                                     │
│    • rows=120: Estimated number of rows this node will emit                                                                     │
│    • width=36: Estimated average byte size of each emitted row                                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ (actual time=0.045..1.230 rows=115 loops=3)  <── ACTUALS (Real Hardware Reality from ANALYZE)                                   │
│    • 0.045   : Actual milliseconds elapsed until the FIRST row was returned (per loop)                                          │
│    • 1.230   : Actual milliseconds elapsed until the LAST row was returned (per loop)                                           │
│    • rows=115: Average number of rows returned PER LOOP                                                                         │
│    • loops=3 : The number of times this entire node was executed by its parent                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### <a id="cost-units--formulas"></a>Cost Units & Formulas

What is a "cost unit"? It is **not** milliseconds or bytes. It is an arbitrary unit calibrated to disk and CPU operations:

* **`seq_page_cost = 1.0`**: Reading 1 sequential 8KB page from disk = $1.0$ cost unit.
* **`random_page_cost = 4.0`** (Default for HDDs; change to `1.1` on modern NVMe SSDs!): Reading 1 random 8KB page.
* **`cpu_tuple_cost = 0.01`**: Processing 1 row in CPU memory.
* **`cpu_operator_cost = 0.0025`**: Evaluating a `WHERE` condition or math expression.

#### Cumulative Cost Math:
Notice that a parent node’s cost **always includes the cost of its children**:
```text
Sort  (cost=120.00..125.00 ...)
  ->  Seq Scan on items  (cost=0.00..100.00 ...)
```
The `Sort` node didn't cost 125 units by itself. It cost **25 units of sorting**, plus the **100 units** incurred by its child `Seq Scan`!

---

### <a id="rows--the-estimation-ratio"></a>Rows & The Estimation Ratio (`rows` vs. `actual rows`)

One of the quickest ways to spot why a query is slow is the **Estimation Ratio**:

$$\text{Estimation Ratio} = \frac{\text{Estimated Rows}}{\text{Actual Rows} \times \text{Loops}}$$

* **Ratio $\approx 1.0$:** Perfect! The planner's statistics are accurate.
* **Ratio is $10\times$ to $1000\times$ off:** 🚨 **Red Alert!**
  * If the planner expects **1 row** but actually gets **1,000,000 rows**, it will choose a **Nested Loop join**, which will freeze your database for hours!
  * **Fix:** Stale statistics. Run `ANALYZE table_name;` or increase statistics targets (`ALTER TABLE t ALTER c SET STATISTICS 500;`).

---

### <a id="loops--actual-time-multiplication"></a>Loops & Actual Time Multiplication

⚠️ **The Biggest Beginner Trap in EXPLAIN ANALYZE:**  
`actual time` and `rows` are reported **PER LOOP**, not total!

Look at this line:
```text
->  Index Scan on order_items  (...) (actual time=0.050..1.200 rows=50 loops=1000)
```

* **Did this node take 1.2 milliseconds?**  
  **NO!** It took:
  $$\text{Total Time} = 1.200\text{ ms} \times 1000\text{ loops} = \mathbf{1{,}200\text{ ms (1.2 seconds!)}}$$
* **Did this node emit 50 rows?**  
  **NO!** It emitted:
  $$\text{Total Rows} = 50 \times 1000 = \mathbf{50{,}000\text{ rows}}$$

Whenever you see `loops > 1`, always multiply `actual time` and `rows` by the loop count!

---

<a id="5-the-buffers-line"></a>
## 💾 5. The Buffers Line: The Absolute Truth of I/O

When you include the `BUFFERS` option, Postgres displays a breakdown of physical 8KB page accesses:

```text
Buffers: shared hit=4280 read=145 dirtied=3 written=0, temp read=1200 temp written=1200
```

```
                                  SHARED BUFFERS (RAM)
                               ┌─────────────────────────┐
                               │       shared hit        │  <-- Found directly in Postgres RAM!
                               │      (Fast: ~100ns)     │      Zero disk I/O.
                               └────────────▲────────────┘
                                            │ (If not in RAM)
                               ┌────────────┴────────────┐
                               │       shared read       │  <-- Missed RAM! Had to read from
                               │     (Slow: ~0.1-5ms)    │      OS filesystem cache or physical SSD.
                               └─────────────────────────┘
```

### Deciphering the Buffer Counters:

| Counter | What It Means | Senior Optimization Rule |
| :--- | :--- | :--- |
| **`shared hit`** | Number of 8KB pages found directly in PostgreSQL's `shared_buffers` (RAM). | Higher is better! Aim for $> 99\%$ hits. |
| **`shared read`** | Number of 8KB pages that had to be fetched from disk (or OS page cache). | If this is high on repeated queries, your **working set exceeds RAM** or you are missing an index! |
| **`shared dirtied`** | Number of pages modified in RAM by an `INSERT`, `UPDATE`, or `DELETE`. | High values mean heavy write checkpoint I/O later. |
| **`shared written`** | Number of pages written directly to disk during the query. | Usually 0; non-zero indicates memory pressure forcing dirty flushes. |
| **`temp read / written`** | Number of 8KB pages spilled to **temporary scratch files on disk**! | 🚨 **Severe Bottleneck:** Query exceeded `work_mem`! Increase `work_mem`. |

---

<a id="6-complete-catalog-of-plan-nodes"></a>
## 🌳 6. Complete Catalog of Plan Nodes

### <a id="scan-nodes"></a>A. Data Access Nodes (Scans)

#### 1. Sequential Scan (`Seq Scan`)
* **What it does:** Reads every single 8KB page of the table from disk/RAM in linear order.
* **When it's good:** Small tables (< 500 rows) or when your query returns $> 15-20\%$ of the entire table. (Reading a table sequentially is faster than hopping back-and-forth across an index for large portions of data).
* **When it's bad:** On large tables where you expect only a handful of rows. Indicates a missing index or un-sargable query (e.g. `WHERE UPPER(email) = '...'`).

#### 2. Index Scan (`Index Scan`)
* **What it does:** Traverses a B-Tree index to locate row pointers (`ctid`), then visits the main table heap page to retrieve the actual columns.
* **The Caveat:** Each heap page visit is a **random read**. If returning 50,000 rows, 50,000 random page reads will be much slower than a single sequential scan!

#### 3. Index Only Scan (`Index Only Scan`) — *The Gold Standard*
* **What it does:** Every column requested in your query lives inside the index itself! Postgres **never visits the table heap**.
* **The Secret Prerequisite: The Visibility Map:**  
  Because Postgres uses MVCC, an index doesn't know if a tuple is visible or dead. Postgres checks the **Visibility Map** (VM). If the page is marked all-visible (maintained by `VACUUM`), it skips the heap entirely. If the VM is stale, it still has to check the heap (`Heap Fetches > 0`).

#### 4. Bitmap Index Scan + Bitmap Heap Scan
* **The Hybrid Engine:** Used when an index matches too many rows for an `Index Scan` (random I/O is too expensive), but too few rows for a `Seq Scan`.
  * **Phase 1 (`Bitmap Index Scan`):** Scans the index and builds a compact **in-memory bitmap** of page IDs: *"Pages 12, 18, 45, and 99 have matches."*
  * **Phase 2 (`Bitmap Heap Scan`):** Reads those exact pages from disk in strict physical order! Random I/O is converted to sequential I/O.
* **Bonus:** Postgres can combine multiple indexes with **`BitmapAnd`** or **`BitmapOr`**!

---

### <a id="join-nodes"></a>B. Join Nodes

```
                                    COMPARING THE 3 JOIN ENGINES
┌────────────────────┬──────────────────────────────────────┬─────────────────────────────────────────┐
│ Join Algorithm     │ How It Works Under the Hood          │ Ideal Scenario                          │
├────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────┤
│ **Nested Loop**    │ For each row in outer table,         │ • Outer table is tiny (< 100 rows).     │
│                    │ executes an indexed lookup on inner. │ • Inner table has a fast primary index. │
├────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────┤
│ **Hash Join**      │ Builds a hash table of inner rows in │ • Medium-to-large un-sorted tables.     │
│                    │ RAM; streams outer rows to probe it. │ • Inner table fits comfortably in       │
│                    │                                      │   work_mem.                             │
├────────────────────┼──────────────────────────────────────┼─────────────────────────────────────────┤
│ **Merge Join**     │ Zips two sorted inputs in parallel   │ • Both tables are large AND already     │
│                    │ like two gears interlocking.         │   sorted (via B-Tree or prior sort).    │
└────────────────────┴──────────────────────────────────────┴─────────────────────────────────────────┘
```

---

### <a id="sort-aggregate--materialize-nodes"></a>C. Sort, Aggregate, and Materialize Nodes

#### Sort Nodes:
* **`Sort Method: quicksort Memory: 25kB`**: Fast in-memory sort.
* **`Sort Method: top-N heapsort Memory: 15kB`**: Optimized sort when you have `ORDER BY ... LIMIT 10`. It only maintains a heap of the top 10 items in RAM!
* **`Sort Method: external merge Disk: 18450kB`**: 🚨 **Performance Killer!** Data was too large for `work_mem`. Postgres had to spill temporary chunks to disk and merge them. Increase `work_mem`!

#### Aggregate Nodes:
* **`HashAggregate`**: Builds an in-memory hash table of group keys. (e.g. `GROUP BY country`). Fast, but requires sufficient `work_mem`.
* **`GroupAggregate`**: Groups data that is **already sorted**. Uses almost zero memory because it streams rows and aggregates until the key changes.

---

### <a id="parallel-query-nodes"></a>D. Parallel Query Nodes

On modern multi-core servers, Postgres can parallelize scans, joins, and aggregates:

```text
Gather  (cost=1000.00..25000.00 rows=50000 width=16) (actual time=2.100..45.200 rows=48000 loops=1)
  Workers Planned: 4
  Workers Launched: 4
  ->  Parallel Seq Scan on large_table  (cost=0.00..19000.00 rows=12500 width=16) ...
```

* **`Gather`**: The leader process that coordinates parallel workers and collects their partial results.
* **`Gather Merge`**: Like `Gather`, but preserves the sorted order produced by parallel workers.
* **`Workers Planned vs. Launched`**: If `Workers Planned: 4` but `Workers Launched: 0`, your server hit the `max_parallel_workers` ceiling and ran single-threaded!

---

<a id="7-four-real-world-case-studies"></a>
## 🧪 7. Four Real-World Case Studies (Annotated Dissections)

Let's dissect 4 common query plans you will encounter in production.

---

### <a id="case-1-the-healthy-index-only-scan"></a>Case 1: The Healthy Index-Only Scan

```text
Index Only Scan using idx_users_active_created on users  (cost=0.42..12.50 rows=15 width=16) (actual time=0.015..0.025 rows=12 loops=1)
  Index Cond: ((is_active = true) AND (created_at >= '2024-01-01'::date))
  Heap Fetches: 0
  Buffers: shared hit=4
Planning Time: 0.112 ms
Execution Time: 0.045 ms
```

#### Diagnostic Breakdown:
* ✅ **Index Only Scan:** Postgres never touched the table heap.
* ✅ **`Heap Fetches: 0`:** The Visibility Map is pristine. Zero table visits needed.
* ✅ **`Buffers: shared hit=4`:** Only 4 pages (32 KB) read, and 100% came from RAM cache!
* ✅ **Execution Time:** $0.045\text{ ms}$ (sub-millisecond perfection).

---

### <a id="case-2-the-stale-statistics-trap"></a>Case 2: The Stale Statistics Trap (Nested Loop Disaster)

```text
Nested Loop  (cost=0.42..5420.00 rows=2 width=64) (actual time=0.080..4250.00 rows=150000 loops=1)
  Buffers: shared hit=150002 read=45000
  ->  Seq Scan on active_flags  (cost=0.00..1.20 rows=2 width=4) (actual time=0.010..0.012 rows=2 loops=1)
        Filter: (enabled = true)
  ->  Index Scan using idx_orders_flag on orders  (cost=0.42..2700.00 rows=1 width=60) (actual time=0.020..1.800 rows=75000 loops=2)
        Index Cond: (flag_id = active_flags.id)
Execution Time: 4252.120 ms
```

#### Diagnostic Breakdown:
* 🚨 **Estimation Disaster:** Look at the parent `Nested Loop`:
  * Estimated Rows: `rows=2`
  * Actual Rows: `rows=150000` (**75,000x mismatch!**)
* 🚨 **Why It Chose a Nested Loop:** Because the planner believed only 2 rows would match, it assumed running a quick loop 2 times would cost almost nothing.
* 🚨 **The Reality:** The loop ran for **150,000 rows**, taking **4.25 seconds** and executing **195,000 buffer reads**!
* 🛠️ **The Fix:**
  ```sql
  ANALYZE active_flags;
  ANALYZE orders;
  ```
  Once updated, the planner will switch to a **Hash Join**, dropping execution time from 4.2 seconds to 30 milliseconds!

---

### <a id="case-3-memory-spills-to-disk"></a>Case 3: Memory Spills to Disk (`work_mem` Starvation)

```text
HashAggregate  (cost=45000.00..52000.00 rows=50000 width=32) (actual time=450.000..720.000 rows=48000 loops=1)
  Group Key: user_id
  Batches: 5  Memory Usage: 4096kB  Disk Usage: 38400kB
  Buffers: shared hit=12000, temp read=4800 temp written=4800
  ->  Seq Scan on transactions  (cost=0.00..38000.00 rows=500000 width=16) ...
Execution Time: 750.320 ms
```

#### Diagnostic Breakdown:
* 🚨 **`Disk Usage: 38400kB`:** The hash table exceeded `work_mem` (which was capped at 4MB).
* 🚨 **`temp read=4800 temp written=4800`:** Postgres had to write 38 MB of intermediate partitions to temporary disk files, and read them back in 5 batches!
* 🚨 **`Batches: 5`:** Multiple disk passes.
* 🛠️ **The Fix:**  
  Increase `work_mem` for this session or query:
  ```sql
  SET work_mem = '64MB';
  -- Re-run query: Disk Usage drops to 0, Batches drops to 1, time drops by 70%!
  ```

---

### <a id="case-4-the-filter-drop-trap"></a>Case 4: The Filter Drop Trap (Late Filtering)

```text
Seq Scan on logs  (cost=0.00..85000.00 rows=100 width=48) (actual time=0.045..380.000 rows=10 loops=1)
  Filter: (service_name = 'auth-service' AND status_code >= 500)
  Rows Removed by Filter: 4999990
  Buffers: shared hit=45000 read=12000
Execution Time: 382.400 ms
```

#### Diagnostic Breakdown:
* 🚨 **`Rows Removed by Filter: 4999990`:** Postgres scanned **5 million rows** from disk and RAM, only to throw away 4,999,990 of them!
* **Why:** No index existed on `(service_name, status_code)`.
* 🛠️ **The Fix:**
  ```sql
  CREATE INDEX idx_logs_service_status ON logs (service_name, status_code);
  ```
  Execution will drop from 380 ms to **0.5 ms** via a direct `Index Scan`!

---

<a id="8-the-6-step-diagnostic-checklist"></a>
## 🧭 8. The Senior Engineer's 6-Step EXPLAIN Diagnostic Checklist

When presented with a slow query plan, follow this systematic diagnostic sequence:

```
                                  6-STEP EXPLAIN DIAGNOSTIC SEQUENCE
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. Scan for "temp written" or "external merge"                                                  │
│    Did the query spill to disk? ──▶ FIX: Increase work_mem.                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Compare (rows=X) vs (actual rows=Y * loops)                                                  │
│    Is estimation off by > 10x? ──▶ FIX: Run ANALYZE or CREATE STATISTICS.                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Check Buffers: (shared read vs shared hit)                                                   │
│    Are we reading massive physical disk pages? ──▶ FIX: Missing index, or working set > RAM.    │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Look for "Rows Removed by Filter"                                                            │
│    Are we throwing away millions of rows after reading? ──▶ FIX: Composite or Partial Index.    │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. Identify the Largest Time Delta                                                              │
│    Subtract child actual time from parent actual time to pinpoint the exact bottleneck node!    │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. Check Nested Loop with High Loop Count                                                       │
│    Is a loop running 100,000 times? ──▶ FIX: Ensure inner table join key is indexed.            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

<a id="9-master-reference-table"></a>
## 📊 9. Master EXPLAIN Quick Reference Table

| Symptom / Node in Plan | Root Cause | Actionable Fix |
| :--- | :--- | :--- |
| **`Rows Removed by Filter: NNNNN`** | Table scan filtered out millions of rows post-read. | Create an index covering the filtered columns. |
| **`Sort Method: external merge`** | Data too large to sort in memory. | Increase `work_mem` for the query/session. |
| **`Batches: > 1` on Hash Join/Agg** | Hash table exceeded memory, spilled to temp disk. | Increase `work_mem`. |
| **`rows=1` vs `actual rows=50000`** | Planner severely underestimated row count; picks wrong join. | Run `ANALYZE table_name;` or increase column statistics target. |
| **`Heap Fetches: > 0` on Index-Only** | Visibility Map is dirty; must visit heap to check MVCC. | Run `VACUUM table_name;` to clean Visibility Map. |
| **`Seq Scan` on large table with filter** | Missing index or un-sargable expression (e.g. `LOWER(col)`). | Add index or functional index (`CREATE INDEX ON t (LOWER(c))`). |
| **`Workers Planned > Workers Launched`** | Server reached global `max_parallel_workers` limit. | Tune `max_parallel_workers` / `max_parallel_workers_per_gather`. |
| **`Buffers: shared read` very high** | Pages not in `shared_buffers` cache; heavy disk I/O. | Tune `shared_buffers` / verify OS page cache sizing. |

---

### 🎓 Summary
> *"Reading an EXPLAIN plan is about following the **I/O and row discrepancies**: Check **`Buffers`** to see if you are hitting RAM or disk, inspect **`loops`** to calculate true elapsed time, compare **`rows` vs `actual rows`** to catch stale statistics, and ensure your query uses **Index-Only Scans** or **in-memory Hash Joins** without spilling to disk."*
