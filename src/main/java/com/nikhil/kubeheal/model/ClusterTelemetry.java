package com.nikhil.kubeheal.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ClusterTelemetry {
    private int totalPods;
    private int healthyPods;
    private int failingPods;
    private int autoHealedCount;
    private int rcaReportsCount;
    private String clusterStatus;     // HEALTHY, DEGRADED, RECOVERING
}
