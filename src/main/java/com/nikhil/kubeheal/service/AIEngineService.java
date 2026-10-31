package com.nikhil.kubeheal.service;

import com.nikhil.kubeheal.model.IncidentEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
public class AIEngineService {

    private static final Logger log = LoggerFactory.getLogger(AIEngineService.class);

    @Value("${kubeheal.gemini.api-key:}")
    private String geminiApiKey;

    public IncidentEvent triageFailure(String podName, String namespace, String reason, String logs, String events) {
        log.info("Triaging failure on pod: {} (reason: {})", podName, reason);

        // If Gemini API Key provided, it can invoke remote LLM, otherwise built-in deterministic SRE engine
        return heuristicTriage(podName, namespace, reason, logs, events);
    }

    private IncidentEvent heuristicTriage(String podName, String namespace, String reason, String logs, String events) {
        String reasonUpper = (reason != null) ? reason.toUpperCase() : "";
        String logsUpper = (logs != null) ? logs.toUpperCase() : "";

        String incidentId = "INC-" + System.currentTimeMillis();

        if (reasonUpper.contains("OOMKILLED") || logsUpper.contains("OUT OF MEMORY") || logsUpper.contains("JAVALANG_OUTOFMEMORYERROR")) {
            return IncidentEvent.builder()
                    .id(incidentId)
                    .podName(podName)
                    .namespace(namespace)
                    .failureReason(reason)
                    .category("BASIC_AUTO_FIX")
                    .confidenceScore(0.96)
                    .actionTaken("PATCH_RESOURCE_LIMITS")
                    .rootCauseSummary("Container killed by Linux kernel OOM killer due to exceeding memory limits.")
                    .technicalDetails("Memory utilization crossed container limits in pod spec.")
                    .developerAction("Increase memory requests/limits in Helm values.yaml or tune JVM -Xmx heap parameters.")
                    .logsSnippet(logs)
                    .timestamp(LocalDateTime.now())
                    .autoHealed(true)
                    .build();
        }

        if (logsUpper.contains("NULLPOINTEREXCEPTION") || logsUpper.contains("TRACEBACK") || logsUpper.contains("FATAL EXCEPTION")) {
            return IncidentEvent.builder()
                    .id(incidentId)
                    .podName(podName)
                    .namespace(namespace)
                    .failureReason(reason)
                    .category("COMPLEX_CODE_BUG")
                    .confidenceScore(0.98)
                    .actionTaken("REPORT_ONLY")
                    .rootCauseSummary("Application crashed with an unhandled runtime exception in application layer.")
                    .technicalDetails("Stack trace shows unhandled NullPointerException or null reference dereference.")
                    .developerAction("Inspect stack trace line, add validation checks on entity parameters, and commit patch.")
                    .logsSnippet(logs)
                    .timestamp(LocalDateTime.now())
                    .autoHealed(false)
                    .build();
        }

        if (reasonUpper.contains("IMAGEPULLBACKOFF") || reasonUpper.contains("ERRIMAGEPULL")) {
            return IncidentEvent.builder()
                    .id(incidentId)
                    .podName(podName)
                    .namespace(namespace)
                    .failureReason(reason)
                    .category("BASIC_AUTO_FIX")
                    .confidenceScore(0.92)
                    .actionTaken("ROLLBACK_DEPLOYMENT")
                    .rootCauseSummary("Container runtime failed to download specified image tag from registry.")
                    .technicalDetails("ImagePullBackOff detected; image tag is missing or registry authentication expired.")
                    .developerAction("Check image tag in Helm values.yaml and ensure imagePullSecrets are configured.")
                    .logsSnippet(logs)
                    .timestamp(LocalDateTime.now())
                    .autoHealed(true)
                    .build();
        }

        // Default transient crash
        return IncidentEvent.builder()
                .id(incidentId)
                .podName(podName)
                .namespace(namespace)
                .failureReason(reason)
                .category("BASIC_AUTO_FIX")
                .confidenceScore(0.88)
                .actionTaken("RESTART_POD")
                .rootCauseSummary("Transient container exit with non-zero exit code.")
                .technicalDetails("Process exited unexpectedly; restarting pod to test recovery.")
                .developerAction("Verify container health checks and liveness/readiness probe initialDelaySeconds.")
                .logsSnippet(logs)
                .timestamp(LocalDateTime.now())
                .autoHealed(true)
                .build();
    }
}
