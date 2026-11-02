from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Incident(BaseModel):
    id: str
    timestamp: str
    namespace: str
    pod_name: str
    container_name: str
    status: str
    restart_count: int
    exit_code: Optional[int] = None
    triage_tier: str       # "BASIC_AUTO_FIX" | "COMPLEX_CODE_BUG"
    action_taken: str      # "RECREATED_POD" | "BLOCKED_INFINITE_LOOP_ESCALATED"
    logs_snippet: str
    rca_markdown: str

class ClusterTelemetry(BaseModel):
    total_nodes: int
    total_pods: int
    unhealthy_pods: int
    auto_healed_count: int
    active_incidents: int
    last_event_time: str
