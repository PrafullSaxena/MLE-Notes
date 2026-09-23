# 🎯 Engineering Mastery & Review Checklist (TODO Reviews)
### *Standardized Technology Taxonomy, Progress Tracker & Study Roadmap*

This document standardizes, categorizes, and tracks the 18 technical feedback topics across our learning sessions (Vector Databases, Relational Storage Internals, Big Data, Machine Learning, DevOps, Observability, and Developer Productivity).

---

## 📊 Master Progress & Taxonomy Matrix

| # | Standardized Technical Title | Primary Tech | Engineering Domain | Status | Workspace Reference |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | **IVF vs. HNSW Indexing** | Milvus / FAISS | Vector Databases | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) & [`milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) |
| **2** | **Poisson Distribution & Queuing Theory** | Mathematics / Stats | ML & Reliability | `COMPLETED` | [`machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 1) |
| **3** | **Deep Learning Models: DNN, CNN, and RNN** | PyTorch / TensorFlow | Deep Learning | `COMPLETED` | [`machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 2) |
| **4** | **t-SNE Dimensionality Reduction (High-Dim to 2D)** | Scikit-Learn | ML & Visualization | `COMPLETED` | [`machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 3) |
| **5** | **Distance Metrics: Cosine vs. Euclidean ($L_2$) vs. IP** | Milvus / Linear Algebra | Vector Databases | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) & [`machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) |
| **6** | **Deep Dive on PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)`** | PostgreSQL | Relational Databases | `COMPLETED` | [`understanding_postgres_explain.md`](docs/understanding_postgres_explain.md) & [`postgresql_internals_and_optimization_guide.md`](docs/postgresql_internals_and_optimization_guide.md) |
| **7** | **Vector DB Architecture & Disaggregated Design** | Milvus / Vector DBs | Distributed Systems | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) & [`milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) |
| **8** | **Postgres JSONB Indexing: B-Trees vs. GIN (`path_ops`)** | PostgreSQL | Relational Databases | `COMPLETED` | [`postgresql_internals_and_optimization_guide.md`](docs/postgresql_internals_and_optimization_guide.md) |
| **9** | **Milvus Collection Aliases & Zero-Downtime Rotations** | Milvus Operations | Vector DB Operations | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) (Section 7) |
| **10** | **Milvus Cluster Optimization & Internal Mechanics** | Milvus | Vector Databases | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) & [`milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) |
| **11** | **Chatbot Context Management & Memory Architecture** | LangChain / LLMs | Generative AI & NLP | `COMPLETED` | [`machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 5) |
| **12** | **Apache Flink: Real-Time Stream Analytics & Top-K** | Apache Flink | Stream Processing | `TODO` | *Upcoming Real-Time Streaming Module* |
| **13** | **Unindexed Ingestion: Growing Segments & Brute-Force**| Milvus Internals | Vector Databases | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) & [`milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) |
| **14** | **Vector Index Taxonomy (FLAT, IVF, HNSW, SCaNN)** | Milvus | Vector Databases | `COMPLETED` | [`milvus_complete_guide.md`](docs/milvus_complete_guide.md) & [`milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) |
| **15** | **Kubernetes (K8s): Pods, StatefulSets & Operators** | Kubernetes | Cloud Infrastructure | `COMPLETED` | [`kubernetes_getting_started_guide.md`](docs/kubernetes_getting_started_guide.md) |
| **16** | **Apache Airflow: DAG Orchestration & ETL Pipelines** | Apache Airflow | Data Engineering | `COMPLETED` | [`airflow_getting_started_guide.md`](docs/airflow_getting_started_guide.md) |
| **17** | **Observability: Grafana, Prometheus & PagerDuty** | Grafana / Prometheus | Observability & SRE | `COMPLETED` | [`grafana_dashboards_alerts_and_pagerduty.md`](docs/grafana_dashboards_alerts_and_pagerduty.md) |
| **18** | **Developer Productivity: Slack ChatOps & Workflows** | Slack Platform | Developer Tooling | `COMPLETED` | [`slack_developer_productivity_and_chatops.md`](docs/slack_developer_productivity_and_chatops.md) |

