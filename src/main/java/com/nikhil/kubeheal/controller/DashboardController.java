package com.nikhil.kubeheal.controller;

import com.nikhil.kubeheal.model.ClusterTelemetry;
import com.nikhil.kubeheal.model.IncidentEvent;
import com.nikhil.kubeheal.service.KubeWatcherService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Controller
public class DashboardController {

    private final KubeWatcherService watcherService;

    public DashboardController(KubeWatcherService watcherService) {
        this.watcherService = watcherService;
    }

    @GetMapping("/")
    public String index(Model model) {
        ClusterTelemetry telemetry = watcherService.getTelemetry();
        List<IncidentEvent> incidents = watcherService.getIncidentHistory();

        model.addAttribute("telemetry", telemetry);
        model.addAttribute("incidents", incidents);
        return "dashboard";
    }

    @PostMapping("/api/chaos/inject")
    public String injectChaos(@RequestParam(defaultValue = "TRANSIENT") String type) {
        watcherService.injectSimulatedChaos(type);
        return "redirect:/";
    }

    @GetMapping("/api/telemetry")
    @ResponseBody
    public ClusterTelemetry getTelemetryApi() {
        return watcherService.getTelemetry();
    }
}
