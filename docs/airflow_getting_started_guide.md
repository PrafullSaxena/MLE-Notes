# The Definitive Apache Airflow Getting Started & Production Guide

A practical, senior-level guide to orchestrating complex data engineering and ML pipelines with Apache Airflow. Covers internal architecture, TaskFlow API, Executors, Sensors, XComs, and end-to-end pipeline integration with Spark and Milvus.

---

## Table of Contents
1. [What is Apache Airflow? (The Mental Model)](#1-what-is-apache-airflow-the-mental-model)
2. [Airflow Internal Architecture](#2-airflow-internal-architecture)
   - [Core Components: Webserver, Scheduler, Metadata DB, Triggerer, Worker](#core-components)
   - [Executors Compared: Sequential vs Local vs Celery vs Kubernetes](#executors-compared)
3. [Airflow Primitives & Mental Model](#3-airflow-primitives--mental-model)
   - [DAGs, Tasks, DAG Runs, and Task Instances](#dags-tasks-dag-runs-and-task-instances)
   - [Operators vs Sensors vs Hooks](#operators-vs-sensors-vs-hooks)
   - [The Modern TaskFlow API (`@task`, `@dag`)](#the-modern-taskflow-api)
4. [Task Dependencies & Workflow Control](#4-task-dependencies--workflow-control)
   - [Bitshift Operators (`>>`, `<<`) and `chain`](#bitshift-operators-and-chain)
   - [Branching (`BranchPythonOperator` / `@task.branch`)](#branching)
   - [Trigger Rules: Mastering Complex Geometries](#trigger-rules)
5. [Data Sharing: XComs & Big Data Anti-Patterns](#5-data-sharing-xcoms--big-data-anti-patterns)
   - [How XCom Works & The 48KB Metadata DB Limit](#how-xcom-works)
   - [Custom Object Storage XCom Backends (S3, GCS)](#custom-xcom-backends)
6. [Scheduling, Data Intervals & The "Execution Date" Gotcha](#6-scheduling-data-intervals--the-execution-date-gotcha)
   - [Logical Date vs Run Date vs Data Intervals](#logical-date-vs-data-intervals)
   - [`catchup` and Backfilling](#catchup-and-backfilling)
7. [Sensors & Deferrable Operators (Async Scaling)](#7-sensors--deferrable-operators)
   - [`poke` vs `reschedule` Mode](#poke-vs-reschedule-mode)
   - [The Triggerer & Deferrable Operators](#the-triggerer--deferrable-operators)
8. [End-to-End Production Pipeline: Spark -> Vectorization -> Milvus](#8-end-to-end-production-pipeline-spark---vectorization---milvus)
9. [Airflow CLI & Debugging Cheat Sheet](#9-airflow-cli--debugging-cheat-sheet)

---

## 1. What is Apache Airflow? (The Mental Model)

Airflow is an **orchestration engine**, not an execution or data-processing engine.

> [!IMPORTANT]
> **Orchestrator vs Data Processor**:
> - Airflow is the **Air Traffic Controller**: It decides *when* planes take off, *in what sequence*, checks if runways are clear, and sounds alarms if an engine fails.
> - Spark, Trino, Snowflake, Milvus, and Kubernetes are the **Jet Engines**: They do the heavy lifting, processing terabytes of data or running matrix math.
> - **Anti-Pattern**: Never load 50GB of raw data into memory inside an Airflow Python worker. Use Airflow to trigger and monitor a Spark job, a dbt model, or an async vector ingest script.

Airflow expresses workflows as **Directed Acyclic Graphs (DAGs)** written in native Python code. Because DAGs are code:
- Workflows are version-controlled in Git.
- Pipelines can be dynamically generated using loops and external config files.
- Unit testing can be written with `pytest`.

---

## 2. Airflow Internal Architecture

```
                             APACHE AIRFLOW ARCHITECTURE
     +-----------------------------------------------------------------------+
     |                                                                       |
     |   +-------------------+                     +--------------------+    |
     |   |  Airflow Web UI   |                     |      DAG Files     |    |
     |   | (Flask / React)   |                     | (/opt/airflow/dags)|    |
     |   +---------+---------+                     +---------+----------+    |
     |             |                                         |               |
     |             v                                         v               |
     |   +------------------------------------------------------+            |
     |   |                   AIRFLOW SCHEDULER                  |            |
     |   |  1. Parses DAG folder periodically                   |            |
     |   |  2. Evaluates task dependencies                      |            |
     |   |  3. Creates DagRuns & TaskInstances                  |            |
     |   |  4. Submits Queued tasks to Executor                 |            |
     |   +-------------+----------------------------+-----------+            |
     |                 |                            |                        |
     |                 v                            v                        |
     |   +--------------------------+    +--------------------------+        |
     |   |     AIRFLOW TRIGGERER    |    |   METADATA DATABASE      |        |
     |   |  (Asyncio event loop for |    | (PostgreSQL / MySQL)     |        |
     |   |   deferrable operators)  |    | - Single source of truth |        |
     |   +-------------+------------+    | - Task states, DAG logs  |        |
     |                 |                 +--------------+-----------+        |
     +-----------------+--------------------------------+--------------------+
                       |                                |
                       v                                v
     +-----------------------------------------------------------------------+
     |                            AIRFLOW EXECUTOR                           |
     |                                                                       |
     |   [CeleryExecutor / Redis Queue]        [KubernetesExecutor]          |
     |          |             |                          |                   |
     |          v             v                          v                   |
     |      Worker 1      Worker 2              On-Demand K8s Pod            |
     |    (Long-lived)  (Long-lived)          (Runs task -> Terminates)      |
     +-----------------------------------------------------------------------+
```

### Core Components

1. **Airflow Scheduler**: The heartbeat of the system. It parses DAG files every few seconds, queries the Metadata DB to check which tasks are ready to run, and pushes executable tasks to the Executor queue.
2. **Metadata Database (PostgreSQL / MySQL)**: Airflow's single source of truth. Stores DAG definitions, execution runs, task states (`success`, `failed`, `running`, `up_for_retry`), variables, connections, and XComs.
3. **Webserver**: Clean GUI for viewing DAGs, DAG runs, gantt charts, task logs, manual triggers, and clearing failed tasks for retries.
4. **Triggerer**: An `asyncio`-powered daemon that handles **deferrable tasks**. Instead of tying up an entire worker thread waiting for a 4-hour Snowflake query or Spark job, the task surrenders its worker slot and sleeps inside the Triggerer until notified.
5. **Workers**: The processes or containers that physically execute the operators.

### Executors Compared

| Executor | Architecture | Scaling Characteristics | Best For |
|---|---|---|---|
| **Sequential** | Runs 1 task at a time via SQLite. | Zero concurrency. Cannot scale. | Local dev & quick testing only. |
| **Local** | Runs tasks in worker subprocesses on the same machine as Scheduler. | Limited by CPU/RAM of the single host. | Small production workloads (< 30 DAGs). |
| **Celery** | Distributed worker pool using Redis or RabbitMQ as broker. | High throughput, fast task startup (< 100ms). Workers run continuously. | High-frequency workloads; static clusters. |
| **Kubernetes** | Launches a dedicated K8s Pod for **each individual task**. | Infinite auto-scaling, total dependency isolation (different Docker images per task). High overhead (~5-15s per task pod startup). | Heavy data pipelines, ML tasks with custom libraries/GPUs. |

---

## 3. Airflow Primitives & Mental Model

### DAGs, Tasks, DAG Runs, and Task Instances

- **DAG**: The blueprint defining the complete pipeline structure and dependencies.
- **Task**: An individual node within the DAG (e.g., `extract_from_postgres`, `run_spark_job`).
- **DAG Run**: An actual execution of the DAG for a specific point in time (e.g., `scheduled__2026-09-23T00:00:00+00:00`).
- **Task Instance (TI)**: The execution of a specific Task within a specific DAG Run. Has a concrete state (`QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`).

### Operators vs Sensors vs Hooks

- **Operator**: Defines **what work is done** (e.g., `PythonOperator`, `BashOperator`, `KubernetesPodOperator`).
- **Sensor**: A special operator that **waits for an external condition** to become true (e.g., a file landing in S3, a partition existing in Hive, an API returning status 200).
- **Hook**: The **low-level connection interface** to external systems (e.g., `PostgresHook`, `S3Hook`). Operators use Hooks under the hood to authenticate and execute queries.

### The Modern TaskFlow API

Airflow 2 introduced the **TaskFlow API** using Python decorators (`@dag`, `@task`). It removes the boilerplate of manual operator instantiations and handles XCom passing automatically as function arguments:

```python
from datetime import datetime
from airflow.decorators import dag, task

@dag(
    dag_id="taskflow_modern_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["learning", "taskflow"]
)
def my_pipeline():

    @task
    def extract() -> list[dict]:
        return [{"id": 1, "text": "Kubernetes orchestration"}, {"id": 2, "text": "Vector databases"}]

    @task
    def transform(records: list[dict]) -> list[dict]:
        for r in records:
            r["length"] = len(r["text"])
        return records

    @task
    def load(processed_records: list[dict]):
        print(f"Ingested {len(processed_records)} items into storage!")

    # Dependencies are inferred automatically from data flow!
    raw_data = extract()
    cleaned_data = transform(raw_data)
    load(cleaned_data)

pipeline = my_pipeline()
```

---

## 4. Task Dependencies & Workflow Control

### Bitshift Operators and Chain

```python
from airflow.models.baseoperator import chain

# Bitshift notation (Right shift >> means "runs before")
task_a >> task_b >> [task_c, task_d] >> task_e

# Chain helper for lists of tasks
# Equivalent to: [task_1, task_2] >> [task_3, task_4]
chain([task_1, task_2], [task_3, task_4])
```

### Branching

When your workflow needs to execute branch A or branch B conditionally:

```python
from airflow.decorators import task

@task.branch
def check_data_volume(row_count: int) -> str:
    if row_count > 100_000:
        return "run_spark_cluster_job"
    else:
        return "run_local_python_ingest"
```

### Trigger Rules

By default, an Airflow task executes only when **all upstream tasks have succeeded** (`TriggerRule.ALL_SUCCESS`). You can override this behavior:

```python
from airflow.utils.trigger_rule import TriggerRule

cleanup_task = PythonOperator(
    task_id="cleanup_temp_files",
    python_callable=cleanup_scratch_dir,
    trigger_rule=TriggerRule.ALL_DONE # Runs regardless of whether upstream succeeded or failed!
)

notify_pagerduty = PythonOperator(
    task_id="page_on_call",
    python_callable=send_pagerduty_alert,
    trigger_rule=TriggerRule.ONE_FAILED # Triggers as soon as any upstream branch fails!
)
```

| Trigger Rule | Executes When... | Use Case |
|---|---|---|
| `all_success` (Default) | Every upstream task finished in `SUCCESS`. | Standard linear pipelines. |
| `all_failed` | Every upstream task finished in `FAILED` or `UPSTREAM_FAILED`. | Disaster recovery pipelines. |
| `all_done` | Every upstream task is finished (regardless of success/fail). | Resource cleanup, teardown of ephemeral clusters. |
| `one_failed` | At least one upstream task fails (doesn't wait for others). | Immediate alerting / emergency rollback. |
| `none_failed` | All upstream tasks either succeeded or were skipped. | Joining branches after a `BranchPythonOperator`. |

---

## 5. Data Sharing: XComs & Big Data Anti-Patterns

### How XCom Works
**XCom** ("Cross-Communication") allows tasks to exchange small pieces of metadata (e.g., job IDs, file paths, partition dates, row counts).
- Whenever a task returns a value, Airflow serializes it (default: JSON) and writes it into the `xcom` table in the Airflow Metadata Database.

```
Task A: return {"s3_path": "s3://bucket/2026-09-23/embeddings.parquet"}
             |
             v (Stored in Postgres table: `xcom`)
             |
Task B: context["ti"].xcom_pull(task_ids="task_a")
```

> [!WARNING]
> **The 48KB Danger Zone**: The default metadata DB column for XCom is a `BLOB`/`BYTEA` limited to roughly 48KB - 1GB depending on DBMS. **Never push large lists, embedding tensors, or Pandas DataFrames through native XCom.** It will bloat PostgreSQL, exhaust connection pools, and crash the scheduler.

### Custom XCom Backends (S3, GCS)
For enterprise data engineering, configure an **Object Storage XCom Backend**. Any object returned by a task is transparently uploaded to S3/GCS, and only the S3 URI is stored in the PostgreSQL database:

```python
# airflow.cfg
# [core]
# xcom_backend = airflow.providers.amazon.aws.transfers.base.S3XComBackend
# xcom_s3_bucket = my-company-airflow-xcoms
```

---

## 6. Scheduling, Data Intervals & The "Execution Date" Gotcha

The most common point of confusion for new Airflow engineers is the schedule timeline.

### Logical Date vs Data Intervals

Airflow operates on **Data Intervals**. A daily pipeline for `2026-09-23` runs at **the END of that day**, i.e., `2026-09-24 00:00:00`:

```
Data Interval: [ 2026-09-23 00:00:00  to  2026-09-23 23:59:59 ]
                                                                |
                                                                v
                                              Execution starts: 2026-09-24 00:00:00
```
- `data_interval_start`: The start of the data period being processed (`2026-09-23 00:00:00`).
- `data_interval_end`: The end of the data period being processed (`2026-09-24 00:00:00`).
- `logical_date` (formerly `execution_date`): Same as `data_interval_start`.

```python
@task
def query_partition(**context):
    start = context["data_interval_start"].strftime("%Y-%m-%d")
    end = context["data_interval_end"].strftime("%Y-%m-%d")
    print(f"Processing data created between {start} and {end}")
```

### `catchup` and Backfilling
When you create a DAG with `start_date = datetime(2025, 1, 1)` and deploy it today:
- If `catchup=True` (default in Airflow 1): The scheduler immediately queues up hundreds of DAG runs (one for every single day since 2025-01-01), potentially crashing your cluster!
- **Production Standard**: Always set `catchup=False` unless you explicitly want automatic historical backfilling.

---

## 7. Sensors & Deferrable Operators

A **Sensor** pauses the pipeline until an external event happens (e.g., waiting for an upstream file `data_ready.flag` to appear).

### `poke` vs `reschedule` Mode

```
Mode: 'poke' (Anti-pattern for long waits)
Worker Thread: [ Occupied (Active) ]----[ Sleep 60s (Active) ]----[ Occupied ]
Result: Completely blocks 1 Airflow worker slot while doing nothing!

Mode: 'reschedule' (Best Practice)
Worker Thread: [ Check condition ] -> False -> [ RELEASE WORKER SLOT ] -> Sleep in DB
Result: Other tasks can use the worker while waiting!
```

```python
from airflow.sensors.filesystem import FileSensor

wait_for_file = FileSensor(
    task_id="wait_for_landing_file",
    filepath="/landing/transactions.csv",
    mode="reschedule",      # Relinquishes worker slot between pokes
    poke_interval=120,      # Check every 2 minutes
    timeout=3600            # Fail if not found after 1 hour
)
```

### The Triggerer & Deferrable Operators
In Airflow 2.2+, **Deferrable Operators** take resource efficiency further. The task yields execution to the `Triggerer` daemon, freeing up the worker completely until an asynchronous event fires via Python's `asyncio`.

---

## 8. End-to-End Production Pipeline: Spark -> Vectorization -> Milvus

Here is a complete, production-grade DAG demonstrating how to orchestrate a distributed data pipeline with retries, alerts, and dependency chaining.

```python
"""
production_vector_ingest_pipeline.py
Orchestrates: Extract -> Spark Transformation -> Embedding Vectorization -> Milvus Ingestion
"""

from datetime import datetime, timedelta
import logging
from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

# Custom alert callback on task failure
def on_task_failure_alert(context):
    task_id = context['task_instance'].task_id
    dag_id = context['task_instance'].dag_id
    log_url = context['task_instance'].log_url
    error = context.get('exception')
    logging.error(f"[ALERT] Task {task_id} in {dag_id} failed: {error}. Inspect logs: {log_url}")

# Default arguments applied to all tasks
DEFAULT_ARGS = {
    "owner": "data-platform",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "on_failure_callback": on_task_failure_alert,
}

@dag(
    dag_id="spark_to_milvus_vector_pipeline",
    default_args=DEFAULT_ARGS,
    description="Extracts documents, runs Spark text prep, embeds with SentenceTransformers, loads to Milvus",
    schedule="0 3 * * *", # Run daily at 3:00 AM UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["spark", "milvus", "vector-db", "ml-engineering"]
)
def vector_ingest_pipeline():

    # Task 1: Check upstream data readiness via BashOperator
    verify_lake_data = BashOperator(
        task_id="verify_lake_data",
        bash_command="test -f /tmp/data_lake/documents_{{ ds_nodash }}.parquet || exit 0"
    )

    # Task 2: Trigger Spark Transformation (in production, use SparkSubmitOperator or DatabricksOperator)
    @task
    def run_spark_preprocessing(ds: str = None) -> str:
        """
        Submits Spark batch job to clean raw text and chunk long articles.
        Returns the output staging S3/file path.
        """
        output_path = f"/tmp/staging/chunked_docs_{ds}.parquet"
        logging.info(f"Triggering Spark job for date {ds}. Target output: {output_path}")
        # In real-world: SparkSession reads raw, runs chunking udf, writes parquet
        return output_path

    # Task 3: Vectorize and Ingest into Milvus
    @task
    def embed_and_load_milvus(staging_path: str):
        """
        Reads chunked documents, generates embeddings using embedding model,
        and batch inserts into Milvus collection with index building.
        """
        from pymilvus import MilvusClient
        logging.info(f"Connecting to Milvus and processing {staging_path}")
        
        # Connect to Milvus
        client = MilvusClient(uri="http://milvus-standalone:19530")
        collection_name = "production_knowledge_base"
        
        if not client.has_collection(collection_name):
            logging.info(f"Collection {collection_name} does not exist. Initializing schema...")
            # Auto-create collection with 384-dim HNSW index
            # client.create_collection(...)
        
        logging.info(f"Successfully vectorized and batch-loaded records into {collection_name}")

    # Task 4: Collection Rotation & Switch Alias
    @task
    def update_milvus_alias():
        """
        Switches the Milvus production alias to point to the freshly updated collection.
        Zero-downtime blue/green deployment!
        """
        logging.info("Switching alias 'kb_active' to current snapshot...")

    # Task 5: Teardown / Cleanup
    @task(trigger_rule=TriggerRule.ALL_DONE)
    def cleanup_temporary_staging(staging_path: str):
        """Clean up scratch files regardless of success or failure."""
        logging.info(f"Cleaning up ephemeral scratch path: {staging_path}")

    # Dependency wiring
    check = verify_lake_data
    staging_file = run_spark_preprocessing()
    load = embed_and_load_milvus(staging_file)
    alias = update_milvus_alias()
    clean = cleanup_temporary_staging(staging_file)

    check >> staging_file >> load >> alias >> clean

pipeline_instance = vector_ingest_pipeline()
```

---

## 9. Airflow CLI & Debugging Cheat Sheet

### Fast Local Testing (Without Running Scheduler)
You can test any individual task directly from your terminal in isolation:

```bash
# Test a single task instance locally (does NOT write to DB, ignores upstream states!)
airflow tasks test <dag_id> <task_id> 2026-09-23

# Render task templates and verify variables/jinja expressions
airflow tasks render <dag_id> <task_id> 2026-09-23

# Validate DAG syntax and check for parsing errors
airflow dags list-import-errors
```

### DAG Operations & Management
```bash
# List all active DAGs
airflow dags list

# Trigger a DAG manually with JSON configuration
airflow dags trigger <dag_id> --conf '{"batch_size": 500, "dry_run": false}'

# Pause / Unpause a DAG
airflow dags pause <dag_id>
airflow dags unpause <dag_id>

# Show task tree / dependency state
airflow dags show <dag_id>
```

### Backfilling Historical Runs
```bash
# Backfill DAG runs for a specific date range
airflow dags backfill <dag_id> \
    --start-date 2026-01-01 \
    --end-date 2026-01-10 \
    --reset-dagruns
```

### Clearing Failed Tasks to Retry
```bash
# Clear failed tasks so scheduler picks them up again
airflow tasks clear <dag_id> \
    --task-regex ".*milvus.*" \
    --start-date 2026-09-20 \
    --end-date 2026-09-23 \
    --downstream \
    --yes
```
