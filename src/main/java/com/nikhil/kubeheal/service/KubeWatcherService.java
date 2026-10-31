package com.nikhil.kubeheal.service;

import com.nikhil.kubeheal.model.ClusterTelemetry;
import com.nikhil.kubeheal.model.IncidentEvent;
import io.fabric8.kubernetes.api.model.Pod;
import io.fabric8.kubernetes.client.KubernetesClient;
import io.fabric8.kubernetes.client.KubernetesClientBuilder;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class KubeWatcherService {

    private static final Logger log = LoggerFactory.getLogger(KubeWatcherService.class);

    @Value("${kubeheal.target-namespace:default}")
    private String targetNamespace;

    @Value("${kubeheal.auto-remediation-enabled:true}")
    private boolean autoRemediationEnabled;

    private final AIEngineService aiEngine;
    private KubernetesClient k8sClient;

    private final List<IncidentEvent> incidentHistory = new CopyOnWriteArrayList<>();
    private final Map<String, Long> debouncedPods = new ConcurrentHashMap<>();

    private int autoHealedCount = 0;
    private int rcaReportsCount = 0;

    public KubeWatcherService(AIEngineService aiEngine) {
        this.aiEngine = aiEngine;
    }

    @PostConstruct
    public void startWatcher() {
        try {
            this.k8sClient = new KubernetesClientBuilder().build();
            log.info("Connected to Kubernetes API server successfully.");

            // Start non-blocking thread to watch pod events
            Thread watcherThread = new Thread(this::watchPodsLoop, "KubeHeal-Watcher");
            watcherThread.setDaemon(true);
            watcherThread.start();
        } catch (Exception e) {
            log.warn("Could not connect to live Kubernetes API ({}); running in offline simulated mode.", e.getMessage());
            seedDemoIncidents();
        }
    }

    private void watchPodsLoop() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                k8sClient.pods().inNamespace(targetNamespace).watch(new io.fabric8.kubernetes.client.Watcher<Pod>() {
                    @Override
                    public void eventReceived(Action action, Pod pod) {
                        handlePodEvent(pod);
                    }

                    @Override
                    public void onClose(io.fabric8.kubernetes.client.WatcherException cause) {
                        log.warn("Pod watcher stream closed: {}. Reconnecting...", cause != null ? cause.getMessage() : "normal");
                    }
                });
            } catch (Exception e) {
                log.error("Watcher encountered error: {}. Retrying in 5 seconds...", e.getMessage());
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException ignored) {}
            }
        }
    }

    public synchronized void handlePodEvent(Pod pod) {
        if (pod == null || pod.getStatus() == null) return;
        String podName = pod.getMetadata().getName();

        String failingReason = checkFailingState(pod);
        if (failingReason == null) return;

        long now = System.currentTimeMillis();
        Long lastSeen = debouncedPods.get(podName);
        if (lastSeen != null && now - lastSeen < 60_000) {
            return; // Debounce within 60s
        }
        debouncedPods.put(podName, now);

        log.warn("Detected failure on pod {} (Reason: {})", podName, failingReason);

        String logs = extractLogs(podName);
        IncidentEvent incident = aiEngine.triageFailure(podName, targetNamespace, failingReason, logs, "");

        if (incident.isAutoHealed() && autoRemediationEnabled) {
            boolean success = remediate(podName);
            incident.setAutoHealed(success);
            autoHealedCount++;
        } else {
            rcaReportsCount++;
        }

        incidentHistory.add(0, incident);
    }

    private boolean remediate(String podName) {
        try {
            log.info("Executing auto-remediation: restarting pod {}", podName);
            if (k8sClient != null) {
                k8sClient.pods().inNamespace(targetNamespace).withName(podName).delete();
            }
            return true;
        } catch (Exception e) {
            log.error("Failed to delete pod {}: {}", podName, e.getMessage());
            return false;
        }
    }

    private String extractLogs(String podName) {
        try {
            if (k8sClient != null) {
                return k8sClient.pods().inNamespace(targetNamespace).withName(podName).tailingLines(50).getLog();
            }
        } catch (Exception e) {
            return "Could not retrieve live logs: " + e.getMessage();
        }
        return "Process terminated abnormally with exit code 1";
    }

    private String checkFailingState(Pod pod) {
        if (pod.getStatus().getContainerStatuses() != null) {
            for (var cs : pod.getStatus().getContainerStatuses()) {
                if (cs.getState() != null && cs.getState().getWaiting() != null) {
                    String reason = cs.getState().getWaiting().getReason();
                    if ("CrashLoopBackOff".equalsIgnoreCase(reason) ||
                        "OOMKilled".equalsIgnoreCase(reason) ||
                        "ImagePullBackOff".equalsIgnoreCase(reason) ||
                        "ErrImagePull".equalsIgnoreCase(reason) ||
                        "Error".equalsIgnoreCase(reason)) {
                        return reason;
                    }
                }
                if (cs.getState() != null && cs.getState().getTerminated() != null) {
                    String reason = cs.getState().getTerminated().getReason();
                    if ("OOMKilled".equalsIgnoreCase(reason) || "Error".equalsIgnoreCase(reason)) {
                        return reason;
                    }
                }
            }
        }
        return null;
    }

    public ClusterTelemetry getTelemetry() {
        int total = 12;
        int failing = 0;
        try {
            if (k8sClient != null) {
                var list = k8sClient.pods().inNamespace(targetNamespace).list();
                total = list.getItems().size();
            }
        } catch (Exception ignored) {}

        return ClusterTelemetry.builder()
                .totalPods(total)
                .healthyPods(Math.max(0, total - failing))
                .failingPods(failing)
                .autoHealedCount(autoHealedCount)
                .rcaReportsCount(rcaReportsCount)
                .clusterStatus("HEALTHY")
                .build();
    }

    public List<IncidentEvent> getIncidentHistory() {
        return Collections.unmodifiableList(incidentHistory);
    }

    public void injectSimulatedChaos(String failureType) {
        String podName = "flight-booking-" + UUID.randomUUID().toString().substring(0, 5);
        String reason = "CrashLoopBackOff";
        String logs = "Container process terminated with status 1";

        if ("OOM".equalsIgnoreCase(failureType)) {
            reason = "OOMKilled";
            logs = "java.lang.OutOfMemoryError: Java heap space\nKernel killed container process";
        } else if ("NULL_POINTER".equalsIgnoreCase(failureType)) {
            reason = "Error";
            logs = "java.lang.NullPointerException: Cannot invoke 'User.getUserId()' because 'customer' is null\n    at BookingServiceImpl.java:142";
        }

        IncidentEvent incident = aiEngine.triageFailure(podName, targetNamespace, reason, logs, "");
        if (incident.isAutoHealed()) {
            autoHealedCount++;
        } else {
            rcaReportsCount++;
        }
        incidentHistory.add(0, incident);
    }

    private void seedDemoIncidents() {
        injectSimulatedChaos("NULL_POINTER");
        injectSimulatedChaos("OOM");
    }

    @PreDestroy
    public void cleanup() {
        if (k8sClient != null) {
            k8sClient.close();
        }
    }
}
