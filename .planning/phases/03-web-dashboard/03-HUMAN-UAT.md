---
status: partial
phase: 03-web-dashboard
source: [03-VERIFICATION.md]
started: 2026-03-24T00:00:00Z
updated: 2026-03-24T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live count on phone browser
expected: Navigate to http://<pi-ip>:8000/dashboard and confirm count display with size breakdown, no horizontal scroll
result: [pending]

### 2. Real-time WebSocket update
expected: Trigger a detection event, verify count increments on screen without page refresh and toast shows "1 new egg added"
result: [pending]

### 3. Collection flow
expected: Tap "Collected", confirm dialog, verify count resets to 0 and persists after refresh
result: [pending]

### 4. History page filters
expected: Apply size/date filters on /history, confirm newest-first ordering and no horizontal scroll
result: [pending]

### 5. Hamburger nav
expected: On sub-720px phone screen, nav links collapse behind hamburger button and expand correctly when tapped
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