---

## 🗂️ Detailed Categorical Checklist & Study Notes

### Category 1: Vector Databases & Similarity Search (Milvus)
- [x] **#1. IVF vs. HNSW Indexing:**
  - *Concept:* Graph-based skip-list traversal (**HNSW**) vs. Voronoi cell K-means clustering (**IVF_FLAT**).
  - *Trade-offs:* HNSW provides highest recall and sub-millisecond search at the expense of higher RAM and build time. IVF saves memory and builds faster but has lower recall.
  - *Location:* [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) (Section 1 & 7).
- [x] **#5. Distance Metrics: Cosine vs. Euclidean ($L_2$) vs. Inner Product (IP):**
  - *Concept:* $L_2$ measures straight-line distance (sensitive to vector magnitude). Cosine measures the angle (independent of document length). IP is dot product (identical to Cosine when vectors are unit-normalized $\|v\|=1$).
  - *Location:* [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) (Section 1.4 & 9).
- [x] **#7. Vector DB Architecture & Disaggregated Design:**
  - *Concept:* 4-layer cloud-native separation: Access Layer (Proxy), Coordinator Brain (Root/Data/Query/IndexCoord), Worker Muscle (Query/Data/IndexNodes), and Storage Engine (etcd, Kafka/Pulsar WAL, MinIO/S3).
  - *Location:* [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) (Section 2).
- [x] **#9. Milvus Collection Aliases & Zero-Downtime Blue/Green Rotations:**
  - *Concept:* Decoupling client query code from physical collection names using `utility.create_alias()` and `utility.alter_alias()`. Re-building an index or ingesting a new embedding version in collection `v2`, then atomic swapping alias `prod_search` from `v1` to `v2` with zero downtime.
  - *Location:* [`docs/milvus_complete_guide.md`](docs/milvus_complete_guide.md) (Section 7).
- [x] **#10. Milvus Optimization & Internal Mechanics:**
  - *Concept:* Managing segment size thresholds (512MB), compaction cycles to purge tombstoned deletions, and memory budgeting on QueryNodes.
  - *Location:* [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) (Section 2 & 8).
- [x] **#13. Insertion Without Creating Index (Growing Segments):**
  - *Concept:* How streaming vectors enter an active in-memory buffer (**Growing Segment**) where they are immediately searchable via brute-force before an HNSW index is built. Flushed into **Sealed Segments** on S3 for asynchronous index construction.
  - *Location:* [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) (Section 2.2 & 9).
- [x] **#14. Types of Indexes in Milvus & Use Cases:**
  - *Concept:* Complete taxonomy: FLAT (brute-force 100% recall), IVF_FLAT (balanced), IVF_PQ / IVF_SQ8 (quantized low-RAM), HNSW (high-speed graph), SCaNN / DiskANN (billion-scale SSD-backed).
  - *Location:* [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb) (Section 1.5 & Reference Table).

---

### Category 2: Relational Databases & SQL Engine Internals (PostgreSQL)
- [x] **#6. Deep Dive on PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)`:**
  - *Concept:* Calculating startup vs total cost ($cost=startup..total$), reading `shared hit` (RAM buffer cache) vs `read` (disk I/O), scan engines (Seq Scan, Index Scan, Index-Only Scan, Bitmap Scan), and join engines (Nested Loop, Hash Join, Merge Join).
  - *Location:* Dedicated field guide in [`docs/understanding_postgres_explain.md`](docs/understanding_postgres_explain.md) and [`docs/postgresql_internals_and_optimization_guide.md`](docs/postgresql_internals_and_optimization_guide.md) (Section 3).
- [x] **#8. Creating Indexes on JSON Keys (B-Trees vs. GIN):**
  - *Concept:* Why full GIN indexes on large JSON cause massive bloat; using compact `jsonb_path_ops` (3x smaller, 2x faster for `@>`) or surgical B-Tree expression indexes on extracted keys (`CREATE INDEX ON table (((payload->>'user_id')::bigint))`).
  - *Location:* [`docs/postgresql_internals_and_optimization_guide.md`](docs/postgresql_internals_and_optimization_guide.md) (Section 4 & 5).
