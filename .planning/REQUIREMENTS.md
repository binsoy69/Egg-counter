# Requirements: Egg Counter

**Defined:** 2026-03-19
**Core Value:** Accurately count and classify eggs as they appear in nest boxes, with live results visible on a remote-accessible dashboard.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Detection

- [x] **DET-01**: User can detect eggs in nest box using YOLO11n model on Raspberry Pi 5
- [x] **DET-02**: System de-duplicates detections so each physical egg is counted exactly once (ByteTrack tracking)
- [x] **DET-03**: System classifies egg size (small, medium, large, jumbo) via visual estimation from bounding box dimensions
- [x] **DET-04**: Each detection is logged with timestamp and size classification

### Dashboard

- [x] **DASH-01**: User can view today's running egg count broken down by size
- [x] **DASH-02**: Dashboard updates in real-time via WebSocket when an egg is detected
- [x] **DASH-03**: User can mark eggs as collected via a "collected" action on the dashboard
- [ ] **DASH-04**: Dashboard is mobile-responsive for phone viewing

### Data

- [ ] **DATA-01**: User can view historical egg production charts over days and weeks

### Infrastructure

- [ ] **INFRA-01**: Dashboard is accessible remotely from phone via Cloudflare Tunnel
- [ ] **INFRA-02**: System auto-starts on Pi boot and auto-restarts on crash

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Dashboard

- **DASH-05**: System health/connection status indicator visible on dashboard
- **DASH-06**: Lighting/image quality warnings when frame is too dark for reliable detection

### Detection

- **DET-05**: Detection snapshot (cropped image saved with each egg event)
- **DET-06**: Configurable daily reset time (dawn vs midnight)

### Data

- **DATA-02**: Weekly/monthly production reports
- **DATA-03**: Laying pattern analysis (time-of-day heatmap)
- **DATA-04**: Data export (CSV/JSON download)

### Infrastructure

- **INFRA-03**: Pi temperature monitoring and alerts
- **INFRA-04**: Multi-camera / multi-box support

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Live camera feed streaming | Not needed -- just counts and data. Bandwidth and privacy concerns. |
| Push notifications to phone | Adds service worker complexity. Deferred to v2+. |
| Multi-user accounts / OAuth | Single-user system. Unnecessary complexity. |
| Egg weight measurement | Requires hardware scale. Visual estimation is the chosen approach. |
| Egg quality/defect detection | Substantially harder ML problem. Different product. |
| Model retraining UI | Training happens offline in v1. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DET-01 | Phase 1 | Complete |
| DET-02 | Phase 1 | Complete |
| DET-03 | Phase 1 | Complete |
| DET-04 | Phase 1 | Complete |
| DASH-01 | Phase 3 | Complete |
| DASH-02 | Phase 3 | Complete |
| DASH-03 | Phase 3 | Complete |
| DASH-04 | Phase 3 | Pending |
| DATA-01 | Phase 2 | Pending |
| INFRA-01 | Phase 4 | Pending |
| INFRA-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
