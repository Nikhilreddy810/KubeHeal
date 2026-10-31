package com.nikhil.kubeheal.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IncidentEvent {
    private String id;
    private String podName;
    private String namespace;
    private String failureReason;
    private String category;          // BASIC_AUTO_FIX vs COMPLEX_CODE_BUG
    private double confidenceScore;
    private String actionTaken;        // RESTART_POD, ROLLBACK_DEPLOYMENT, REPORT_ONLY
    private String rootCauseSummary;
    private String technicalDetails;
    private String developerAction;
    private String logsSnippet;
    private LocalDateTime timestamp;
    private boolean autoHealed;
}
