# ⚡ Apache Spark & PySpark Masterclass: Zero to Contributor

A comprehensive, production-grade tutorial suite covering **Apache Spark internal architecture, the PySpark DataFrame API, distributed joins, window functions, and advanced performance optimization**.

> **Companion Video References:**
> - [PySpark Tutorial | Full Course (From Zero to Pro!)](https://www.youtube.com/watch?v=94w6hPk7nkM) by Ansh Lamba (~6 Hours)
> - [PySpark Tutorial for Beginners](https://www.youtube.com/watch?v=_C8kWBEw6KU) by freeCodeCamp.org / Krish Naik
> - [Apache Spark Architecture & Optimization](https://www.youtube.com/@AdvancingAnalytics) by Advancing Analytics

---

## 🗺️ Curriculum Structure

This tutorial is organized into **4 progressive, hands-on Jupyter notebooks**. Each notebook combines deep theoretical architecture with fully executable code and pre-rendered outputs.

```
spark_tutorial/
├── 01_spark_architecture_and_internals.ipynb      # Cluster design, DAGs, Catalyst, Tungsten
├── 02_dataframes_and_structured_api.ipynb          # Schemas, CSV/Parquet, Column ops, Spark SQL
├── 03_advanced_transformations_and_joins.ipynb     # Window functions, BHJ vs SMJ, Aggregations
└── 04_performance_tuning_and_production_patterns.ipynb # AQE, Skew Salting, Repartition vs Coalesce, ETL
```

---

### 📘 [Notebook 1: Spark Architecture & Deep Internals](01_spark_architecture_and_internals.ipynb)
* **The Evolution of Big Data:** Why Hadoop MapReduce was too slow (disk-bound I/O) and why Spark won (RAM caching & DAG lineage).
* **Cluster Mechanics:** Driver Node (Brain), Worker Nodes / Executors (Muscle), and Cluster Managers (Kubernetes, YARN, Standalone).
* **The Execution Hierarchy:** Application $\rightarrow$ Job (triggered by Actions) $\rightarrow$ Stage (split by Shuffles) $\rightarrow$ Task (1 per partition).
* **Lazy Evaluation & DAG:** Why Spark delays execution until an Action is invoked.
* **Narrow vs. Wide Transformations:** The network **Shuffle Barrier** and how stages are split.
* **The Catalyst Optimizer:** Unresolved Plan $\rightarrow$ Analyzed Plan $\rightarrow$ Optimized Plan (Predicate Pushdown & Column Pruning) $\rightarrow$ Physical Plan.
* **Project Tungsten:** Off-heap binary memory (`UnsafeRow`) and Whole-Stage Code Generation.
* **Hands-on:** Starting a `SparkSession`, inspecting configurations, and decoding `.explain(extended=True)`.

---

### 📊 [Notebook 2: PySpark DataFrames & The Structured API](02_dataframes_and_structured_api.ipynb)
* **RDDs vs DataFrames:** Why the Structured API is 10x-100x faster than raw Python RDDs.
* **Strict Schemas:** Using `StructType` and `StructField` (and why `inferSchema=True` is an anti-pattern in production).
* **Storage Formats Compared:** Why **Apache Parquet** (columnar layout, statistics footer, dictionary encoding) outperforms CSV and JSON.
* **Core Transformations:** `select`, `col`, `withColumn`, `withColumnRenamed`, `drop`, `filter`, and conditional `when/otherwise`.
* **Handling Missing Data:** Solving dirty real-world data with `dropna`, `fillna`, and `coalesce`.
* **Spark SQL Interoperability:** Creating temporary views (`createOrReplaceTempView`) and querying DataFrames with standard ANSI SQL.

---

### 🔗 [Notebook 3: Advanced Transformations, Window Functions & Joins](03_advanced_transformations_and_joins.ipynb)
* **Multi-Metric Aggregations & Pivot Tables:** Grouping across multiple business dimensions simultaneously.
* **Window Functions Demystified:**
  * **Ranking:** `row_number()`, `rank()`, `dense_rank()`.
  * **Analytics:** `lead()` and `lag()` for time-series comparisons without self-joins.
  * **Cumulative Metrics:** Running totals and moving averages using `rowsBetween`.
* **Distributed Joins Under the Hood:**
  * `inner`, `left`, `right`, `full`, `left_semi`, and `left_anti` (finding orphan keys).
  * **Shuffle Sort-Merge Join (SMJ):** How large distributed joins work.
  * **Broadcast Hash Join (BHJ):** Replicating small dimension tables across executor RAM to **completely eliminate network shuffles** (`broadcast(df)`).

---

### 🚀 [Notebook 4: Performance Tuning, Skew Mitigation & Production ETL](04_performance_tuning_and_production_patterns.ipynb)
* **Partition Sizing Mechanics:** Calculating partition counts; `repartition()` (full shuffle) vs `coalesce()` (narrow merge).
* **The "Straggler" Problem & Data Skew:** Why 1 task gets stuck at 99% for hours while all others finish in seconds.
* **The Salting Technique:** Mitigating data skew mathematically using random salt keys and two-stage aggregation.
* **Caching & Persistence:** When to use `cache()` vs `persist(StorageLevel)`, and how to avoid memory leaks with `unpersist()`.
* **Adaptive Query Execution (AQE):** Modern Spark runtime optimizations (dynamic partition coalescing, runtime join switching, and skew joins).
* **Capstone Production ETL:** Building an end-to-end, multi-source e-commerce ETL pipeline writing partitioned Parquet data.

---

## 📖 Master Spark Jargon Buster & Reference Table

| Term | What It Means (Simple English) | Analogy / Real-World Implication |
| :--- | :--- | :--- |
| **Driver Node** | Master process. Runs your Python script, creates the `SparkSession`, translates code to a DAG, and schedules tasks. | The master architect / air traffic controller. |
| **Executor** | Dedicated JVM worker process on cluster nodes. Stores cached data in RAM and runs tasks. | The construction crew executing physical work. |
| **Cluster Manager** | Allocates CPU cores and RAM across physical machines (Kubernetes, YARN, Standalone). | Resource scheduler. |
| **Partition** | Atomic chunk of data (typically 128 MB on disk). Governs parallelism. | One slice of a multi-tier cake. 1 Partition = 1 Task = 1 CPU Core at a time. |
| **Transformation** | An operation that produces a new DataFrame (e.g. `filter`, `select`). **Lazy**. | Writing down items on a grocery list. |
| **Action** | An operation that triggers DAG computation and returns results (e.g. `show()`, `count()`, `write`). **Eager**. | Driving to the grocery store and buying the items. |
| **Narrow Transf.** | 1-to-1 data flow (e.g. `filter`, `map`). No data leaves the executor. | Peeling carrots at your own station. |
| **Wide Transf.** | N-to-N data flow (e.g. `groupBy`, `join`). Requires a **Shuffle** across the network. | Trading ingredients across tables. Expensive network I/O! |
| **Shuffle** | Redistributing data across cluster nodes over the network. Splits execution into new **Stages**. | Major bottleneck in distributed computing. Minimize whenever possible! |
| **DAG** | Directed Acyclic Graph. The mathematical dependency blueprint of your transformations. | The workflow graph Spark optimizes before executing. |
| **Catalyst** | Spark's internal relational query optimizer. Performs predicate pushdown and column pruning. | Automatic SQL query tuner. |
| **Tungsten** | Spark's execution engine. Allocates off-heap binary memory (`UnsafeRow`) to bypass Java GC pauses. | C-speed execution inside a Java/Python framework. |
| **AQE** | Adaptive Query Execution. Dynamically optimizes query plans at runtime after shuffle stages. | A GPS rerouting dynamically based on real-time traffic. |
| **Broadcast Join** | Copying a small lookup table to all executors in memory to avoid a shuffle. | Handing every cook a copy of the menu. |
| **Salting** | Appending random keys (`0..k`) to skewed keys to break a massive partition into smaller chunks. | Opening 4 checkout registers for the longest line at a supermarket. |

---

## 🏃 How to Run the Notebooks

From the project root directory:

```bash
# Start JupyterLab
uv run jupyter lab notebooks/spark_tutorial/01_spark_architecture_and_internals.ipynb
```

Choose **Run → Run All Cells**. All dependencies (`pyspark`, `py4j`, `ipykernel`) are already installed and configured in your local `.venv`.