- [x] *Bonus:* **TOAST Architecture & 100M-Row JSON Blueprint:**
  - *Concept:* Handling 2KB-20KB payloads, 8KB page thresholding, `EXTENDED` storage, `lz4` compression, zero-TOAST query discipline, and declarative partitioning.
  - *Location:* [`docs/postgresql_internals_and_optimization_guide.md`](docs/postgresql_internals_and_optimization_guide.md) (Section 1, 2, 5).

---

### Category 3: Machine Learning, Deep Learning & Applied Statistics
- [x] **#2. Poisson Distribution & Queuing Theory in Systems:**
  - *Concept:* Discrete probability distribution modeling independent arrival events over fixed intervals:
    $$P(k \text{ events in interval}) = \frac{\lambda^k e^{-\lambda}}{k!}$$
  - *System Design Applications:* Modeling database lock contention, API rate-limiting, message broker consumer queues, and server arrival rates.
  - *Location:* [`docs/machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 1).
- [x] **#3. Deep Learning Foundations: DNN, CNN, and RNN Architectures:**
  - *DNN (Deep Neural Networks / Multi-Layer Perceptrons):* Fully connected dense layers with non-linear activation functions (ReLU, GELU) for tabular features.
  - *CNN (Convolutional Neural Networks):* Parameter sharing via convolutional kernels, pooling layers, and spatial hierarchies for computer vision.
  - *RNN (Recurrent Neural Networks / LSTMs / GRUs):* Sequential modeling with hidden state recurrent loops; solving vanishing gradients via gating mechanisms.
  - *Location:* [`docs/machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 2).
- [x] **#4. t-SNE (t-Distributed Stochastic Neighbor Embedding):**
  - *Concept:* Non-linear manifold learning algorithm that converts high-dimensional vector embeddings (e.g. 384/1024 dims) into 2D or 3D coordinate space.
  - *Why it matters:* Preserves local neighborhood distances using Student-t distributions, making it the premier tool to visually inspect vector cluster separation and embeddings quality.
  - *Location:* [`docs/machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 3).
- [x] **#11. Chatbot Context Management & Memory Architecture:**
  - *Concept:* Token budgeting and context window management:
    - Sliding Window Buffer (recent $N$ turns)
    - Conversation Summary Buffer (LLM compresses past history)
    - Semantic Memory Injection (retrieving past relevant user preferences via Vector Search / RAG).
  - *Location:* [`docs/machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md) (Section 5).

---

### Category 4: Big Data & Real-Time Stream Processing
- [x] *Completed Foundation:* **Apache Spark Masterclass (4 Notebooks):**
  - Driver/Executor cluster mechanics, Catalyst optimizer, DAG execution, Wide vs. Narrow shuffles, Sort-Merge vs. Broadcast joins, Adaptive Query Execution (AQE), and Skew Salting.
  - *Location:* [`notebooks/spark_tutorial/`](notebooks/spark_tutorial/).
