# Architecture


```mermaid
flowchart TB
    %% Power & Initialization
    UPS[UPS Battery Backup]
    BOOT([Power On])

    NET[Netplan<br/>Stable LAN IP<br/>192.168.0.123]

    %% Services
    subgraph SERVICES["Always-On Services"]
        DDNS[Cloudflare-Verified-DDNS<br/>47 MB Image<br/>Authoritative DNS Publisher]
        WG[WireGuard VPN<br/>DNS-Based Endpoint]
    end

    %% Power Semantics
    UPS --> BOOT
    UPS -. "Survives outage" .-> NET
    UPS -. "Continuous operation" .-> SERVICES

    %% Boot Sequence
    BOOT --> NET
    NET --> SERVICES

    %% Core Dependency
    DDNS -->|Publishes verified DNS record| WG

    %% Styling
    classDef power fill:#ededed,stroke:#333,stroke-width:2px;
    classDef network fill:#fff2cc,stroke:#333,stroke-width:2px;
    classDef service fill:#f5f7fa,stroke:#333,stroke-width:2px;
    classDef vpn fill:#e2f0d9,stroke:#333,stroke-width:2px;

    class UPS,BOOT power;
    class NET network;
    class DDNS service;
    class WG vpn;
```






```mermaid
flowchart TB
    %% Power & Boot
    UPS[UPS Battery Backup<br/>Power Continuity] --> BOOT([Power On / Boot])

    BOOT --> NET[Netplan<br/>Assigns Stable LAN IP<br/>192.168.0.123]

    %% Host System
    subgraph HOST["Linux Host (Always-On)"]
        NET --> DOCKER[Docker Engine<br/>restart: unless-stopped]

        %% Containers
        subgraph CONTAINERS["Docker Containers"]
            DDNS[Cloudflare-Verified-DDNS<br/>Public IP → Cloudflare DNS]
            WG[WG-Easy WireGuard VPN<br/>UDP 51820<br/>TCP 51821]
        end

        DOCKER --> DDNS
        DOCKER --> WG
    end

    %% Styling
    classDef power fill:#e6e6e6,stroke:#333,stroke-width:2px;
    classDef network fill:#fff2cc,stroke:#333,stroke-width:2px;
    classDef host fill:#ddebf7,stroke:#333,stroke-width:2px;
    classDef docker fill:#cfe2f3,stroke:#333,stroke-width:2px;
    classDef container fill:#fce5cd,stroke:#333,stroke-width:2px;
    classDef vpn fill:#d9ead3,stroke:#333,stroke-width:2px;

    class UPS,BOOT power;
    class NET network;
    class HOST host;
    class DOCKER docker;
    class DDNS container;
    class WG vpn;
```





```mermaid
flowchart TB
    %% Physical Layer
    subgraph PHYSICAL["Physical Layer"]
        UPS[UPS Battery Backup]
        BOOT([Power On / Boot])
        UPS --> BOOT
    end

    %% Network Layer
    subgraph NETWORK["Network Initialization"]
        NET[Netplan<br/>Static LAN IP<br/>192.168.0.123]
    end

    %% Runtime Layer
    subgraph RUNTIME["Service Runtime"]
        DOCKER[Docker Engine<br/>restart: unless-stopped]

        subgraph SERVICES["Containers"]
            DDNS[Cloudflare-Verified-DDNS<br/>Public IP → DNS]
            WG[WG-Easy WireGuard VPN<br/>UDP 51820 / TCP 51821]
        end
    end

    BOOT --> NET
    NET --> DOCKER
    DOCKER --> DDNS
    DOCKER --> WG
    UPS --> NET
    UPS --> DOCKER

    %% Styling
    classDef physical fill:#eeeeee,stroke:#333,stroke-width:2px;
    classDef network fill:#fff2cc,stroke:#333,stroke-width:2px;
    classDef runtime fill:#ddebf7,stroke:#333,stroke-width:2px;
    classDef container fill:#fce5cd,stroke:#333,stroke-width:2px;
    classDef vpn fill:#d9ead3,stroke:#333,stroke-width:2px;

    class UPS,BOOT physical;
    class NET network;
    class DOCKER runtime;
    class DDNS container;
    class WG vpn;
```






