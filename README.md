# KubeHeal: Autonomous AI-Powered Kubernetes SRE Operator & GitOps Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Client-326ce5.svg)](https://kubernetes.io/)
[![Helm](https://img.shields.io/badge/Helm-3-0f1689.svg)](https://helm.sh/)
[![ArgoCD](https://img.shields.io/badge/Argo%20CD-GitOps-orange.svg)](https://argo-cd.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**KubeHeal** is a cloud-native, production-grade **Autonomous Kubernetes SRE Operator** written in Python (FastAPI + Official Kubernetes API Client). It replaces passive cluster alerts and blind restart loops with real-time event streaming, forensic container log collection, intelligent failure triage, and automated GitOps remediation.

---

## 🌟 Key Architecture & Capabilities

```
              KUBERNETES CLUSTER (EKS / Minikube)
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │  [ Failing Workload Pod ]                              │
    │       │ (OOMKilled / CrashLoopBackOff / Probe Timeout)  │
    │       ▼                                                │
    │  [ Kube-APIServer Event Stream ]                       │
    │       │                                                │
    └───────┼────────────────────────────────────────────────┘
            │ (Watch Stream API - Persistent HTTP/2)
            ▼
    ┌────────────────────────────────────────────────────────┐
    │              KUBEHEAL PYTHON SRE OPERATOR              │
    │                                                        │
    │ 1. KubeWatcher (app/watcher.py)                        │
    │    - Listens to APIServer pod lifecycle event stream.  │
    │    - Intercepts state changes with 0s latency.         │
    │                                                        │
    │ 2. Triage & Healing Engine (app/triage_engine.py)       │
    │    - Pulls dead container logs via previous=True.      │
    │    - Bifurcates: BASIC_AUTO_FIX vs COMPLEX_CODE_BUG.   │
    │    - Halts infinite restart loops on OOM (Exit 137).   │
    │    - Triggers self-healing pod recreations.            │
    │                                                        │
    │ 3. Executive SRE Dashboard (app/main.py)               │
    │    - Fast, dark-mode real-time monitor on port 8090.   │
    │    - Structured Markdown Root Cause Analysis (RCA).    │
    └────────────────────────────────────────────────────────┘
```

- **Real-Time Kube-APIServer Event Streamer**: Utilizes `kubernetes.watch.Watch` to intercept pod status modifications with sub-second latency instead of expensive cluster polling loops.
- **Forensic Log Extraction**: Automatically retrieves previous dead container logs (`previous=True`) and maps termination exit codes (e.g. Exit Code `137` for `OOMKilled`, Exit Code `1` for application exceptions).
- **Intelligent Triage & Loop Prevention**:
  - `BASIC_AUTO_FIX`: Safely deletes transiently failing pods, allowing Deployment ReplicaSets to cleanly recreate healthy instances.
  - `COMPLEX_CODE_BUG`: When memory limits are breached or stack traces persist, it halts blind restarts to protect node resources, generating an instant Markdown Root Cause Analysis (RCA) report.
- **Enterprise GitOps & Helm 3 Ready**: Complete with a modular Helm 3 chart (`helm/kubeheal`), least-privilege RBAC (`ClusterRole`, `ClusterRoleBinding`, `ServiceAccount`), and declarative Argo CD application manifests (`argocd/kubeheal-app.yaml`).
- **Lightweight Multi-Stage Docker Build**: Minimal non-root Python Alpine/Slim image (< 80MB) following CIS container security benchmarks.

---

## 📂 Repository Structure

```text
KubeHeal/
├── app/
│   ├── main.py              # FastAPI server, endpoints (/healthz, /api) & bootstrap
│   ├── watcher.py           # Kube-APIServer real-time event watcher thread
│   ├── triage_engine.py     # Log collector, failure classifier & auto-remediation logic
│   ├── k8s_client.py        # In-cluster ServiceAccount & local kubeconfig loader
│   ├── models.py            # Pydantic telemetry and incident data models
│   └── templates/
│       └── dashboard.html   # Real-time dark-mode Executive SRE Dashboard
├── helm/kubeheal/           # Production Helm 3 chart
│   ├── Chart.yaml
│   ├── values.yaml          # Parameterized resource limits, replicas & ports
│   └── templates/
│       ├── deployment.yaml  # Operator Deployment manifest
│       ├── rbac.yaml        # Least-privilege ClusterRole & ServiceAccount
│       └── service.yaml     # Service exposing port 8090
├── argocd/
│   └── kubeheal-app.yaml    # Declarative GitOps deployment manifest
├── cicd/
│   └── Jenkinsfile          # Declarative CI/CD pipeline (Lint, Build, Trivy scan, Helm)
├── chaos-tests/
│   ├── oom-killed-pod.yaml  # Simulates Out-Of-Memory failure (Exit Code 137)
│   └── crash-loop-pod.yaml  # Simulates unhandled container application crash
├── requirements.txt         # Pinned lightweight Python dependencies
├── Dockerfile               # Multi-stage, non-root hardened container image
└── README.md
```

---

## 🚀 Quickstart & Local Execution

### 1. Run Locally with Python:
Ensure your local Kubernetes cluster (Minikube / Docker Desktop / KinD) is running:
```bash
# Clone the repository
git clone https://github.com/Nikhilreddy810/KubeHeal.git
cd KubeHeal

# Install dependencies
pip install -r requirements.txt

# Start KubeHeal operator & web dashboard
uvicorn app.main:app --host 0.0.0.0 --port 8090
```
Open **`http://localhost:8090`** in your browser to view the live Executive SRE Dashboard.

---

## 🛠️ Deploy to Kubernetes via Helm 3

Deploy KubeHeal with its configured RBAC into your cluster:
```bash
# Lint the chart
helm lint helm/kubeheal

# Install or upgrade
helm upgrade --install kubeheal ./helm/kubeheal --namespace default

# Check status
kubectl get pods -l app.kubernetes.io/name=kubeheal
```

---

## 🧪 Chaos Testing & Live Verification

Trigger a simulated failure to observe KubeHeal's real-time detection, log capture, and triage:
```bash
# Inject an OOMKilled failure
kubectl apply -f chaos-tests/oom-killed-pod.yaml

# Observe KubeHeal logs and dashboard
# KubeHeal will capture Exit Code 137, halt blind restarts, and generate an RCA report.
```