- [ ] **#12. Apache Flink: Real-Time Stream Analytics & Top-K Ranking:**
  - *Concept:* True event-driven stream processing (sub-millisecond latency vs. Spark's micro-batching).
  - *Core Mechanics:* Event-time vs. processing-time, watermarks, sliding/tumbling windows, managed state backends (EmbeddedRocksDB), and maintaining distributed top-K heaps for real-time recommendation feeds.

---

### Category 5: Cloud Infrastructure, Data Engineering & DevOps
- [x] **#15. Kubernetes (K8s) Core Architecture & Deployments:**
  - *Concept:* Container orchestration at scale:
    - Control Plane (API server, etcd, scheduler) vs Worker Nodes (kubelet, kube-proxy, containerd).
    - Pods, ReplicaSets, Deployments (stateless services).
    - StatefulSets & Persistent Volume Claims (PVCs) for databases (Postgres, Milvus DataNodes).
    - Services (ClusterIP, NodePort, LoadBalancer, Headless) and Ingress.
    - Probes (Liveness, Readiness, Startup) and Resource Requests vs. Limits.
  - *Location:* [`docs/kubernetes_getting_started_guide.md`](docs/kubernetes_getting_started_guide.md).
- [x] **#16. Apache Airflow: Workflow Orchestration & Data Pipelines:**
  - *Concept:* Programmatic workflow management:
    - Authoring Directed Acyclic Graphs (DAGs) in Python using modern TaskFlow API (`@task`, `@dag`).
    - Operators vs Sensors vs Hooks, deferrable operators and Triggerer.
    - Task dependencies, retries, SLAs, and XComs (custom S3 backends).
    - Production orchestrations: Scheduling daily Spark ETL jobs, validating data quality, and triggering Milvus vector refreshes.
  - *Location:* [`docs/airflow_getting_started_guide.md`](docs/airflow_getting_started_guide.md).

---

### Category 6: Observability, SRE & Developer Productivity
- [x] **#17. Observability: Prometheus, Grafana Dashboards & PagerDuty:**
  - *Metrics Scraping:* Prometheus pull model for node exporters and database metrics.
  - *PromQL Masterclass:* `rate()`, `histogram_quantile(0.95, ...)`, RED & USE methods.
  - *Visualization:* Building Grafana panels for query latency (p50, p95, p99), memory saturation, and CPU load.
  - *Alerting & Incident Response:* Grafana alerting engine lifecycle (Pending $\to$ Firing), label-based routing, and PagerDuty Events API v2 escalation policies.
  - *Location:* [`docs/grafana_dashboards_alerts_and_pagerduty.md`](docs/grafana_dashboards_alerts_and_pagerduty.md).
- [x] **#18. Developer Productivity & ChatOps (Slack Platform):**
  - *Concept:* Turning Slack into an operational command center:
    - Keyboard shortcuts, advanced search syntax, and team channel naming architecture.
    - Slack Workflow Builder for automated triage and approvals.
    - Incoming webhooks and rich Block Kit JSON formatting.
    - Airflow task failure callbacks posting real-time alert cards to Slack.
  - *Location:* [`docs/slack_developer_productivity_and_chatops.md`](docs/slack_developer_productivity_and_chatops.md).

---

## 🔗 Existing Workspace Resources Quick Reference

1. **Milvus Complete Master Guide:** [`docs/milvus_complete_guide.md`](docs/milvus_complete_guide.md)
2. **Milvus Step-by-Step Hands-On Notebook:** [`notebooks/milvus_step_by_step_guide.ipynb`](notebooks/milvus_step_by_step_guide.ipynb)
3. **Machine Learning Foundations & Architectures:** [`docs/machine_learning_fundamentals_and_models.md`](docs/machine_learning_fundamentals_and_models.md)
4. **PostgreSQL Internals & 100M Row JSON Guide:** [`docs/postgresql_internals_and_optimization_guide.md`](docs/postgresql_internals_and_optimization_guide.md)
5. **PostgreSQL EXPLAIN In-Depth Field Guide:** [`docs/understanding_postgres_explain.md`](docs/understanding_postgres_explain.md)
6. **Kubernetes Getting Started & Production Guide:** [`docs/kubernetes_getting_started_guide.md`](docs/kubernetes_getting_started_guide.md)
7. **Apache Airflow Getting Started & Production Guide:** [`docs/airflow_getting_started_guide.md`](docs/airflow_getting_started_guide.md)
8. **Observability: Grafana Dashboards, Alerts & PagerDuty:** [`docs/grafana_dashboards_alerts_and_pagerduty.md`](docs/grafana_dashboards_alerts_and_pagerduty.md)
9. **Slack Developer Productivity & ChatOps Automation:** [`docs/slack_developer_productivity_and_chatops.md`](docs/slack_developer_productivity_and_chatops.md)
10. **Spark Masterclass Series (4 Executed Notebooks):** [`notebooks/spark_tutorial/`](notebooks/spark_tutorial/)
11. **Envelope Encryption Guide:** [`docs/envelope_encryption_guide.md`](docs/envelope_encryption_guide.md)
