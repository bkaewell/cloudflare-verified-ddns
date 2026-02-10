# SYSTEM_DESIGN.md

**cloudflare-verified-ddns**  
Lightweight, reliable Cloudflare DDNS updater with self-healing, persistent caching and uptime tracking

**Current date reference:** February 09, 2026  
**Target use case:** High-availability WireGuard VPN server behind dynamic residential/public IP

## Core Design Principles

The system is intentionally built around four interlocking goals:

1. **Scalability**  
   Designed to grow with the number of sub-domains managed inside a single Cloudflare zone.  
   → Adding more DNS → IP mappings requires only additional sub-domain records (no code or container changes).  
   → Horizontal scaling is not currently needed (single container), but vertical scaling (more sub-domains) is trivial.

2. **Maintainability**  
   - Open-source on GitHub with clear structure (`src/cloudflare_verified_ddns/`)  
   - Poetry for dependency management → reproducible builds  
   - Comprehensive documentation (this file + ARCHITECTURE.md, TUNING.md, VPN-DNS-STACK.md)  
   - Non-root container user (`app`) → security & clarity  
   - Minimal external dependencies → easy onboarding for contributors

3. **Efficiency**  
   - Final image size **47.2 MB** (python:3.13-alpine base + minimal deps + no pip/setuptools/wheel at runtime)  
   - Multi-stage build + aggressive cleanup (pip removal, bytecode deletion)  
   - Named volume for cache → zero disk writes to container layer  
   - Low CPU/memory footprint → suitable for Raspberry Pi, tiny VPS, home server

4. **Reliability**  
   Primary non-functional requirement: the system works consistently under normal conditions and **gracefully handles and recovers from failures** without manual intervention.  
   → Measured uptime consistently ~99.9 % or better (via `uptime.json`: READY loops / total loops)  
   → Aspirational target: 5-nines (99.999 %, ~5 min downtime/year)  
   → Realistic current target: 99.9 % (~8.76 hours downtime/year)

   **Important caveat**: Availability is ultimately limited by the **weakest link in the chain** (power company and ISP reliability).

   ### Reliability Goals & Observability

   - **Target Availability Levels**

     | Availability | Downtime per year | Classification       | Current status                  | Notes / Measurement |
     |--------------|-------------------|----------------------|---------------------------------|----------------------|
     | 99.999 %     | ~5 minutes        | 5-nines (aspirational) | Not yet achieved               | Industry gold standard |
     | **99.9 %**   | ~8.76 hours       | **Current realistic target** | **Achieved** (ongoing)         | Measured via `uptime.json` |
     | 99 %         | ~3.65 days        | Minimum acceptable   | Exceeded comfortably           | Baseline for self-hosted |

   - **Service Level Objective (SLO)**  
     Internal measurable target: Public IP request latency < 100 ms at p99.9  
     → Achieved via fast HTTP GET + caching  
     → Loop runtime consistently ~100 ms in production

   - **Service Level Agreement (SLA)**  
     Formal external promise to users: **None committed**  
     → Early-stage OSS; no contractual uptime/latency guarantees  
     → Focus on internal observability instead

   - **How Reliability Is Achieved**

     - **Redundancy**  
       - Multiple public IP providers  
       - Dual power (wall + UPS battery backup)  
       - Persistent volume for cache & uptime

     - **Fault Tolerance & Self-Healing**  
       - Readiness FSM (probes → READY after 2 confirmations)  
       - Recovery Controller + configurable Recovery Policy  
       - Smart-plug power toggle (HTTP GET) for hardware reset

     - **Observability**  
       - Uptime % in `uptime.json`  
       - Cache hit/miss/expired/refresh logging  
       - Loop timing & RTT metrics in logs

This combination delivers **high reliability with minimal operational overhead**, suitable for a self-hosted high-availability VPN endpoint — while acknowledging external utility limits.

## Core Data Flow Elements

The system can be understood through three fundamental activities:

1. **Moving data**  
   - Public IP → fetched via GET (multiple providers)  
   - DNS state → verified via DoH  
   - Update → PUT to Cloudflare API when mismatch  
   - Router/WAN health → ping + TLS probe (1.1.1.1:443)

2. **Storing data**  
   - Persistent JSON files (`/app/cache/cloudflare_verified_ddns/*.json`)  
   - Named Docker volume → survives container rebuilds/restarts  
   - Owned by non-root user (`app`) → secure write access

3. **Transforming data**  
   - Raw IP → verified → cached → uptime % calculated  
   - Cache age → freshness check → metrics → decision (no-op / update)

## Networking & Communication Summary

| Purpose                  | Protocol / Method | Endpoint / Target                     | Reliability feature                     |
|--------------------------|-------------------|---------------------------------------|------------------------------------------|
| Public IP detection      | HTTP GET          | ipify.org, ifconfig.me, icanhazip, ipecho | Multiple providers + fallback            |
| DNS verification         | DoH (HTTPS)       | Cloudflare DoH resolver               | Avoids unnecessary API writes            |
| DNS update               | HTTP PUT          | Cloudflare API                        | Only when needed + verified              |
| Router health            | ICMP ping         | local router (192.168.0.1)            | Fast local check                         |
| WAN path health          | TLS probe         | 1.1.1.1:443                           | Ensures outbound connectivity            |
| Smart plug power toggle  | HTTP GET          | smart-plug endpoint                   | Hardware-level recovery                  |

## Summary of Design Choices

- **Why Python 3.13 + alpine** → smallest possible runtime with modern features  
- **Why non-root user** → reduced attack surface (even if small container)  
- **Why persistent volume** → cache + uptime survive restarts/rebuilds  
- **Why readiness FSM** → prevents premature traffic routing  
- **Why recovery controller** → self-healing instead of fail-fast  
- **Why multiple IP sources** → no single point of failure for IP detection

This design prioritizes **simplicity + observability + resilience** over premature optimization or over-engineering.
