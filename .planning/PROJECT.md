# Egg Counter

## What This Is

A real-time egg counting and size classification system for a small hobby farm. A Raspberry Pi 5 with a USB camera monitors nest boxes, uses a YOLO model to detect eggs and classify their size (small, medium, large, jumbo), and pushes results via WebSocket to a web dashboard accessible remotely from a phone.

## Core Value

Accurately count and classify eggs as they appear in nest boxes, with live results visible on a remote-accessible dashboard.

## Requirements

### Validated

- [x] Detect eggs in nest box using YOLO model on Raspberry Pi 5 — Validated in Phase 1: Detection Pipeline
- [x] Classify egg size (small, medium, large, jumbo) via visual estimation — Validated in Phase 1: Detection Pipeline

### Active
- [ ] Display running count of today's eggs broken down by size on web dashboard
- [ ] Show historical egg production data with charts/trends over days and weeks
- [ ] Push real-time updates from Pi to dashboard via WebSocket when eggs are detected
- [ ] Dashboard accessible remotely from phone (not just local network)
- [ ] Alert/notification on dashboard when a new egg is detected

### Out of Scope

- Live camera feed on dashboard — not needed, just counts and data
- Push notifications to phone — deferred to v2, v1 is web dashboard only
- Multiple user accounts — single user access
- Egg weight measurement — using visual estimation only, no scale hardware
- OAuth/social login — unnecessary for single-user system

## Context

- **Hardware**: Raspberry Pi 5 with USB camera positioned at nest box exit
- **Detection model**: Latest YOLO (likely YOLOv8/v11) trained on egg dataset
- **Scale**: Small flock, under 100 eggs per day
- **Environment**: Farm setting — camera must handle variable lighting in nest boxes
- **Size classification**: Based on visual estimation from the model, no additional hardware (scale, calipers)
- **Viewing**: Single user checks dashboard remotely from phone throughout the day

## Constraints

- **Hardware**: Raspberry Pi 5 — model must be optimized for edge inference (limited GPU/NPU)
- **Camera**: USB camera — need to handle variable lighting and nest box angles
- **Network**: Pi needs internet/network access to serve the dashboard remotely
- **Model accuracy**: Visual size classification is inherently less precise than weight-based — acceptable tradeoff for no extra hardware

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| YOLO for detection | User preference, strong real-time performance on edge devices | Implemented (Phase 1) |
| WebSocket for real-time updates | Instant push to dashboard when egg detected, no polling delay | — Pending |
| Visual size estimation | No extra hardware needed, acceptable accuracy for hobby farm | Implemented (Phase 1) — bbox ratio method with USDA thresholds |
| Remote access | User wants to check from phone anywhere, not just local network | — Pending |

---
*Last updated: 2026-03-23 after Phase 1 completion*
