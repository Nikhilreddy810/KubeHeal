import time
import logging
from kubernetes import client, config, watch

from collector import TelemetryCollector
from ai_engine import AIEngine
from remediator import SafeRemediator
from notifier import IncidentNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("KubeHeal.Main")

# Track handled pod restarts to prevent rapid infinite retry loops
HANDLED_CACHE = {}

def init_k8s_clients():
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes configuration.")
    except Exception:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig file.")

    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()
    return core_api, apps_api

def run_agent(namespace: str = "default"):
    core_api, apps_api = init_k8s_clients()

    collector = TelemetryCollector(core_api)
    ai_engine = AIEngine()
    remediator = SafeRemediator(core_api, apps_api)
    notifier = IncidentNotifier()

    print("\n" + "*"*80)
    print("🤖 KubeHeal Autonomous SRE Operator Active & Monitoring Cluster")
    print(f"🎯 Target Namespace: {namespace}")
    print("*"*80 + "\n")

    w = watch.Watch()
    while True:
        try:
            for event in w.stream(core_api.list_namespaced_pod, namespace=namespace):
                pod = event['object']
                pod_name = pod.metadata.name
                phase = pod.status.phase

                # Identify if any container is in an unhealthy waiting state
                failing_reason = None
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        if cs.state.waiting and cs.state.waiting.reason in ["CrashLoopBackOff", "OOMKilled", "ErrImagePull", "ImagePullBackOff", "Error"]:
                            failing_reason = cs.state.waiting.reason
                            break
                        elif cs.state.terminated and cs.state.terminated.reason in ["OOMKilled", "Error"]:
                            failing_reason = cs.state.terminated.reason
                            break
                elif phase in ["Failed"]:
                    failing_reason = phase

                if failing_reason:
                    now = time.time()
                    last_seen = HANDLED_CACHE.get(pod_name, 0)
                    if now - last_seen < 60:
                        # Debounce alerts within 60 seconds for same pod
                        continue
                    HANDLED_CACHE[pod_name] = now

                    logger.warning(f"🚨 Incident detected on Pod: {pod_name} (Reason: {failing_reason})")

                    # 1. Collect Logs & Events
                    reason, logs, events = collector.collect_failure_context(pod)

                    # 2. AI Triage Engine Analyzes Failure
                    decision = ai_engine.analyze_failure(pod_name, namespace, reason, logs, events)

                    # 3. Decision Execution
                    if decision.get("category") == "BASIC_AUTO_FIX":
                        action = decision.get("action")
                        if action == "RESTART_POD":
                            success = remediator.restart_pod(pod_name, namespace)
                            if success:
                                notifier.log_auto_healed(pod_name, namespace, decision)
                        elif action == "ROLLBACK_DEPLOYMENT":
                            success = remediator.rollback_deployment_for_pod(pod_name, namespace)
                            if success:
                                notifier.log_auto_healed(pod_name, namespace, decision)
                        else:
                            remediator.restart_pod(pod_name, namespace)
                            notifier.log_auto_healed(pod_name, namespace, decision)
                    else:
                        # Complex Code Bug -> Generate RCA Report for Engineer
                        notifier.generate_rca_report(pod_name, namespace, reason, logs, decision)

        except Exception as e:
            logger.error(f"Watcher stream interrupted: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_agent()
