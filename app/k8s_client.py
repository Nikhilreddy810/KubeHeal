import logging
from kubernetes import client, config

logger = logging.getLogger("KubeHeal-Client")

def get_k8s_client():
    try:
        # 1. Try In-Cluster configuration (when running inside Kubernetes pod)
        config.load_incluster_config()
        logger.info("[✓] Loaded in-cluster Kubernetes ServiceAccount configuration.")
    except config.ConfigException:
        # 2. Fall back to local kubeconfig (~/.kube/config) for local dev/testing
        try:
            config.load_kube_config()
            logger.info("[✓] Loaded local kubeconfig (~/.kube/config).")
        except Exception as e:
            logger.error(f"[X] Failed to load any Kubernetes configuration: {e}")
            raise e

    return client.CoreV1Api(), client.AppsV1Api()
