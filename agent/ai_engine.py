import os
import json
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger("KubeHeal.AI")

SYSTEM_PROMPT = """
You are KubeHeal, an expert Autonomous Kubernetes Site Reliability Engineer (SRE).
Analyze the provided Kubernetes pod crash telemetry, including pod status, events, and container logs.

Classify the incident into one of two categories:
1. "BASIC_AUTO_FIX": Transient glitch, OOM memory limit exhaustion, failed deployment, or image pull timeout that can be safely remediated via Kubernetes API actions.
2. "COMPLEX_CODE_BUG": Code-level failure (e.g., NullPointerException, unhandled exception, syntax error, database connection failure, broken business logic) that requires developer intervention.

Output strictly valid JSON with this exact schema:
{
  "category": "BASIC_AUTO_FIX" | "COMPLEX_CODE_BUG",
  "confidence_score": 0.0 - 1.0,
  "action": "RESTART_POD" | "ROLLBACK_DEPLOYMENT" | "PATCH_RESOURCE_LIMITS" | "REPORT_ONLY",
  "root_cause_summary": "Concise 1-2 sentence explanation of why the pod failed",
  "technical_details": "Exact failing component, exception name, or resource bottleneck identified",
  "developer_recommendation": "Step-by-step actionable advice for the engineer to permanently fix the issue"
}
"""

class AIEngine:
    def __init__(self, api_key: str = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name

    def analyze_failure(self, pod_name: str, namespace: str, reason: str, logs: str, events: str) -> Dict[str, Any]:
        """
        Sends the collected failure context to LLM for automated triage.
        Falls back to local heuristic SRE rules if external API is unreachable or key is not provided.
        """
        prompt = f"""
KUBERNETES FAILURE INCIDENT TELEMETRY:
- Pod Name: {pod_name}
- Namespace: {namespace}
- Reported Reason / Waiting State: {reason}

RECENT POD EVENTS:
{events or "No events captured"}

LAST 50 LINES OF CONTAINER LOGS:
{logs or "No logs available"}
"""
        if self.api_key and os.getenv("GEMINI_API_KEY"):
            try:
                return self._call_gemini(prompt)
            except Exception as e:
                logger.warning(f"External AI call failed ({e}). Falling back to local SRE heuristic triage.")

        return self._heuristic_fallback(reason, logs, events)

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data['candidates'][0]['content']['parts'][0]['text']
        return json.loads(raw_text)

    def _heuristic_fallback(self, reason: str, logs: str, events: str) -> Dict[str, Any]:
        """Built-in deterministic SRE engine for offline or zero-API-key testing."""
        reason_upper = (reason or "").upper()
        logs_upper = (logs or "").upper()

        if "OOMKILLED" in reason_upper or "OUT OF MEMORY" in logs_upper:
            return {
                "category": "BASIC_AUTO_FIX",
                "confidence_score": 0.95,
                "action": "PATCH_RESOURCE_LIMITS",
                "root_cause_summary": "Container terminated by Linux kernel OOM Killer due to exceeding memory limit.",
                "technical_details": "Memory consumption exceeded container limits in deployment spec.",
                "developer_recommendation": "Increase memory request/limits in Helm values.yaml or optimize memory leak."
            }

        if "IMAGEPULLBACKOFF" in reason_upper or "ERRIMAGEPULL" in reason_upper:
            return {
                "category": "BASIC_AUTO_FIX",
                "confidence_score": 0.90,
                "action": "ROLLBACK_DEPLOYMENT",
                "root_cause_summary": "Container runtime failed to pull image from registry; likely invalid tag or auth failure.",
                "technical_details": "Image pull failed with ImagePullBackOff.",
                "developer_recommendation": "Verify image tag in values.yaml and ensure docker registry secret exists."
            }

        if "NULLPOINTEREXCEPTION" in logs_upper or "TRACEBACK" in logs_upper or "FATAL ERROR" in logs_upper:
            return {
                "category": "COMPLEX_CODE_BUG",
                "confidence_score": 0.98,
                "action": "REPORT_ONLY",
                "root_cause_summary": "Application runtime encountered an unhandled code exception during execution.",
                "technical_details": "Application stack trace indicates unhandled error or null pointer dereference.",
                "developer_recommendation": "Review stack trace in attached RCA report, fix null check or missing parameter, and commit bugfix."
            }

        # Default fallback
        return {
            "category": "BASIC_AUTO_FIX",
            "confidence_score": 0.75,
            "action": "RESTART_POD",
            "root_cause_summary": "Transient process crash or unhandled exit code.",
            "technical_details": f"Container exited unexpectedly with status: {reason}",
            "developer_recommendation": "Restarted pod to verify if failure is transient or reproducible."
        }
