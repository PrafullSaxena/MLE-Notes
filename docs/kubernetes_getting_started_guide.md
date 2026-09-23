# The Definitive Kubernetes (K8s) Getting Started & Production Guide

A practical, senior-level guide to understanding Kubernetes architecture, core primitives, networking, storage, deployment patterns, and day-to-day operations.

---

## Table of Contents
1. [Why Kubernetes? (The Mental Model)](#1-why-kubernetes-the-mental-model)
2. [Kubernetes Architecture Demystified](#2-kubernetes-architecture-demystified)
   - [The Control Plane](#the-control-plane)
   - [The Worker Nodes](#the-worker-nodes)
   - [The Reconciliation Loop](#the-reconciliation-loop-declarative-vs-imperative)
3. [Core Primitives & Workload Objects](#3-core-primitives--workload-objects)
   - [Pods: The Atomic Unit](#pods-the-atomic-unit)
   - [Deployments & ReplicaSets](#deployments--replicasets)
   - [StatefulSets: For Stateful Systems (DBs, Milvus, Kafka)](#statefulsets-for-stateful-systems)
   - [DaemonSets & Jobs / CronJobs](#daemonsets--jobs--cronjobs)
4. [Networking & Service Discovery](#4-networking--service-discovery)
   - [The K8s Networking Model](#the-k8s-networking-model)
   - [Services: ClusterIP vs NodePort vs LoadBalancer vs Headless](#services-explained)
   - [Ingress Controllers & API Gateways](#ingress-controllers--api-gateways)
5. [Configuration & Secret Management](#5-configuration--secret-management)
   - [ConfigMaps & Secrets](#configmaps--secrets)
   - [Environment Variables vs Volume Mounts](#env-vars-vs-volume-mounts)
6. [Storage: Volumes, PVs, PVCs & StorageClasses](#6-storage-volumes-pvs-pvcs--storageclasses)
7. [Resource Management & Scheduling](#7-resource-management--scheduling)
   - [Requests vs Limits (CPU & Memory)](#requests-vs-limits)
   - [QoS Classes (Guaranteed, Burstable, BestEffort)](#qos-classes)
   - [Node Affinity, Taints & Tolerations](#node-affinity-taints--tolerations)
8. [Health Checks: Liveness, Readiness & Startup Probes](#8-health-checks-probes)
9. [Hands-On Lab: Deploying a Multi-Tier Application](#9-hands-on-lab-deploying-a-multi-tier-application)
10. [Senior kubectl Cheat Sheet & Troubleshooting Runbook](#10-senior-kubectl-cheat-sheet--troubleshooting-runbook)

---

## 1. Why Kubernetes? (The Mental Model)

Before containers, applications ran on Bare Metal or Virtual Machines. When traffic spiked or a server crashed:
- Someone manually provisioned a VM.
- Ran Ansible/Chef scripts.
- Configured load balancer IPs.
- Restarted failed processes.

Docker solved the **packaging and runtime isolation** problem: *"It runs on my machine, so it runs anywhere."*
However, Docker alone does not answer:
- How do you heal a container when it segfaults at 3 AM?
- How do you scale from 2 containers to 20 containers during flash sales?
- How do you perform zero-downtime rolling deploys?
- How do 50 microservices discover each other's dynamic IP addresses?

**Kubernetes (K8s)** is a **distributed operating system** and container orchestrator. You write a declarative manifest (`YAML`) stating:
> *"I want 5 replicas of service `api-gateway` running version `v1.4.2`, each with at least 500m CPU and 1GB RAM, exposed on internal port 8080."*

Kubernetes takes that desired state, continuously inspects the real world, and executes actions to eliminate any divergence.

---

## 2. Kubernetes Architecture Demystified

```
                          KUBERNETES CLUSTER ARCHITECTURE
  +-------------------------------------------------------------------------------+
  |                             CONTROL PLANE (Master)                            |
  |                                                                               |
  |  kubectl / Helm                   +----------------------------------------+  |
  |        |                          |        kube-controller-manager         |  |
  |        v                          |  (Node, ReplicaSet, EndpointSlice...)  |  |
  |  +--------------------+           +-------------------+--------------------+  |
  |  |  kube-apiserver   |<-------------------------------+                       |
  |  | (Auth, Validating, |                                                       |
  |  |   REST gateway)    |<----------+-------------------+                       |
  |  +---------+----------+           |  kube-scheduler   |                       |
  |            ^                      | (Filters & Scores)|                       |
  |            |                      +-------------------+                       |
  |            v                                                                  |
  |  +--------------------+                                                       |
  |  |       etcd         | (Consistent, distributed, raft-backed key-value store)|
  |  +--------------------+                                                       |
  +------------+------------------------------------------------------------------+
               |
               | (Secure mTLS communication)
               v
  +-------------------------------------+   +-------------------------------------+
  |          WORKER NODE 1              |   |          WORKER NODE 2              |
  |  +-------------------------------+  |   |  +-------------------------------+  |
  |  |            kubelet            |  |   |  |            kubelet            |  |
  |  | (Ensures Pod containers run)  |  |   |  | (Ensures Pod containers run)  |  |
  |  +---------------+---------------+  |   |  +---------------+---------------+  |
  |                  | (CRI)            |   |                  | (CRI)            |
  |  +---------------v---------------+  |   |  +---------------v---------------+  |
  |  |   containerd / CRI-O runtime  |  |   |  |   containerd / CRI-O runtime  |  |
  |  +-------------------------------+  |   |  +-------------------------------+  |
  |  |          kube-proxy           |  |   |  |          kube-proxy           |  |
  |  | (iptables/IPVS packet routing)|  |   |  | (iptables/IPVS packet routing)|  |
  |  +-------------------------------+  |   |  +-------------------------------+  |
  |                                     |   |                                     |
  |   [ Pod A ]       [ Pod B ]         |   |   [ Pod C ]       [ Pod D ]         |
  |  (App: v1.0)     (DB Proxy)         |   |  (App: v1.0)     (Worker)           |
  +-------------------------------------+   +-------------------------------------+
```

### The Control Plane

1. **`kube-apiserver`**: The front door to K8s. It exposes a JSON/REST API. Every component (kubectl, scheduler, kubelet) talks **only** to the API server. No component touches `etcd` directly. It performs Authentication, Authorization (RBAC), and Admission Control.
2. **`etcd`**: The single source of truth. A strongly consistent, distributed key-value store using the Raft consensus protocol. It stores cluster state, configuration, and secret data. **Backing up etcd equals backing up your entire cluster.**
3. **`kube-scheduler`**: Watches for newly created Pods with no assigned node. It evaluates node constraints (resource requests, taints, affinity, port conflicts), **filters** invalid nodes, **scores** remaining nodes, and assigns the Pod to the winning node.
4. **`kube-controller-manager`**: Runs continuous control loops (controllers). Examples:
   - *Node Lifecycle Controller*: Notices if a node stops sending heartbeats and evicts pods after timeout.
   - *ReplicaSet Controller*: Ensures the count of running pods matches desired `replicas: N`.
   - *Endpoints/EndpointSlice Controller*: Links Services to live Pod IP addresses.

### The Worker Nodes

1. **`kubelet`**: The node agent. It registers the node with the API server, watches for PodSpecs assigned to its node, and talks to the container runtime via CRI (Container Runtime Interface) to pull images, start containers, and run health probes.
2. **`Container Runtime`** (`containerd` or `CRI-O`): Low-level engine that creates Linux namespaces, cgroups, and root filesystems to actually run container processes.
3. **`kube-proxy`**: Network proxy running on each node. It programs kernel packet-filtering rules (`iptables` or `IPVS`) so that requests sent to a virtual Service IP (ClusterIP) get NATed and load-balanced to healthy Pod IPs.

### The Reconciliation Loop (Declarative vs Imperative)

```
        +-----------------------------------------------+
        |               DESIRED STATE                   |
        |             (Stored in etcd)                  |
        +-----------------------+-----------------------+
                                |
                                v
     +-------------------> OBSERVE (Query API Server)
     |                          |
     |                          v
     |                     DIFF CHECK
     |               (Desired == Current?)
     |                   /             \
     |             YES  /               \  NO
     |                 v                 v
     |          Sleep & Repeat        ACT (Create/Kill/Update)
     +-----------------------------------+
```
Instead of executing imperative commands (`start server`, `restart if died`), K8s continuously observes the current state and runs controllers to reconcile it with your declared YAML state.

---

## 3. Core Primitives & Workload Objects

### Pods: The Atomic Unit
A **Pod** is the smallest deployable unit in Kubernetes. A Pod wraps one or more tightly coupled containers that:
- Share the same Network namespace (same IP address, same `localhost`, can communicate over local IPC).
- Share the same Storage volumes.
- Are co-located and co-scheduled on the exact same physical node.

> [!NOTE]
> 95% of Pods are **single-container Pods**. Multi-container Pods are reserved for helper patterns like the **Sidecar** (e.g., Envoy proxy, log shipper, secret injector) or **Init Containers** (pre-flight DB migrations before the app boots).

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: auth-service
  labels:
    app: auth
    env: production
spec:
  containers:
  - name: server
    image: myregistry.com/auth:v1.2.0
    ports:
    - containerPort: 8080
```

### Deployments & ReplicaSets
Never deploy naked Pods in production. If a node dies, naked Pods die with it.
Instead, use a **Deployment**:
1. You define a **Deployment**.
2. The Deployment manages a **ReplicaSet** (version tracking).
3. The ReplicaSet ensures the specified number of Pods exist.

```
Deployment (my-app)
   |
   +---> ReplicaSet v1 (active: 3 pods)
   |        |--> Pod 1, Pod 2, Pod 3
   |
   +---> [Rollout Update to v2]
            |
            v
         ReplicaSet v2 (spin up 1 pod -> scale down v1 by 1 -> repeat)
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: default
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max 4 pods during deployment
      maxUnavailable: 0  # Never drop below 3 ready pods
  selector:
    matchLabels:
      app: payment
  template:
    metadata:
      labels:
        app: payment
    spec:
      containers:
      - name: payment-api
        image: payment-api:2.1.0
        ports:
        - containerPort: 8000
```

### StatefulSets: For Stateful Systems
Deployments are designed for **stateless** apps (where any pod can replace any other). 
Databases, Milvus, Postgres, Kafka, and Zookeeper require:
1. **Stable, persistent network identities**: `milvus-0`, `milvus-1`, `milvus-2` (not random hashes like `app-7df4f9bc-xk2d`).
2. **Dedicated, persistent storage per pod**: When `milvus-0` restarts or migrates to another node, it reconnects to the exact same disk volume (`data-milvus-0`).
3. **Ordered deployment and termination**: Pod 0 boots first, gets ready, then Pod 1 boots. Shutdown occurs in reverse order.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-cluster
spec:
  serviceName: "postgres-headless"
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        volumeMounts:
        - name: pgdata
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: pgdata
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "standard-ssd"
      resources:
        requests:
          storage: 100Gi
```

### DaemonSets & Jobs / CronJobs
- **DaemonSet**: Ensures that **all (or selected) nodes run exactly one copy** of a Pod. Used for cluster-wide infrastructure: logging agents (`Fluentbit`, `Promtail`), monitoring agents (`Node Exporter`, `Datadog`), and network plugins (`Cilium`, `Calico`).
- **Job**: Runs a task to completion (exit code 0) rather than keeping it running (e.g., one-off DB schema migration, Spark batch driver).
- **CronJob**: Runs a Job on a scheduled time table (e.g., `0 2 * * *` nightly data backup).

---

## 4. Networking & Service Discovery

### The K8s Networking Model
Kubernetes enforces fundamental networking guarantees:
1. Every Pod gets its own unique IP address within the cluster network (Pod CIDR).
2. Any Pod can communicate with any other Pod directly using IP, without NAT (no port mapping conflicts).
3. Agents on a node (like kubelet) can communicate with all Pods on that node.

### Services Explained
Because Pods are ephemeral (they die and are recreated with new IPs), clients cannot rely on Pod IP addresses. A **Service** provides a **stable virtual IP (ClusterIP)** and DNS name that load-balances traffic across a set of Pods matching a label selector.

```
 Client Request -> http://payment-service:8000
                         |
                         v (Service ClusterIP: 10.96.100.45)
                         |
           +-------------+-------------+
           | (kube-proxy iptables load balancing)
           v                           v
     Pod 1 (10.244.1.12)         Pod 2 (10.244.2.87)
```

| Service Type | Scope & Mechanics | Primary Use Case |
|---|---|---|
| **`ClusterIP`** (Default) | Allocates an internal virtual IP reachable **only from inside** the cluster. | Microservice-to-microservice communication, internal DBs. |
| **`NodePort`** | Allocates a static high-range port (`30000-32767`) on **every worker node IP**. | On-premises legacy load balancers, direct node access. |
| **`LoadBalancer`** | Integrates with cloud providers (AWS ELB/ALB, GCP Cloud LB) to provision an external public IP. | Exposing an internet-facing app directly (costs 1 cloud LB per service). |
| **`Headless`** (`clusterIP: None`) | No virtual IP or proxying. DNS query returns the list of all individual backing Pod IPs directly. | StatefulSets, database primary-replica routing, Milvus internal nodes. |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: payment-service
spec:
  type: ClusterIP
  selector:
    app: payment
  ports:
  - port: 8000        # Port exposed by the Service inside cluster
    targetPort: 8000  # Port where the container is listening
```

### Ingress Controllers & API Gateways
Instead of creating an expensive cloud `LoadBalancer` for every single microservice, an **Ingress** routes HTTP/HTTPS traffic from outside the cluster to internal Services using domain names and URL paths (L7 routing).

```
                      Internet Request
                             |
                   Cloud Load Balancer (Public IP)
                             |
                Ingress Controller (NGINX / Envoy)
                             |
         +-------------------+-------------------+
         | Path: /api/v1/auth                    | Path: /api/v1/search
         v                                       v
    Service: auth                           Service: search
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  rules:
  - host: api.mycompany.com
    http:
      paths:
      - path: /auth
        pathType: Prefix
        backend:
          service:
            name: auth-service
            port:
              number: 8080
      - path: /search
        pathType: Prefix
        backend:
          service:
            name: search-service
            port:
              number: 8000
```

---

## 5. Configuration & Secret Management

Never hardcode credentials, database endpoints, or tunable parameters into container images.

- **`ConfigMap`**: Plaintext configuration data (properties, JSON, NGINX conf files).
- **`Secret`**: Sensitive data (tokens, private keys, passwords) encoded in Base64 (or encrypted at rest via KMS plugin in etcd).

### Env Vars vs Volume Mounts

```yaml
# 1. ConfigMap Definition
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "info"
  MILVUS_PORT: "19530"
  settings.json: |
    {
      "cache_size_mb": 512,
      "max_workers": 8
    }
---
# 2. Consuming via Environment Variables & File Mounts
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: server
  template:
    metadata:
      labels:
        app: server
    spec:
      containers:
      - name: server
        image: app-server:v1
        env:
        # Single value from ConfigMap
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: LOG_LEVEL
        # Secret reference
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        # Volume mount for config files (updates live without pod restart!)
        volumeMounts:
        - name: config-volume
          mountPath: /etc/app/config
          readOnly: true
      volumes:
      - name: config-volume
        configMap:
          name: app-config
```

> [!TIP]
> **Live Reloads**: When a ConfigMap mounted as a **Volume** is modified, Kubernetes automatically updates the mounted file within ~60 seconds without restarting the container. In contrast, values passed as **Environment Variables** are frozen at pod boot time and require a pod rollout restart (`kubectl rollout restart deployment/<name>`).

---

## 6. Storage: Volumes, PVs, PVCs & StorageClasses

Containers have ephemeral filesystems. When a container crashes, its local files are destroyed. To persist data:

```
Developer declares intent:            StorageClass talks to Cloud / SAN:
+------------------------+           +---------------------------------+
| PersistentVolumeClaim  |  ------>  | Dynamic Provisioner             |
| (PVC: "I need 100GB")  |           | (AWS EBS / GCP PD / Ceph / NFS) |
+-----------+------------+           +----------------+----------------+
            |                                         |
            v                                         v
+-------------------------------------------------------+
| PersistentVolume (PV: Actual cluster storage resource)|
+-------------------------------------------------------+
            |
            v Mounted into Pod
    /var/lib/milvus/data
```

1. **StorageClass**: The blueprint defining *how* storage is created (e.g., AWS GP3 EBS, Google SSD, NVMe).
2. **PersistentVolume (PV)**: An actual physical or virtual disk allocated in the infrastructure.
3. **PersistentVolumeClaim (PVC)**: A developer's request for storage ("give me 50GB `ReadWriteOnce` storage").
4. **Access Modes**:
   - `ReadWriteOnce` (RWO): Mounted as read-write by a single node (standard block storage like AWS EBS).
   - `ReadOnlyMany` (ROX): Mounted read-only by many nodes simultaneously.
   - `ReadWriteMany` (RWX): Mounted read-write by many nodes simultaneously (requires distributed filesystems like NFS, AWS EFS, CephFS).

---

## 7. Resource Management & Scheduling

Misconfiguring resources is the **#1 cause of production outages** in Kubernetes.

### Requests vs Limits

```
  Node Total Capacity: 4 CPU, 8GB RAM
  +--------------------------------------------------------------------+
  | [ Pod 1: Request 1 CPU ]   [ Pod 2: Request 2 CPU ]   [ Free: 1 CPU]
  +--------------------------------------------------------------------+
  Schedulers ONLY consider REQUESTS when deciding where to place a Pod!
```

- **`requests`**: Guaranteed minimum reserved for the container. The scheduler uses this to pick a node.
- **`limits`**: Maximum cap the container is allowed to consume.
  - If a container exceeds its **Memory Limit** $\to$ Kernel OOM-killer immediately terminates it (`Exit Code 137`, `OOMKilled`).
  - If a container exceeds its **CPU Limit** $\to$ The Linux Completely Fair Scheduler (CFS) **throttles** its CPU cycles (causes latency spikes, but does NOT kill the pod).

```yaml
resources:
  requests:
    cpu: "500m"     # 500 millicores = 0.5 vCPU
    memory: "512Mi" # 512 Mebibytes
  limits:
    cpu: "2"        # 2 vCPUs
    memory: "2Gi"   # 2 Gibibytes
```

### QoS Classes
Kubernetes assigns each Pod a Quality of Service (QoS) class, which dictates node eviction priority during memory starvation:

1. **`Guaranteed`**: `requests == limits` for both CPU and Memory for all containers. *Lowest eviction priority (safest).*
2. **`Burstable`**: `requests < limits`. Has guaranteed baseline but can burst. *Medium eviction priority.*
3. **`BestEffort`**: No requests or limits specified. *First in line to be slaughtered when node runs out of RAM.*

### Node Affinity, Taints & Tolerations

- **Taints & Tolerations**: Keep pods away from specific nodes.
  - A node is tainted: `taint: gpu=true:NoSchedule`.
  - Normal pods cannot run on this node.
  - Only pods with a matching **toleration** can schedule here (e.g., GPU training jobs).
- **Node Affinity**: Pulls pods toward specific nodes.
  - `nodeAffinity`: "Run this Milvus query node only on nodes labeled `instance-type=compute-optimized`".

---

## 8. Health Checks: Probes

Without probes, K8s only knows if the process inside the container is running. If your Python or Java app enters a deadlock or memory leak where it cannot respond to HTTP requests, K8s thinks it is completely healthy.

```
       Startup Probe                         Readiness Probe                       Liveness Probe
   [ Is app done booting? ]           [ Can app handle live user traffic? ]    [ Is app deadlocked / broken? ]
              |                                        |                                      |
     YES: Stop checking,                      NO: Remove Pod IP from                NO: KILL and restart
     enable other probes.                     Service load balancer.                container immediately.
```

```yaml
spec:
  containers:
  - name: api-server
    image: api:v1
    startupProbe:
      httpGet:
        path: /healthz
        port: 8080
      failureThreshold: 30
      periodSeconds: 10 # Gives app up to 300 seconds to warm up cache
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
    livenessProbe:
      httpGet:
        path: /live
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 15
      timeoutSeconds: 3
```

> [!WARNING]
> **Liveness Probe Trap**: Do NOT check external dependencies (like your PostgreSQL database or Milvus vector DB) inside your `/live` endpoint! If Postgres has a 10-second blip, all your API pods' liveness probes will fail simultaneously, causing K8s to restart hundreds of API pods at once, resulting in a catastrophic cascading outage. Check external dependencies in `/ready`, never `/live`.

---

## 9. Hands-On Lab: Deploying a Multi-Tier Application

Let's write a complete, production-ready manifest deploying a **Redis Cache** (backend) and a **Python Web API** (frontend) with proper ConfigMaps, Services, and Probes.

### `app-deployment.yaml`

```yaml
# 1. Redis Service & Stateful Deployment
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  type: ClusterIP
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-cache
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        ports:
        - containerPort: 6379
---
# 2. ConfigMap for Web API
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  APP_ENV: "production"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
---
# 3. Web API Deployment with Probes and Resources
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: web-api
  template:
    metadata:
      labels:
        app: web-api
    spec:
      containers:
      - name: web-api
        image: python:3.11-slim
        command: ["python", "-c"]
        args:
        - |
          import http.server, socketserver, os
          port = 8080
          class Handler(http.server.SimpleHTTPRequestHandler):
              def do_GET(self):
                  self.send_response(200)
                  self.end_headers()
                  self.wfile.write(b"Kubernetes Masterclass API is running!\n")
          with socketserver.TCPServer(("", port), Handler) as httpd:
              httpd.serve_forever()
        envFrom:
        - configMapRef:
            name: api-config
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 512Mi
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 5
        livenessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 10
---
# 4. Web API External LoadBalancer Service
apiVersion: v1
kind: Service
metadata:
  name: web-api-service
spec:
  type: NodePort # Or LoadBalancer in Cloud
  selector:
    app: web-api
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080
```

---

## 10. Senior kubectl Cheat Sheet & Troubleshooting Runbook

### Core Inspection & Debugging
```bash
# Cluster overview
kubectl cluster-info
kubectl get nodes -o wide
kubectl top nodes                  # Check CPU & RAM consumption per node
kubectl top pods -A --sort-by=cpu  # Check top CPU hogs

# Pods and Workloads
kubectl get pods -n <namespace> -o wide --show-labels
kubectl describe pod <pod-name>    # Crucial: view Events at bottom of output!
kubectl logs <pod-name> -c <container-name> --tail=100 -f
kubectl logs <pod-name> --previous # View crash logs from container prior to restart

# Exec into running pod
kubectl exec -it <pod-name> -- /bin/sh

# Port-forwarding directly to your localhost (Bypasses Services/Ingress for testing)
kubectl port-forward pod/<pod-name> 8080:8080
kubectl port-forward svc/<service-name> 9092:9092
```

### Rollouts & Deployments
```bash
# Check rollout status
kubectl rollout status deployment/web-api

# View deployment revision history
kubectl rollout history deployment/web-api

# Undo / Rollback to previous version
kubectl rollout undo deployment/web-api
kubectl rollout undo deployment/web-api --to-revision=2

# Trigger a zero-downtime rolling restart (useful after ConfigMap changes)
kubectl rollout restart deployment/web-api
```

### Fast Manifest Generation (Dry Run Tricks)
Never write YAML from scratch. Use `kubectl` client dry-runs to generate templates:

```bash
# Generate a Deployment YAML
kubectl create deployment my-service --image=nginx:alpine --replicas=3 --dry-run=client -o yaml > deployment.yaml

# Generate a Service YAML
kubectl expose deployment my-service --port=80 --target-port=8080 --type=ClusterIP --dry-run=client -o yaml > service.yaml

# Generate a Secret from literals
kubectl create secret generic db-creds --from-literal=password='s3cr3tP@ss' --dry-run=client -o yaml > secret.yaml
```

### Common Pod Failure States & Quick Diagnosis

| Status / Error | Root Cause | Solution |
|---|---|---|
| `CrashLoopBackOff` | Application starts, errors out, and exits (code 1 or non-zero). | Check `kubectl logs <pod> --previous`. Usually wrong DB connection, missing env var, or missing file. |
| `ImagePullBackOff` / `ErrImagePull` | Cannot pull image. Wrong image name, missing tag, or missing `imagePullSecrets` for private registry. | Inspect `kubectl describe pod <pod>` events to see exact HTTP 401/404 response. |
| `OOMKilled` (Exit code 137) | Container exceeded memory `limit`. | Increase `resources.limits.memory` or profile application for memory leaks. |
| `Pending` | Pod cannot be scheduled onto any node. | Run `kubectl describe pod <pod>`: check for "Insufficient cpu/memory", unfulfilled node selector, or missing PVC. |
| `CreateContainerConfigError` | ConfigMap or Secret referenced by the Pod does not exist. | Create the missing ConfigMap/Secret or fix typographical errors in metadata names. |
