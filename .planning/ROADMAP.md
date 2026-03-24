# Roadmap: Egg Counter

## Overview

This project builds a real-time egg counting and size classification system on a Raspberry Pi 5. The build order follows the data flow: first make detection correct (the hardest problem), then make it durable with persistence, then make it visible with a dashboard, then make it accessible remotely with hardening. Each phase delivers a verifiable capability that the next phase depends on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Detection Pipeline** - YOLO-based egg detection, tracking, and size classification running on the Pi
- [ ] **Phase 2: Data Persistence** - SQLite storage of egg events with historical data and daily aggregation
- [ ] **Phase 3: Web Dashboard** - Live mobile-friendly dashboard showing counts, size breakdown, and trends
- [ ] **Phase 4: Remote Access and Hardening** - Cloudflare Tunnel for remote phone access and systemd for production reliability

## Phase Details

### Phase 1: Detection Pipeline
**Goal**: User can run a detection process on the Pi that correctly identifies, de-duplicates, and classifies eggs in the nest box
**Depends on**: Nothing (first phase)
**Requirements**: DET-01, DET-02, DET-03, DET-04
**Success Criteria** (what must be TRUE):
  1. Running the detection process with a camera pointed at the nest box prints a notification when a new egg appears, including its size classification
  2. An egg sitting in the nest box for minutes or hours is counted exactly once, not repeatedly
  3. Each detected egg is classified as small, medium, large, or jumbo based on its visual size
  4. Each detection event is logged with a timestamp and size classification to stdout or a log file
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, config, zone, logger, scheduler, and zone setup tool
- [x] 01-02-PLAN.md — Size classifier (bbox ratio method) and egg tracker (de-duplication, stability, restart)
- [x] 01-03-PLAN.md — YOLO detector wrapper, pipeline integration, and CLI entry point
- [x] 01-04-PLAN.md — GUI preview mode for visual verification (gap closure)

### Phase 2: Data Persistence
**Goal**: Egg detection events are durably stored and queryable, surviving reboots and power loss
**Depends on**: Phase 1
**Requirements**: DATA-01
**Success Criteria** (what must be TRUE):
  1. Detected eggs are written to a SQLite database on the Pi's SD card immediately upon detection
  2. After a Pi reboot, the database retains all previously recorded egg events and today's count resumes correctly
  3. User can query historical egg production data grouped by day and by size category
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — SQLite logger (drop-in replacement), query/DAO class, and pipeline integration

### Phase 3: Web Dashboard
**Goal**: User can view live egg counts, manage collections, and see production trends from a phone browser on the local network
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. Opening the dashboard in a phone browser shows today's running egg count broken down by size (small, medium, large, jumbo)
  2. When a new egg is detected, the dashboard updates within seconds without the user refreshing the page
  3. User can tap a "collected" action on the dashboard to mark eggs as collected
  4. The dashboard is readable and usable on a phone screen without horizontal scrolling or broken layout
  5. User can view historical egg production charts showing trends over days and weeks
**Plans**: TBD

Plans:
- [x] 03-01: TBD
- [x] 03-02: TBD

### Phase 4: Remote Access and Hardening
**Goal**: The system is accessible from anywhere on a phone and runs reliably without manual intervention
**Depends on**: Phase 3
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. User can open the dashboard from a phone on cellular data (outside the local network) via a stable HTTPS URL
  2. After a Pi reboot or power cycle, the detection process and web server start automatically without manual intervention
  3. If the detection process crashes, it restarts automatically within seconds
**Plans**: 2 plans

Plans:
- [x] 04-01 - Application-managed authentication for dashboard, API, and websocket access
- [x] 04-02 - Deployment/systemd/cloudflared artifacts and operator runbook

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Detection Pipeline | 3/4 | Gap closure | - |
| 2. Data Persistence | 1/1 | Human verification | - |
| 3. Web Dashboard | 1/2 | In progress | - |
| 4. Remote Access and Hardening | 2/2 | Human verification | - |
