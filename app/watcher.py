import logging
import threading
import time
from kubernetes import watch
from app.triage_engine import TriageEngine

logger = logging.getLogger("KubeHeal-Watcher")

class KubeWatcher:
    def __init__(self, core_api, triage_engine: TriageEngine):
        self.core_api = core_api
        self.triage = triage_engine
        self.running = False
        self._thread = None
        # Track seen failures to avoid spamming alerts in the same state
        self.processed_signatures = set()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("[✓] Real-time Kube-APIServer event watcher thread started.")

    def _watch_loop(self):
        while self.running:
            try:
                w = watch.Watch()
                logger.info("[*] Connecting to Kube-APIServer event stream...")
                for event in w.stream(self.core_api.list_pod_for_all_namespaces, timeout_seconds=60):
                    if not self.running:
                        break

                    pod = event.get('object')
                    if not pod or not pod.status:
                        continue

                    self._inspect_pod(pod)

            except Exception as e:
                logger.error(f"[X] Watcher error: {e}. Reconnecting in 5 seconds...")
                time.sleep(5)

    def _inspect_pod(self, pod):
        # Ignore pods in kube-system unless explicitly desired
        ns = pod.metadata.namespace
        name = pod.metadata.name

        # Look at container statuses
        statuses = pod.status.container_statuses or []
        for cs in statuses:
            container_name = cs.name
            restarts = cs.restart_count
            
            failure_reason = None
            exit_code = None

            # Case 1: Currently Waiting with failure
            if cs.state and cs.state.waiting:
                reason = cs.state.waiting.reason
                if reason in ["CrashLoopBackOff", "ImagePullBackOff", "CreateContainerConfigError"]:
                    failure_reason = reason

            # Case 2: Terminated with OOM or Error
            if cs.last_state and cs.last_state.terminated:
                term_reason = cs.last_state.terminated.reason
                term_code = cs.last_state.terminated.exit_code
                if term_reason == "OOMKilled" or term_code == 137:
                    failure_reason = "OOMKilled"
                    exit_code = 137
                elif term_code and term_code != 0:
                    failure_reason = f"Error (Exit Code {term_code})"
                    exit_code = term_code

            # Trigger triage if an unhandled failure state is identified
            if failure_reason:
                signature = f"{ns}/{name}/{container_name}/{failure_reason}/{restarts}"
                if signature not in self.processed_signatures:
                    self.processed_signatures.add(signature)
                    # Keep set bounded
                    if len(self.processed_signatures) > 500:
                        self.processed_signatures.clear()

                    logger.warning(f"[!] DETECTED FAILURE: {ns}/{name} -> {failure_reason} (Restarts: {restarts})")
                    self.triage.evaluate_and_remediate(
                        namespace=ns,
                        pod_name=name,
                        container_name=container_name,
                        failure_reason=failure_reason,
                        restart_count=restarts,
                        exit_code=exit_code
                    )
