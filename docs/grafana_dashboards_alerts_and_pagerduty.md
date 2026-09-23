# Production Observability: Grafana Dashboards, Alerts & PagerDuty Integration

A comprehensive, senior-level guide to building enterprise-grade observability pipelines. Covers PromQL fundamentals, RED/USE dashboard engineering, Grafana alerting engines, PagerDuty escalation policies, and preventing on-call fatigue.

---

## Table of Contents
1. [The Modern Observability Stack (Mental Model)](#1-the-modern-observability-stack-mental-model)
2. [The Telemetry Pipeline Architecture](#2-the-telemetry-pipeline-architecture)
3. [PromQL Masterclass: The Language Behind the Metrics](#3-promql-masterclass)
   - [Metric Types: Counter, Gauge, Histogram, Summary](#metric-types)
   - [Rate vs Irate](#rate-vs-irate)
   - [Quantiles & Latency Percentiles (p50, p95, p99)](#quantiles-and-latency-percentiles)
   - [Vector Matching & Aggregations](#vector-matching--aggregations)
4. [Building Production Grafana Dashboards](#4-building-production-grafana-dashboards)
   - [The RED Method (For Services & APIs)](#the-red-method)
   - [The USE Method (For Infrastructure & DBs)](#the-use-method)
   - [Panel Types & Visual Best Practices](#panel-types)
   - [Dynamic Dashboard Variables & Templating](#dynamic-dashboard-variables)
5. [Grafana Alerting Engine](#5-grafana-alerting-engine)
   - [Alert Rule Architecture: Query -> Reduce -> Math -> Threshold](#alert-rule-architecture)
   - [The "Pending" vs "Firing" Lifecycle (Eliminating Flapping)](#the-pending-vs-firing-lifecycle)
   - [Writing Context-Rich Annotations and Runbooks](#writing-context-rich-annotations)
6. [PagerDuty Integration & Escalation Policies](#6-pagerduty-integration--escalation-policies)
   - [How PagerDuty Works (Services, Schedules, Escalation Paths)](#how-pagerduty-works)
   - [Setting Up Events API v2 in PagerDuty](#setting-up-events-api-v2)
   - [Connecting Grafana to PagerDuty Contact Points](#connecting-grafana-to-pagerduty)
   - [Notification Policies & Label-Based Routing](#notification-policies--label-based-routing)
   - [Alert Grouping & Deduplication](#alert-grouping--deduplication)
7. [Production Incident Runbook & Best Practices](#7-production-incident-runbook--best-practices)

---

## 1. The Modern Observability Stack (Mental Model)

Monitoring is not just about knowing when a server catches fire. True **Observability** allows you to infer the internal health of a complex distributed system (K8s, Postgres, Milvus, microservices) based on its external outputs.

The three pillars of telemetry:
1. **Metrics**: Numeric time-series values aggregated over intervals (e.g., `cpu_utilization = 82%`, `http_requests_total = 14,200`). *Best for: Dashboards, alerting, anomaly detection.*
2. **Logs**: Discrete timestamped text events (e.g., `2026-09-23 10:14:02 ERROR: Postgres connection timeout`). *Best for: Root-cause debugging after an alert fires.*
3. **Traces**: Distributed request propagation through microservices (e.g., Request `req-984` spent 20ms in Gateway, 450ms in Milvus Vector Search, 15ms in Redis). *Best for: Pinpointing bottlenecks in microservices.*

Grafana is the **single pane of glass** unifying metrics (Prometheus/Mimir), logs (Loki), and traces (Tempo).

---

## 2. The Telemetry Pipeline Architecture

```
                    END-TO-END OBSERVABILITY & ALERTING PIPELINE
 +----------------------------------------------------------------------------------+
 | 1. TELEMETRY SOURCES                                                             |
 |   [ Node Exporter ]      [ cAdvisor / K8s ]      [ Vector DB / App / Postgres ]  |
 |   (CPU, RAM, Disk, Net)  (Pod & Container stats) (p99 latency, query RPS, errors)|
 +------------------+------------------+--------------------+-----------------------+
                    |                  |                    |
                    | (PULL via HTTP /metrics every 15s)    |
                    v                  v                    v
 +----------------------------------------------------------------------------------+
 | 2. TIME-SERIES DATABASE (Prometheus / Thanos / Cortex)                           |
 |   - Scrapes targets                                                              |
 |   - Stores metrics on disk / TSDB blocks                                         |
 |   - Evaluates PromQL queries                                                     |
 +-------------------------------------+--------------------------------------------+
                                       |
                                       v (PromQL API)
 +----------------------------------------------------------------------------------+
 | 3. VISUALIZATION & ALERTING (Grafana)                                            |
 |   - Interactive Dashboards (RED & USE panels)                                    |
 |   - Unified Alerting Engine (Evaluates rules: e.g. p99 > 500ms for 5m)           |
 +-------------------------------------+--------------------------------------------+
                                       |
                   +-------------------+-------------------+
                   | (Alert Fired)                         | (Alert Fired)
                   | severity = warning                    | severity = critical
                   v                                       v
 +------------------------------------+  +------------------------------------------+
 | Slack / Teams Channel              |  | PagerDuty Events API v2                  |
 | Channel: #alerts-team-platform     |  | - Service: Production-Core               |
 | (For informational/triage awareness|  | - Escalation Policy:                     |
 |  No one gets woken up)             |  |    1. Push notification & SMS to Primary |
 |                                    |  |    2. Call Secondary after 15 minutes    |
 +------------------------------------+  +------------------------------------------+
```

---

## 3. PromQL Masterclass

Prometheus Query Language (PromQL) is a read-only, functional query language designed for fast aggregation of multi-dimensional time series.

### Metric Types

1. **Counter**: A cumulative metric that can **only increase or reset to zero on restart** (e.g., `http_requests_total`, `bytes_transmitted`). Never query a raw counter directly—always wrap it in `rate()` or `increase()`.
2. **Gauge**: A metric that can go **up and down** arbitrarily (e.g., `memory_usage_bytes`, `cpu_utilization`, `active_connections`).
3. **Histogram**: Samples observations (usually request durations or response sizes) and counts them into configurable buckets (e.g., `http_request_duration_seconds_bucket`). Includes `_count` and `_sum`.
4. **Summary**: Similar to histogram, but calculates client-side quantiles directly. (Histograms are preferred because summaries cannot be aggregated across multiple pods).

### Rate vs Irate

Both calculate the per-second average rate of increase of a counter:

- **`rate(http_requests_total[5m])`**: Calculates the average rate over the entire 5-minute window. **Use this for alerting and dashboards** because it smooths out temporary spikes.
- **`irate(http_requests_total[2m])`**: Calculates the "instant rate" using only the last two data points in the window. **Use this only for zooming into high-frequency, jittery spikes during live triage.**

### Quantiles and Latency Percentiles

Averages lie. If 99 queries take 10ms and 1 query takes 10,000ms, the average is 110ms—which hides the fact that users are experiencing horrific 10-second lag spikes. Always measure **Percentiles (p50, p95, p99)**.

To calculate the 99th percentile request latency across all API pods:

```promql
histogram_quantile(
  0.99,
  sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[5m])) by (le)
)
```

> [!NOTE]
> The `by (le)` clause is mandatory. `le` stands for *"less than or equal to"*—the bucket label generated by Prometheus histograms.

### Vector Matching & Aggregations

```promql
# 1. Total Requests per second grouped by HTTP status code
sum(rate(http_requests_total[5m])) by (status_code)

# 2. Memory utilization percentage per node
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# 3. Overall error rate percentage (HTTP 5xx / Total requests)
(
  sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(http_requests_total[5m]))
) * 100
```

---

## 4. Building Production Grafana Dashboards

### The RED Method (For Services & APIs)
For every microservice, API, or query layer (e.g., Milvus search proxy):
- **Rate**: Requests handled per second (`sum(rate(http_requests_total[1m]))`).
- **Errors**: Number of failed requests per second (`sum(rate(http_requests_total{status=~"5.."}[1m]))`).
- **Duration**: How long requests take (p50, p95, p99 latency percentiles).

### The USE Method (For Infrastructure & DBs)
For physical nodes, VMs, storage disks, and memory:
- **Utilization**: % of time the resource was busy (e.g., CPU % active, Disk I/O busy time).
- **Saturation**: Degree of queued extra work that cannot be processed (e.g., Linux load average, disk queue length, thread pool backlog).
- **Errors**: Count of hardware or kernel error events (e.g., network packet drops, disk ECC errors).

### Panel Types

| Panel Type | Best For | Example Query / Use Case |
|---|---|---|
| **Time Series** | Historical trend lines, latency distributions over time. | p99 latency curve over 24 hours. |
| **Stat** | Big numerical KPIs with colored background thresholds. | Current Cluster Active Pods: `count(kube_pod_info)`. |
| **Gauge** | Visual dials showing percentage capacity. | Heap memory utilization (0% - 100%). |
| **Bar Chart / Histogram** | Comparing discrete categories or bucket counts. | Traffic volume broken down by HTTP endpoint. |
| **Heatmap** | Multi-dimensional latency visualization over time. | Shows multi-modal latency distributions (bimodal spikes). |

### Dynamic Dashboard Variables
Instead of creating 20 dashboards for 20 microservices, use **Variables** so users can select filters from a dropdown menu.

In Dashboard Settings $\to$ Variables:
1. **Name**: `environment`
   - Type: `Query`
   - Query: `label_values(up, env)`
2. **Name**: `service`
   - Type: `Query`
   - Query: `label_values(http_requests_total{env="$environment"}, service)`
3. Query inside panels:
   ```promql
   rate(http_requests_total{env="$environment", service="$service"}[5m])
   ```

---

## 5. Grafana Alerting Engine

### Alert Rule Architecture

```
+--------------------------------------------------------------------+
| 1. QUERY (A)                                                       |
|    PromQL: sum(rate(http_requests_total{status=~"5.."}[5m]))       |
|            / sum(rate(http_requests_total[5m])) * 100              |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
| 2. REDUCE EXPRESSION (B)                                           |
|    Function: Last / Mean / Max over input query A                  |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
| 3. THRESHOLD EXPRESSION (C)                                        |
|    Condition: If $B > 5.0 (Error rate > 5%)                        |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
| 4. EVALUATION LIFECYCLE                                            |
|    Evaluate every: 1 minute | For: 5 minutes                       |
+--------------------------------------------------------------------+
```

### The Pending vs Firing Lifecycle

Alert fatigue destroys engineering teams. If a network blip lasts 2 seconds, you should **never** wake up an engineer on call.

```
       Metric exceeds threshold
                 |
                 v
   +----------------------------+
   |      State: PENDING        |  (Condition is true, but timer running)
   +--------------+-------------+
                  |
     Did condition persist for
     entire 'For: 5m' duration?
             /          \
       YES  /            \  NO (Metric dipped back down)
           v              v
+---------------------+  +--------------------+
|    State: FIRING    |  |   State: NORMAL    |
| (Page sent to oncall|  |  (Silently dropped |
|  & posted to Slack) |  |   no page sent)    |
+---------------------+  +--------------------+
```

### Writing Context-Rich Annotations

Every alert MUST tell the responding engineer what broke, why it matters, and how to fix it:

```yaml
labels:
  severity: critical
  team: data-platform
  service: milvus-vector-db

annotations:
  summary: "Milvus Search p99 latency exceeded 1500ms on cluster {{ $labels.cluster }}"
  description: "Current p99 search latency is {{ $values.B.Value }}ms. Users are experiencing search timeouts."
  runbook_url: "https://wiki.mycompany.com/runbooks/milvus-high-latency"
  dashboard_url: "https://grafana.mycompany.com/d/milvus-overview?var-cluster={{ $labels.cluster }}"
```

---

## 6. PagerDuty Integration & Escalation Policies

### How PagerDuty Works

- **Services**: Represents an entity you monitor (e.g., `Production Milvus Cluster`, `Payment Gateway`).
- **Escalation Policies**: Dictates who gets notified and when:
  - *Level 1*: Push notification and SMS to Primary On-Call engineer immediately.
  - *Level 2*: If unacknowledged within 15 minutes, phone call to Secondary On-Call engineer.
  - *Level 3*: If unacknowledged within 30 minutes, escalate to Engineering Director.
- **Schedules**: Rotations (daily, weekly shifts) defining who is on primary/secondary duty.

### Setting Up Events API v2 in PagerDuty

1. In PagerDuty: Go to **Services** $\to$ **Service Directory** $\to$ Click your Service.
2. Select **Integrations** tab $\to$ Click **Add another integration**.
3. Search for **Grafana** (or **Events API v2**).
4. Click Add. PagerDuty will generate an **Integration Key** (a 32-character routing key, e.g., `d41d8cd98f00b204e9800998ecf8427e`).

### Connecting Grafana to PagerDuty

In Grafana:
1. Navigate to **Alerts & IRM** $\to$ **Contact points**.
2. Click **Add contact point**.
3. Name: `PagerDuty-Production-Sev1`.
4. Integration type: `PagerDuty`.
5. Enter your **Integration Key**.
6. Check **Auto-resolve alerts**: When the metric returns to normal, Grafana sends a `resolve` event to PagerDuty, closing the incident automatically without human intervention!

### Notification Policies & Label-Based Routing

You should never send all alerts to PagerDuty. Route alerts dynamically using labels:

```
                            ALERT GENERATED
                                   |
                     Inspect label: `severity`
                       /           |           \
         severity = critical   severity = warn   severity = info
                     /             |               \
                    v              v                v
            [ PagerDuty Sev-1 ]  [ Slack #alerts ]  [ Internal Log ]
            (Pages engineer)     (Channel post)     (Ignored)
```

In Grafana **Notification Policies**:
- **Default Policy**: Send to Slack `#alerts-general`.
- **Nested Policy 1**:
  - Matcher: `severity = critical`
  - Contact Point: `PagerDuty-Production-Sev1`
  - Group By: `["alertname", "cluster", "service"]`
- **Nested Policy 2**:
  - Matcher: `severity = warning`
  - Contact Point: `Slack-#team-data-platform`

### Alert Grouping & Deduplication

If your primary PostgreSQL database goes down, 50 microservices will immediately fail and fire alerts simultaneously. 
Without alert grouping, the on-call engineer's phone will ring 50 times in 30 seconds.

- **`group_by: ['cluster', 'alertname']`**: Combines multiple identical alerts into a single PagerDuty incident.
- **`group_wait: 30s`**: Wait 30 seconds before sending the initial notification to batch simultaneous failures together.
- **`group_interval: 5m`**: How often to send updates about new alerts added to an existing group.
- **`repeat_interval: 4h`**: How long to wait before re-paging about an already acknowledged, ongoing alert.

---

## 7. Production Incident Runbook & Best Practices

1. **Only Page on User-Impacting Symptoms (SLOs)**: Never page an engineer because a CPU reached 85%. Page them because the API error rate > 2% or latency > 1s. High CPU with fast, error-free responses is NOT an emergency.
2. **Every Page Must Be Actionable**: If an engineer wakes up, looks at the alert, and has no action to take except "watch it fix itself", **delete the alert immediately**.
3. **Always Include a Runbook Link**: Under high stress at 3:00 AM, engineers should not have to guess what commands to run. The alert annotation must link to an explicit Markdown runbook with recovery steps.
4. **Automate Self-Healing First**: If the standard fix for an alert is restarting a pod or clearing temporary cache, implement a Kubernetes liveness probe or an automated cronjob before adding a human pager.
