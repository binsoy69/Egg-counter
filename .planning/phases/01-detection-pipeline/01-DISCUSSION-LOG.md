# Phase 1: Detection Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 01-detection-pipeline
**Areas discussed:** Size classification approach, De-duplication & counting logic, Detection output & logging

---

## Size Classification Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Bounding box ratio | Use ratio of egg bbox to nest box width for size estimation | ✓ (try both) |
| Absolute pixel thresholds | Raw bbox pixel dimensions with fixed thresholds | |
| Multi-class YOLO model | Train YOLO with 4 size classes directly | ✓ (try both) |

**User's choice:** Try both bounding box ratio AND multi-class YOLO, compare accuracy to pick the winner.
**Notes:** User wants to benchmark both approaches. Whichever is more accurate wins, even if it means more annotation work. Nest box itself serves as the reference object (always visible, known dimensions).

### Follow-up: Reference object
| Option | Description | Selected |
|--------|-------------|----------|
| Nest box itself | Known dimensions, always in frame | ✓ |
| No fixed reference | Just eggs on bedding | |
| I can add one | Place a reference marker | |

### Follow-up: Tie-breaker preference
| Option | Description | Selected |
|--------|-------------|----------|
| Simpler one (ratio) | Prefer less training overhead | |
| More accurate one | Always pick best benchmark result | ✓ |

---

## De-duplication & Counting Logic

### New egg rule
| Option | Description | Selected |
|--------|-------------|----------|
| Zone-based trigger | Define nest box region, count when egg stable for N seconds | ✓ |
| Appearance-based | Count new track IDs that persist for N frames | |
| Frame diff + detection | Count when egg count in frame increases | |

**User's choice:** Zone-based trigger
**Notes:** YOLO detects → ByteTrack assigns track ID → enters zone → stable for N seconds → counted

### Occlusion handling
| Option | Description | Selected |
|--------|-------------|----------|
| Keep last known count | Maintain count when eggs hidden by hen | ✓ |
| Flag as uncertain | Log uncertainty, keep count | |

### Stability duration
| Option | Description | Selected |
|--------|-------------|----------|
| 3 seconds | Quick confirmation | ✓ |
| 5 seconds | Balanced speed/reliability | |
| 10 seconds | Very conservative | |

### Zone configuration
| Option | Description | Selected |
|--------|-------------|----------|
| One-time setup tool | Draw zone on camera frame, save to config | ✓ |
| Hardcoded coordinates | Manual config file editing | |
| Auto-detect nest box | CV-based automatic detection | |

### Daily reset
| Option | Description | Selected |
|--------|-------------|----------|
| Midnight | Reset at 00:00 | |
| Dawn / configurable time | Custom reset time (deferred to v2) | |
| Collection-based | Reset when eggs are collected | ✓ (custom) |

**User's choice:** Count resets when eggs are collected, not at a fixed time.
**Notes:** Ties into Phase 3 DASH-03 "collected" action. Phase 1 just logs events.

### Simultaneous eggs
| Option | Description | Selected |
|--------|-------------|----------|
| Count each independently | Each egg gets own track ID and timer | ✓ |
| Batch as single event | Group nearby detections | |

### Camera restart
| Option | Description | Selected |
|--------|-------------|----------|
| Re-count visible eggs | Detect existing eggs, mark as already-counted | ✓ |
| Start fresh from zero | Lose pre-restart count | |
| Resume from persisted count | Read from storage (Phase 2 dependency) | |

### Egg removal
| Option | Description | Selected |
|--------|-------------|----------|
| Ignore removals | Once counted, stays counted | |
| Track removals | Log removal events | ✓ (custom) |

**User's choice:** Egg removal is manual by the owner, always all at once. System should handle/log this.

### Collection pattern
| Option | Description | Selected |
|--------|-------------|----------|
| All at once | Owner collects every egg in one go | ✓ |
| Sometimes partial | Owner may take only some | |

### Night detection
| Option | Description | Selected |
|--------|-------------|----------|
| Daylight only | Skip detection at night | ✓ |
| 24/7 with IR | Run around the clock with IR camera | |
| You decide | Claude determines | |

---

## Detection Output & Logging

### Log format
| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON lines | One JSON object per line, machine-parseable | ✓ |
| Plain text log | Human-readable lines | |
| Both | JSON to file, readable to console | |

### Event data fields
| Option | Description | Selected |
|--------|-------------|----------|
| Confidence score | Model confidence 0.0-1.0 | ✓ |
| Bounding box coordinates | Position in frame | ✓ |
| Size method result | Which method used + raw measurement | ✓ |
| You decide the rest | Claude includes useful extras | ✓ |

### Console output
| Option | Description | Selected |
|--------|-------------|----------|
| Human-readable summary | Brief line to stdout on events | ✓ |
| JSON only to file | Silent operation | |

### Log path
| Option | Description | Selected |
|--------|-------------|----------|
| You decide | Claude picks sensible default, configurable | ✓ |
| Same directory as script | Log file next to detection script | |

### Log rotation
| Option | Description | Selected |
|--------|-------------|----------|
| Daily rotation | One file per day | ✓ |
| Single file, no rotation | One growing file | |
| You decide | Claude determines | |

### Diagnostic logging
| Option | Description | Selected |
|--------|-------------|----------|
| Periodic health logs | System stats every N minutes | |
| Eggs only | Only detection/collection events | ✓ |
| You decide | Claude determines | |

---

## Claude's Discretion

- YOLO confidence threshold (sensible default, configurable)
- Log file storage path
- Additional event JSON fields beyond specified ones
- ByteTrack configuration details
- Edge case handling not explicitly discussed

## Deferred Ideas

- Configurable daily reset time (v2 — DET-06)
- System health/diagnostic logging as separate concern
- Night/IR detection capability
