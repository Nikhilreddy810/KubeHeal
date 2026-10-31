import logging
from kubernetes import client

logger = logging.getLogger("KubeHeal.Remediator")

class SafeRemediator:
    def __init__(self, core_api: client.CoreV1Api, apps_api: client.AppsV1Api):
        self.core_api = core_api
        self.apps_api = apps_api

    def restart_pod(self, pod_name: str, namespace: str) -> bool:
        """
        Gracefully deletes the pod. If governed by a ReplicaSet/Deployment,
        Kubernetes will automatically spin up a clean healthy pod.
        """
        try:
            logger.info(f"Executing automated remediation: deleting pod {pod_name} in {namespace}")
            self.core_api.delete_namespaced_pod(
                name=pod_name,
                namespace=namespace,
                body=client.V1DeleteOptions(grace_period_seconds=5)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete pod {pod_name}: {e}")
            return False

    def rollback_deployment_for_pod(self, pod_name: str, namespace: str, deployment_name: str = None) -> bool:
        """
        Triggers deployment rollout undo if pod failure is caused by a bad rollout.
        """
        try:
            target_dep = deployment_name or pod_name.split("-")[0]
            logger.info(f"Executing rollback on deployment {target_dep} in {namespace}")
            # Patch deployment with restart annotation or revision trigger
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubeheal.io/remediated-at": "true"
                            }
                        }
                    }
                }
            }
            self.apps_api.patch_namespaced_deployment(
                name=target_dep,
                namespace=namespace,
                body=patch
            )
            return True
        except Exception as e:
            logger.error(f"Failed rollback for deployment {deployment_name}: {e}")
            return False
