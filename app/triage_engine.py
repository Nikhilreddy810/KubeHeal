import logging
import uuid
from datetime import datetime
from typing import List, Optional
from app.models import Incident

logger = logging.getLogger("KubeHeal-Triage")

class TriageEngine:
    def __init__(self, core_api):
        self.core_api = core_api
        self.incidents: List[Incident] = []
        self.auto_healed_counter = 0

    def evaluate_and_remediate(
        self,
        namespace: str,
        pod_name: str,
        container_name: str,
        failure_reason: str,
        restart_count: int,
        exit_code: Optional[int]
    ) -> Incident:
        # Step 1: Collect dead container logs (equivalent to kubectl logs --previous)
        previous_logs = self._fetch_logs(namespace, pod_name, container_name)

        # Step 2: Intelligent Triage Bifurcation
        # If exit code is 137 (OOMKilled) or app thrown Exception or excessive restarts -> Do NOT blind-restart
        is_oom = exit_code == 137 or "OOMKilled" in failure_reason
        is_severe_code_bug = "Exception" in previous_logs or "Error" in failure_reason
        is_flapping = restart_count > 3

        if is_oom or (is_severe_code_bug and is_flapping):
            triage_tier = "COMPLEX_CODE_BUG"
            action_taken = "BLOCKED_LOOP_ESCALATED"
            rca_md = self._generate_rca_report(
                namespace, pod_name, container_name, failure_reason, exit_code, restart_count, previous_logs,
                recommendation="Increase Pod memory limits/requests or profile application heap leak. Automated restarts suspended to prevent node starvation."
            )
            logger.warning(f"[ESCALATION] Pod {pod_name} flagged as {triage_tier}. Blind restarts prevented.")
        else:
            triage_tier = "BASIC_AUTO_FIX"
            action_taken = "RECREATED_POD"
            self._recreate_pod(namespace, pod_name)
            self.auto_healed_counter += 1
            rca_md = self._generate_rca_report(
                namespace, pod_name, container_name, failure_reason, exit_code, restart_count, previous_logs,
                recommendation="Transient failure detected. Triggered proactive deletion; Deployment controller provisioned clean replica."
            )
            logger.info(f"[REMEDIATED] Pod {pod_name} successfully healed under {triage_tier}.")

        incident = Incident(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            status=failure_reason,
            restart_count=restart_count,
            exit_code=exit_code,
            triage_tier=triage_tier,
            action_taken=action_taken,
            logs_snippet=previous_logs[:500] if previous_logs else "No previous logs captured.",
            rca_markdown=rca_md
        )

        self.incidents.insert(0, incident)
        # Keep recent 50 incidents in memory
        if len(self.incidents) > 50:
            self.incidents.pop()

        return incident

    def _fetch_logs(self, namespace: str, pod_name: str, container_name: str) -> str:
        try:
            return self.core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container_name,
                previous=True,
                tail_lines=30
            )
        except Exception:
            try:
                return self.core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container_name,
                    tail_lines=30
                )
            except Exception as e:
                return f"[Warning] Could not retrieve container logs: {e}"

    def _recreate_pod(self, namespace: str, pod_name: str):
        try:
            self.core_api.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info(f"[Action] Successfully deleted pod {pod_name} in {namespace}.")
        except Exception as e:
            logger.error(f"[Action Failed] Could not delete pod {pod_name}: {e}")

    def _generate_rca_report(
        self,
        namespace: str,
        pod_name: str,
        container_name: str,
        failure_reason: str,
        exit_code: Optional[int],
        restarts: int,
        logs: str,
        recommendation: str
    ) -> str:
        return f"""### Root Cause Analysis (RCA) - Incident
- **Target**: `{namespace}/{pod_name}` (Container: `{container_name}`)
- **Failure Classification**: `{failure_reason}` (Exit Code: `{exit_code}`)
- **Total Restarts**: `{restarts}`
- **Automated Diagnosis**: {recommendation}

#### Captured Log Trace:
```text
{logs[-400:] if len(logs) > 400 else logs}
```
"""
