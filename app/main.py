import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.k8s_client import get_k8s_client
from app.triage_engine import TriageEngine
from app.watcher import KubeWatcher
from app.models import ClusterTelemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("KubeHeal-App")

app = FastAPI(title="KubeHeal SRE Operator", version="2.0.0")
templates = Jinja2Templates(directory="app/templates")

# Initialize Kubernetes Clients
core_api, apps_api = get_k8s_client()

# Initialize SRE Triage & Healing Engine
triage_engine = TriageEngine(core_api=core_api)

# Initialize Real-Time Kube-APIServer Event Streamer
watcher = KubeWatcher(core_api=core_api, triage_engine=triage_engine)

@app.on_event("startup")
def startup_event():
    logger.info("[🚀] Starting KubeHeal Kubernetes SRE Operator...")
    watcher.start()

@app.on_event("shutdown")
def shutdown_event():
    logger.info("[🛑] Stopping KubeHeal watcher...")
    watcher.running = False

@app.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request):
    # Fetch cluster metrics
    try:
        nodes = core_api.list_node().items
        total_nodes = len(nodes)
    except Exception:
        total_nodes = 1

    try:
        pods = core_api.list_pod_for_all_namespaces().items
        total_pods = len(pods)
        unhealthy = sum(1 for p in pods if p.status.phase in ["Pending", "Failed"] or any(
            cs.restart_count > 0 for cs in (p.status.container_statuses or [])
        ))
    except Exception:
        total_pods = 0
        unhealthy = 0

    telemetry = ClusterTelemetry(
        total_nodes=total_nodes,
        total_pods=total_pods,
        unhealthy_pods=unhealthy,
        auto_healed_count=triage_engine.auto_healed_counter,
        active_incidents=len(triage_engine.incidents),
        last_event_time=datetime.now().strftime("%H:%M:%S")
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "telemetry": telemetry,
            "incidents": triage_engine.incidents
        }
    )

@app.get("/healthz")
def healthz():
    return {"status": "UP", "operator": "KubeHeal-Python", "version": "2.0.0"}

@app.get("/api/incidents")
def get_incidents():
    return triage_engine.incidents