```mermaid
flowchart TB
    UPS[UPS Battery Backup<br/>Survives Power Outages]

    BOOT([Power On / Boot Sequence])
    NET[Netplan<br/>Stable LAN IP<br/>192.168.0.123]

    subgraph HOST["Always-On Linux Host"]
        DOCKER[Docker Engine<br/>Auto-Restart Policy]

        subgraph CONTAINERS["Critical Services"]
            DDNS[Cloudflare-Verified-DDNS<br/>Ensures DNS Accuracy]
            WG[WireGuard VPN Server<br/>Secure Remote Access]
        end
    end

    UPS --> BOOT
    UPS --> NET
    UPS --> DOCKER

    BOOT --> NET
    NET --> DOCKER
    DOCKER --> DDNS
    DOCKER --> WG

    %% Styling
    classDef power fill:#e6e6e6,stroke:#333,stroke-width:2px;
    classDef network fill:#fff2cc,stroke:#333,stroke-width:2px;
    classDef host fill:#ddebf7,stroke:#333,stroke-width:2px;
    classDef container fill:#fce5cd,stroke:#333,stroke-width:2px;
    classDef vpn fill:#d9ead3,stroke:#333,stroke-width:2px;

    class UPS,BOOT power;
    class NET network;
    class HOST host;
    class DDNS container;
    class WG vpn;
```




```mermaid
flowchart TB
    %% Power & Resilience
    UPS[UPS Battery Backup]

    BOOT([Power On / Boot Sequence])
    NET[Netplan<br/>Static LAN IP<br/>192.168.0.123]

    %% Host System
    subgraph HOST["Edge Node / Always-On Linux System"]
        DOCKER[Docker Engine<br/>restart: unless-stopped]

        subgraph CONTAINERS["Docker Containers"]
            DDNS[Cloudflare-Verified-DDNS<br/>Image Size: 47 MB<br/>Authoritative Public IP Publisher]
            WG[WG-Easy WireGuard VPN<br/>Secure Remote Access<br/>DNS-Based Endpoint Resolution]
        end
    end

    %% Power Flow
    UPS --> BOOT
    UPS -. "Survives power outage" .-> NET
    UPS -. "Ensures continuous operation" .-> DOCKER

    %% Boot & Runtime Flow
    BOOT --> NET
    NET --> DOCKER
    DOCKER --> DDNS
    DOCKER --> WG

    %% DNS Dependency
    DDNS -->|Maintains accurate DNS A/AAAA records| WG

    %% Styling
    classDef power fill:#e6e6e6,stroke:#333,stroke-width:2px;
    classDef network fill:#fff2cc,stroke:#333,stroke-width:2px;
    classDef host fill:#ddebf7,stroke:#333,stroke-width:2px;
    classDef docker fill:#cfe2f3,stroke:#333,stroke-width:2px;
    classDef container fill:#fce5cd,stroke:#333,stroke-width:2px;
    classDef vpn fill:#d9ead3,stroke:#333,stroke-width:2px;

    class UPS,BOOT power;
    class NET network;
    class HOST host;
    class DOCKER docker;
    class DDNS container;
    class WG vpn;
```



