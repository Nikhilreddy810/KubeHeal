# 🤖 KubeHeal: Autonomous AI-Powered Kubernetes Self-Healing & RCA Operator

[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.30+-326CE5.svg?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Helm 3](https://img.shields.io/badge/Helm-v3.x-0F1689.svg?style=for-the-badge&logo=helm&logoColor=white)](https://helm.sh/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-D24939.svg?style=for-the-badge&logo=jenkins&logoColor=white)](https://www.jenkins.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**KubeHeal** is an autonomous, closed-loop Kubernetes SRE operator engineered to detect container runtime crashes, stream cluster failure events, and apply real-time generative AI intelligence to triage incidents. 

It automatically self-heals transient operational errors (transient exits, pod restarts, rollout reversions) within safe guardrails while instantly compiling structured **Root Cause Analysis (RCA)** incident reports for complex code-level bugs.

---

## 🏛️ System Architecture Topology

```text
                      ┌────────────────────────────────────────────────────────┐
                      │              KUBERNETES CLUSTER (Minikube / EKS)       │
                      │                                                        │
                      │  [ App Pods / Deployments ] ◄── Packaged via Helm      │
                      │             │ (Pod Crash / OOM / Error Event)          │
                      │             ▼                                          │
                      │      Kube-APIServer (Events API)                       │
                      └─────────────┬──────────────────────────────────────────┘
                                    │ (Real-time Stream Watch)
                                    ▼
       ┌────────────────────────────────────────────────────────────┐
       │                 KUBEHEAL OPERATOR / DAEMON                 │
       │                                                            │
       │  1. EVENT CAPTURE & CONTEXT COLLECTOR                      │
       │     • Real-time watch stream for Pod states:               │
       │       CrashLoopBackOff, OOMKilled, Error, ImagePullBackOff │
       │     • Extracts: `kubectl logs --tail=50`, pod events,      │
       │       and previous container exit states                   │
       │                                                            │
       │  2. AI SRE TRIAGE ENGINE (Gemini API / LLM)                │
       │     • Analyzes crash telemetry & stack trace               │
       │     • Triage Categorization:                               │
       │       ├─ LEVEL 1: Basic Operational Error (Auto-Fixable)   │
       │       └─ LEVEL 2: Complex Code/App Bug (Generate RCA)      │
       │                                                            │
       │  3. DECISION & REMEDIATION CONTROLLER                      │
       │     ├─ If LEVEL 1 (Basic Operational Error):               │
       │     │  • Triggers safe K8s API action:                     │
       │     │    - Graceful Pod Re-creation via ReplicaSet         │
       │     │    - Deployment Rollback for bad rollouts            │
       │     │  • Logs auto-healed alert with sub-second MTTR       │
       │     │                                                      │
       │     └─ If LEVEL 2 (Complex Bug / NullPointerException):    │
       │        • Prevents dangerous infinite restart loops         │
       │        • Publishes instant Markdown RCA Incident Report    │
       │          (Root cause, failing line, developer action plan) │
       └────────────────────────────┬───────────────────────────────┘
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────────┐
       │                TELEMETRY & NOTIFICATIONS                   │
       │   • Webhook Incident Alerts (Slack / Terminal Stream)      │
       │   • Structured RCA Reports stored in `/reports/*.md`       │
       │   • Cluster status restored to HEALTHY without manual SRE  │
       └────────────────────────────────────────────────────────────┘
```

---

## ⚡ Incident Triage & Decision Matrix

| Incident Signature | Classification | Automated Remediation Action | Human SRE Required? |
| :--- | :--- | :--- | :---: |
| **Transient Container Exit** | `BASIC_AUTO_FIX` | Graceful Pod deletion & ReplicaSet recreation | ❌ Zero human touch |
| **OOMKilled (Out Of Memory)** | `BASIC_AUTO_FIX` | Resource limit detection & container restart alert | ❌ Auto-mitigated |
| **ImagePullBackOff / Bad Tag** | `BASIC_AUTO_FIX` | Automatic Deployment Rollout Undo (`v1.rollback`) | ❌ Auto-mitigated |
| **Java `NullPointerException`** | `COMPLEX_CODE_BUG` | **REPORT_ONLY** (Compiles instant RCA Incident Report) | ✅ Direct developer fix |
| **Database Connection Failure** | `COMPLEX_CODE_BUG` | **REPORT_ONLY** (Logs host/port network timeout RCA) | ✅ Infrastructure review |

---

## 📁 Repository Directory Layout

```text
KubeHeal/
├── agent/                             # Core Python Autonomous Operator
│   ├── main.py                        # K8s event watcher & debouncing loop
│   ├── collector.py                   # Context extraction (logs, events, exit codes)
│   ├── ai_engine.py                   # LLM integration (Gemini SRE prompt) + heuristic fallback
│   ├── remediator.py                  # Safe K8s API execution controller
│   ├── notifier.py                    # Formats Markdown RCA reports & console telemetry
│   ├── requirements.txt               # Dependencies (kubernetes, requests, etc.)
│   └── Dockerfile                     # Multi-stage lightweight non-root container build
├── helm/                              # Production Helm Packaging
│   └── kubeheal/
│       ├── Chart.yaml                 # Helm Chart metadata
│       ├── values.yaml                # Configurable parameters (namespace, resources, limits)
│       └── templates/
│           ├── deployment.yaml        # Deployment specification
│           └── rbac.yaml              # Least-privilege ServiceAccount, ClusterRole & Binding
├── cicd/
│   └── Jenkinsfile                    # Declarative Pipeline (Lint, Build, Dry-Run, Deploy)
├── chaos-tests/                       # Reproducible Failure Scenarios
│   ├── 01-transient-crash.yaml        # Simulates transient exit (Trigger: Auto-Heal)
│   └── 02-java-nullpointer-bug.yaml   # Simulates Spring Boot NullPointer (Trigger: RCA Report)
└── reports/                           # Output Artifacts
    └── sample-rca-incident.md         # Example generated Incident Report
```

---

## 🚀 Quickstart & Verification

### 1. Deploy KubeHeal via Helm
```bash
# Lint the Helm chart
helm lint ./helm/kubeheal

# Test template rendering & dry-run
helm upgrade --install kubeheal ./helm/kubeheal --dry-run --debug

# Install to Kubernetes cluster
helm install kubeheal ./helm/kubeheal --namespace default
```

### 2. Verify Operator Pod Running
```bash
kubectl get pods -l app.kubernetes.io/name=kubeheal
```

### 3. Trigger Chaos Scenario 1 (Transient Crash ➔ Auto-Healed)
```bash
kubectl apply -f chaos-tests/01-transient-crash.yaml
```
*Observe KubeHeal logs:*
```text
🚨 Incident detected on Pod: test-transient-crash (Reason: CrashLoopBackOff)
⚡ [KUBEHEAL AUTO-HEALED] Pod: test-transient-crash | Namespace: default
🎯 Action Executed: RESTART_POD
💡 Root Cause: Transient container crash or unhandled exit signal.
```

### 4. Trigger Chaos Scenario 2 (Java NullPointerException ➔ RCA Generated)
```bash
kubectl apply -f chaos-tests/02-java-nullpointer-bug.yaml
```
*Observe KubeHeal logs:*
```text
🚨 Incident detected on Pod: test-java-nullpointer-bug (Reason: Error)
📝 [KUBEHEAL RCA REPORT GENERATED] Saved to: reports/incident-default-test-java-nullpointer-bug-*.md
🚨 Summary: Application runtime encountered an unhandled NullPointerException in BookingServiceImpl.
👉 Action Required: Add null-check on User entity or validate JWT claims before invoking reserveSeat().
```

---

## 📜 Sample Generated RCA Incident Report

Every complex bug caught by KubeHeal generates an actionable, executive Markdown report like this:

> ### 🚨 KubeHeal Incident Root Cause Analysis (RCA)
> **Incident ID:** `INC-20261031-001`  
> **Status:** `REQUIRES_DEVELOPER_ACTION`  
> **Classification:** `COMPLEX_CODE_BUG` (Confidence: 98%)  
> **Target Pod:** `booking-service-78fbd4-x8k2`  
> 
> ### 🔍 Executive Root Cause Summary
> Application runtime encountered an unhandled NullPointerException in `BookingServiceImpl`.
> 
> ### 🛠️ Technical Breakdown
> - **Identified Defect:** Null customer object passed to `reserveSeat()` at line 142.
> - **Automated Remediation Attempted:** `REPORT_ONLY` (Prevented recursive failure loops).
> 
> ### 💡 Developer Action Plan
> Add null-check on User entity or validate JWT claims before invoking `reserveSeat()`.
> 
> ### 📜 Raw Captured Telemetry
> ```text
> java.lang.NullPointerException: Cannot invoke getUserId() because customer is null
>     at com.nikhil.flight.service.BookingServiceImpl.reserveSeat(BookingServiceImpl.java:142)
> ```

---

## 🔒 Security Best Practices
- **Least-Privilege RBAC:** The operator runs with a dedicated `ServiceAccount` granted only targeted verbs (`get`, `list`, `watch`, `delete` for pods; `patch` for deployments).
- **Non-Root Execution:** Containerized using a multi-stage Docker build running under non-root UID `10001`.
- **Debounced Remediation:** Built-in 60-second alert cooldown prevents cascading reboot storms.

---

## 👤 Author
**Nikhil Reddy Levaku**  
- **Portfolio:** [nikhilreddy810.github.io/portfolio/](https://nikhilreddy810.github.io/portfolio/)  
- **LinkedIn:** [linkedin.com/in/nikhilreddylevaku/](https://www.linkedin.com/in/nikhilreddylevaku/)  
- **GitHub:** [@Nikhilreddy810](https://github.com/Nikhilreddy810)  
- **Email:** levakunikhilreddy8@gmail.com
