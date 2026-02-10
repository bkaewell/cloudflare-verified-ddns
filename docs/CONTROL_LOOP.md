# Control Loop – Supervisor & Scheduling

## Overview

The top-level infinite loop (`run_supervisor_loop`) is the heartbeat of the agent.

**Responsibilities:**
- Run the DDNS cycle repeatedly
- Capture & log unhandled exceptions
- Delegate next-sleep decision to `SchedulingPolicy`
- Maintain adaptive polling cadence

**Key properties:**
- Never exits (lifecycle managed externally by Docker)
- Exceptions are contained and surfaced via telemetry
- Scheduling is adaptive to avoid API abuse and tight loops

## Supervisor Loop Flow

```mermaid
flowchart TD
    Start((Start)) --> LoopStart[Loop Start]
    LoopStart --> Cycle["ddns.run_cycle()"]
    Cycle --> Success{No Exception?}
    Success -->|Yes| MeasureTime[Measure elapsed]
    Success -->|No| LogError[Log exception<br>supervisor_state = ERROR]
    MeasureTime --> Decide["scheduler.next_schedule()"]
    LogError --> Decide
    Decide --> Sleep["time.sleep(sleep_for)"]
    Sleep --> LoopStart
```

## Polling Cadence & Scheduler

```mermaid
stateDiagram-v2
    direction LR
    [*] --> PROBING
    PROBING --> READY: 2 consecutive<br/> IP confirmations
    READY --> RECOVERY: Recovery policy<br/> triggered
    RECOVERY --> PROBING: Reset

    state Cadence {
        PROBING --> FAST_POLL
        READY --> SLOW_POLL
        RECOVERY --> FAST_POLL
    }
```

- `FAST_POLL` (~30 s) during `PROBING` → quick convergence
- `SLOW_POLL` (~120 s) in steady state → reduce API load
- Jitter (0–10 s) prevents synchronized polling spikes if multiple instances run

### Why this design?
- No external cron/systemd timer → single-process simplicity
- Adaptive cadence balances freshness vs rate-limiting
- Exception containment prevents crash loops
- Jitter avoids thundering herd
- Fully observable via structured logs (cadence, sleep, jitter)