```mermaid
flowchart TD
    %% Boot Sequence Diagram for Cloudflare Verified DDNS + WireGuard VPN
    A[Power On / Boot] --> B[Netplan Configures LAN IP]
    B --> C[Stable LAN IP: 192.168.0.123]
    C --> D[Always-Running Services]

    %% Services
    D --> E[Cloudflare-Verified-DDNS<br/>Public IP --> Cloudflare DNS]
    D --> F[WG-Easy WireGuard VPN<br/>UDP 51820 / TCP 51821]

    %% UPS
    UPS[UPS Battery Backup<br/>Ensures Continuous Operation] --> E
    UPS --> F

    %% Style / notes
    classDef power fill:#f9f,stroke:#333,stroke-width:2px;
    classDef network fill:#ffeb99,stroke:#333,stroke-width:2px;
    classDef services fill:#99ccff,stroke:#333,stroke-width:2px;
    classDef container fill:#ffcc99,stroke:#333,stroke-width:2px;
    classDef vpn fill:#99ff99,stroke:#333,stroke-width:2px;
    classDef ups fill:#cccccc,stroke:#333,stroke-width:2px;

    class A power;
    class B,C network;
    class D services;
    class E container;
    class F vpn;
    class UPS ups;
```








## Overview

This project implements a **self-healing network watchdog** that continuously verifies WAN health and ensures that a device’s **public IP address remains consistent with its Cloudflare DNS record**.

The system is designed for **24/7 unattended operation**, optimized for:
- Fast no-op behavior under healthy conditions
- High signal-to-noise telemetry
- Conservative, state-driven recovery actions
- Clear separation of observation, decision-making, and mutation

It is intentionally **policy-driven**, **idempotent**, and **failure-aware**.

---

## Core Responsibilities

The watchdog performs one evaluation loop per cycle. Each execution cycle follows a strict **observe → assess → act** model:

1. **Observe**
   - Router reachability (LAN)
   - WAN path reachability
   - Public IP resolution

2. **Assess**
   - Build confidence in WAN stability across cycles
   - Classify WAN health (UP / DEGRADED / DOWN)
   - Track sustained failure streaks via a finite state machine (FSM)
   - Derive a single `NetworkState`

3. **Act**
   - Reconcile DNS when WAN is stable and when IP drift is confirmed
   - Escalate recovery only on sustained failure
   - Reset failure state on successful recovery
   - Emit structured telemetry

---

## High-Level Architecture (ASCII)

┌────────────────────┐
│  main_loop()       │
│  (Supervisor)      │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ NetworkWatchdog    │
│ evaluate_cycle()   │
└─────────┬──────────┘
          │
 ┌────────┼─────────┐
 │        │         │
 ▼        ▼         ▼
LAN     WAN      Public IP
Probe   Probe    Resolution
 │        │         │
 └────────┼─────────┘
          ▼
 WAN Health Classifier
          │
          ▼
    WanFSM (Policy)
          │
          ▼
 DNS Sync / Recovery

 ---

## State Model
### WAN Health (Internal)
| State      | Meaning                        |
| ---------- | ------------------------------ |
| `UP`       | Public IP stable across cycles |
| `DEGRADED` | Reachable but not yet trusted  |
| `DOWN`     | Unreachable or failing         |


### Network State (External)
| State      | Meaning                               |
| ---------- | ------------------------------------- |
| `HEALTHY`  | All systems nominal                   |
| `DEGRADED` | WAN reachable but unstable            |
| `DOWN`     | WAN unavailable or router unreachable |
| `ERROR`    | Internal failure                      |
| `UNKNOWN`  | Fallback                              |

---

## WAN Health State Diagram (ASCII)

            ┌─────────────┐
            │             │
            │    DOWN     │◄──────────────┐
            │             │               │
            └─────▲───────┘               │
                  │                       │
        sustained │ failures              │
                  │                       │
            ┌─────┴───────┐        probe failure
            │             │─────────────────────┐
            │  DEGRADED   │                     │
            │             │─────────────────────┘
            └─────▲───────┘
                  │
       stable IP  │
      confirmed   │
                  │
            ┌─────┴───────┐
            │             │
            │     UP      │
            │             │
            └─────────────┘

---

## WAN Health State Diagram (Mermaid)

stateDiagram-v2
    [*] --> DEGRADED
    DEGRADED --> UP : IP stable across cycles
    UP --> DEGRADED : instability detected
    DEGRADED --> DOWN : sustained failures
    DOWN --> DEGRADED : partial recovery

---

## Failure Escalation Policy
TBD

---

## DNS Reconciliation Strategy
TBD

---


