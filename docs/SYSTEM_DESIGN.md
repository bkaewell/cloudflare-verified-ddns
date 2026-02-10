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

4. **Reliability** (the primary non-functional requirement)

   Broken into three tightly related concepts:

   - **Reliability** — the system works consistently under normal conditions  
     → `restart: unless-stopped` policy  
     → readiness FSM (probing → ready transition after 2 confirmations)  
     → persistent JSON cache + uptime tracking

   - **Fault Tolerance** — the system maintains composure when things go wrong  
     → Recovery Controller + Recovery Policy (handles transient failures)  
     → Self-healing: retries, backoff, circuit-breaker-like logic  
     → Smart plug integration (HTTP GET to toggle power on full failure)

   - **Redundancy** — backup mechanisms reduce single points of failure  
     → Dual power (wall + UPS battery backup)  
     → Persistent volume for cache (survives container restarts/rebuilds)  
     → Multiple public IP sources (ipify, ifconfig.me, icanhazip, ipecho)  
     → DoH verification before update (avoids unnecessary Cloudflare writes)

**Golden target (aspirational):** 5-nines (99.999 %) availability  
→ 5 minutes of downtime per year  
→ Current realistic target: **99.9 %** (~8.76 hours downtime/year)  
→ Measured via uptime.json (total loops vs READY loops)

**SLO / SLA discussion**  
- **SLO** (internal goal): <100 ms response time to public IP request at p99.9  
  → Currently achieved via fast HTTP GET + caching  
- **SLA** (external promise to users): **not committed yet**  
  → Too early for formal uptime guarantees  
  → Focus remains on internal observability (uptime %, cache hit rate, loop latency)

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

Future work candidates:
- Prometheus metrics endpoint
- Multi-provider DNS support (not just Cloudflare)
- Multi-arch images (amd64/arm64/v7)
- GitHub Actions CI (lint, test, build, push)

Feedback & contributions welcome — MIT licensed.