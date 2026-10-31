import logging
from typing import Dict, Any, Tuple
from kubernetes import client

logger = logging.getLogger("KubeHeal.Collector")

class TelemetryCollector:
    def __init__(self, core_api: client.CoreV1Api):
        self.core_api = core_api

    def collect_failure_context(self, pod) -> Tuple[str, str, str]:
        """
        Extracts the waiting/exit reason, last 50 lines of logs, and recent events for a failing pod.
        """
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace

        # 1. Determine failure reason
        reason = "Unknown"
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                if cs.state.waiting and cs.state.waiting.reason:
                    reason = cs.state.waiting.reason
                    break
                elif cs.state.terminated and cs.state.terminated.reason:
                    reason = cs.state.terminated.reason
                    break
        elif pod.status.phase:
            reason = pod.status.phase

        # 2. Extract logs
        logs = ""
        try:
            logs = self.core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=50,
                previous=True  # Fetch logs from crashed instance if restarted
            )
        except Exception:
            try:
                logs = self.core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    tail_lines=50
                )
            except Exception as e:
                logs = f"Could not retrieve logs: {str(e)}"

        # 3. Extract recent events related to this Pod
        events_str = ""
        try:
            events = self.core_api.list_namespaced_event(
                namespace=namespace,
                field_selector=f"involvedObject.name={pod_name}"
            )
            events_str = "\n".join([f"- [{e.type}] {e.reason}: {e.message}" for e in events.items[-5:]])
        except Exception as e:
            events_str = f"Could not retrieve events: {str(e)}"

        return reason, logs, events_str
