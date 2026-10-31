import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("KubeHeal.Notifier")

class IncidentNotifier:
    def __init__(self, reports_dir: str = "../reports"):
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def log_auto_healed(self, pod_name: str, namespace: str, decision: Dict[str, Any]):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print("\n" + "="*80)
        print(f"⚡ [KUBEHEAL AUTO-HEALED] Pod: {pod_name} | Namespace: {namespace}")
        print(f"🕒 Timestamp: {timestamp}")
        print(f"🎯 Action Executed: {decision.get('action')}")
        print(f"💡 Root Cause: {decision.get('root_cause_summary')}")
        print(f"🔧 Technical Detail: {decision.get('technical_details')}")
        print("="*80 + "\n")

    def generate_rca_report(self, pod_name: str, namespace: str, reason: str, logs: str, decision: Dict[str, Any]) -> str:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        filename = f"incident-{namespace}-{pod_name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.md"
        filepath = os.path.join(self.reports_dir, filename)

        markdown_report = f"""# 🚨 KubeHeal Incident Root Cause Analysis (RCA)

**Incident ID:** `INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}`  
**Status:** `REQUIRES_DEVELOPER_ACTION`  
**Classification:** `{decision.get('category')}` (Confidence: {int(decision.get('confidence_score', 0.9) * 100)}%)  
**Target Pod:** `{pod_name}`  
**Namespace:** `{namespace}`  
**Trigger Event / Exit Reason:** `{reason}`  
**Detection Timestamp:** `{timestamp}`  

---

## 🔍 Executive Root Cause Summary
{decision.get('root_cause_summary')}

## 🛠️ Technical Breakdown
- **Identified Defect:** {decision.get('technical_details')}
- **Automated Remediation Attempted:** `{decision.get('action')}` (Flagged for human review to prevent cascade failure)

## 💡 Developer Action Plan
{decision.get('developer_recommendation')}

---

## 📜 Raw Captured Telemetry (Last 50 Log Lines)
```text
{logs or "No logs available"}
```

---
*Report generated automatically by [KubeHeal Autonomous SRE Operator](https://github.com/Nikhilreddy810/KubeHeal).*
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_report)

        print("\n" + "#"*80)
        print(f"📝 [KUBEHEAL RCA REPORT GENERATED] Saved to: {filepath}")
        print(f"🚨 Summary: {decision.get('root_cause_summary')}")
        print(f"👉 Action Required: {decision.get('developer_recommendation')}")
        print("#"*80 + "\n")

        return filepath
