# ─── Standard library imports ───
from typing import Optional

# ─── Project imports ───
from .logger import get_logger
from .cache import PersistentCache
from .cloudflare import CloudflareDNSProvider
from .readiness import ReadinessState
from .utils import (
    ping_host, 
    verify_wan_reachability, 
    get_ip, doh_lookup
)


class DDNSController:
    """
    Control-loop coordinator for WAN readiness and DDNS reconciliation.

    Responsibilities:
    • Observe LAN, WAN path, and public IP signals
    • Derive a single authoritative readiness verdict per cycle
    • Reconcile DNS only after stability is proven

    Design bias:
    • Conservative by default
    • Low-noise when healthy
    • Fail-fast and conservative
    """
    # ─── Class Constants ───
    # consecutive stable IPs required for READY
    PROMOTION_CONFIRMATIONS_REQUIRED: int = 2

    def __init__(
            self,
            *,
            router_ip: str, 
            max_cache_age_s: str,
            readiness: ReadinessState,
            dns_provider: CloudflareDNSProvider, 
            cache: PersistentCache,
        ):
        """
        Initialize the DDNS control loop.

        • Readiness FSM is the single source of truth
            • Startup assumes nothing about network health
        """

        # ─── Core Controle Plane (Single Source of Truth) ───
        self.readiness = readiness

        # ─── External Actuators ───
        self.dns_provider = dns_provider

        # ─── Environment & Topology ─── 
        self.router_ip = router_ip

        # ─── Policy & Control Parameters ─── 
        self.max_cache_age_s = max_cache_age_s

        # ─── Promotion / Stability Tracking (Probation Logic) ───         
        self.last_public_ip: Optional[str] = None
        self.promotion_votes: int = 0   # consecutive confirmations
        
        # ─── Metrics & Long-Lived Counters ───
        self.cache = cache
        self.uptime = cache.load_uptime()
        self.logger = get_logger("ddns")
        self.ready_confirmation_announced = False

    def _record_ip_observation(self, public_ip: Optional[str]) -> bool:
        """
        Track consecutive public IP observations for promotion gating.

        • IP change or missing value resets confidence
        • Matching consecutive IPs build confidence
        • Returns True only after required confirmations

        Keeps hysteresis out of the FSM and easy to reason about.
        """
        if not public_ip:
            self.promotion_votes = 0
            self.last_public_ip = None
            return False

        if public_ip == self.last_public_ip:
            self.promotion_votes += 1
        else:
            self.promotion_votes = 1
            self.last_public_ip = public_ip

        return self.promotion_votes >= DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED

    def _log_readiness_change(
        self,
        prev: ReadinessState,
        current: ReadinessState,
        promotion_votes: Optional[int] = None,
    ):
        """
        Emit a single log line for a readiness state transition.
        """

        prev = prev or ReadinessState.INIT
        transition = f"{prev.name} → {current.name}"
        meta = []

        if prev == ReadinessState.PROBING and current == ReadinessState.READY:
            meta.append(
                f"confirmations={promotion_votes}/"
                f"{DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED}"
            )

        # tlog(
        #     READINESS_EMOJI[current],
        #     "READINESS",
        #     "CHANGE",
        #     primary=transition,
        #     meta=" | ".join(meta) if meta else None,
        # )

        # ─── Future Work ───
        # Send notification via 3rd party messaging app
        #  - Telegram's @BotFather API 

    def _reconcile_dns_if_needed(self, public_ip: str) -> None:
        """
        Reconcile Cloudflare DNS with the current public IP.

        Invariants:
        • Called only when readiness is READY
        • Safe to call repeatedly (idempotent)
        • No mutation without authoritative confirmation

        Strategy:
        • L1: local cache (cheap no-op)
        • L2: DoH verification (truth without mutation)
        • L3: targeted update (only on confirmed drift)
        """

        # ─── L1 Local Cache (Cheap, fast no-op) ───
        # Only proceed to DoH if cache is absent, stale, or mismatched
        cache = self.cache.load_cloudflare_ip()
        cache_hit = cache.hit
        cache_fresh = cache_hit and (cache.age_s <= self.max_cache_age_s)
        cache_match = cache_fresh and (cache.ip == public_ip)

        if not cache_hit:
            cache_state = "MISS"
        elif not cache_fresh:
            cache_state = "EXPIRED"
        elif not cache_match:
            cache_state = "MISMATCH"
        else:
            cache_state = "HIT"

        # tlog(
        #     {
        #         "HIT": "🟢",
        #         "MISMATCH": "🟡",
        #         "EXPIRED": "🟠",
        #         "MISS": "🔴",
        #     }[cache_state],
        #     "CACHE",
        #     cache_state,
        #     primary=f"age={cache.age_s:.0f}s" if cache_hit else "no cache",
        #     meta=(
        #         f"rtt={cache.elapsed_ms:.1f}ms"
        #     ) if cache_hit else None,
        # )



        # if cache_state == "EXPIRED":
        #     self.logger.info(
        #         "DNS cache expired: age=%.0fs (ttl=%ss); refreshing authoritative state",
        #         cache.age_s,
        #         self.max_cache_age_s,
        #     )
        # elif cache_state == "MISMATCH":
        #     self.logger.warning(
        #         "DNS cache mismatch: cached_ip=%s desired_ip=%s; verifying authoritative state",
        #         cache.ip,
        #         public_ip,
        #     )
        # elif cache_state == "MISS":
        #     self.logger.debug("DNS cache miss: no cached Cloudflare IP found")



        if cache_match:
            self.logger.debug(
                "DDNS reconcile no-op: cache=%s age=%.0fs rtt=%.1fms",
                cache_state,
                cache.age_s,
                cache.elapsed_ms,
            )
            return  # Fast no-op: we trust the cache = DNS = current IP

        # ─── L2 Authoritative DoH lookup ───
        doh = doh_lookup(self.dns_provider.dns_name)

        if doh.success and doh.ip == public_ip:
            # tlog(
            #     "🟢",
            #     "DNS",
            #     "VERIFIED",
            #     primary=f"ip={doh.ip}",
            #     meta=f"rtt={doh.elapsed_ms:.0f}ms"
            # )
            self.cache.store_cloudflare_ip(public_ip)
            # tlog("🟢", "CACHE", "REFRESHED", primary=f"ttl={self.max_cache_age_s}s")
            # tlog("🌐", "DDNS", "NO-OP", primary="doh=verified")

            status = (
                "cache-refreshed-after-expiry"
                if cache_state == "EXPIRED"
                else "no-op(doh-verified)"
            )
            if cache_state == "EXPIRED":
                self.logger.warning(
                    "DDNS summary: status=%s | cache=%s rtt(cache=%.1fms,doh=%.0fms)",
                    status,
                    cache_state,
                    cache.elapsed_ms,
                    doh.elapsed_ms,
                )
            else:
                self.logger.debug(
                    "DDNS reconcile no-op: %s | cache=%s rtt(cache=%.1fms,doh=%.0fms)",
                    status,
                    cache_state,
                    cache.elapsed_ms,
                    doh.elapsed_ms,
                )

            return

        if not doh.success:
            self.logger.warning(
                "DDNS verify warning: DoH lookup failed, applying direct DNS update | dns=%s | cache=%s",
                self.dns_provider.dns_name,
                cache_state,
            )


        # ─── L3 Targeted update required (mutation) ───
        _, elapsed_ms = self.dns_provider.update_dns(public_ip)
        self.cache.store_cloudflare_ip(public_ip)

        # meta=[]
        # meta.append(f"rtt={elapsed_ms:.0f}ms")
        # meta.append(f"desired={public_ip}")
        # meta.append(f"ttl={self.dns_provider.ttl}s")
        # tlog(
        #     "🟢",
        #     "CLOUDFLARE",
        #     "UPDATED",
        #     primary=f"dns={self.dns_provider.dns_name}",
        #     meta=" | ".join(meta)
        # )
        # tlog("🟢", "CACHE", "REFRESHED", primary=f"ttl={self.max_cache_age_s}s")
        # tlog("🌐", "DDNS", "PUBLISHED", primary="reason=ip-mismatch")

        self.logger.info(
            "DDNS summary: status=updated | cache=%s rtt(update=%.0fms,cache=%.1fms)",
            cache_state,
            elapsed_ms,
            cache.elapsed_ms,
        )

    def _tick_uptime(self, readiness: ReadinessState) -> None:
        """
        Advance uptime counters for the current loop iteration.
        """
        self.uptime.total += 1

        if readiness == ReadinessState.READY:
            self.uptime.up += 1

        # Persist periodically (best-effort)
        # if self.uptime.total % 50 == 0:
        #     self.cache.store_uptime(self.uptime)

        self.cache.store_uptime(self.uptime)

    def run_cycle(self) -> None:
        """
        Execute one autonomous control-loop cycle.

        Phases:
        1. Observe raw network signals
        2. Assess readiness (FSM)
        3. Perform READY-only side effects (DDNS)
        4. Emit cycle summary and diagnostics
        """

        # ─── Observe: raw signals only ───
        # LAN (weak signal; informational only)
        lan = ping_host(self.router_ip)

        if not lan.success:
            self.logger.error(
                "L1/L2 LAN probe failed: gateway ICMP unreachable; " \
                "local link or router path may be unstable | " \
                "router=%s | rtt=%.0fms",
                self.router_ip,
                lan.elapsed_ms,
            )

        # WAN path reachability (strong signal; feeds Network Health FSM)
        wan = verify_wan_reachability(host="1.1.1.1", port=443)

        if not wan.success:
            self.logger.error(
                "L3/L4 WAN probe failed: no transport path to 1.1.1.1:443; " \
                "TLS/session verification cannot proceed | rtt=%.0fms",
                wan.elapsed_ms,
            )

        public = None
        allow_promotion = False

        can_observe_public_ip = (
            wan.success
            and self.readiness.state != ReadinessState.NOT_READY
        )

        in_promotion_window = (
            self.readiness.state == ReadinessState.PROBING
        )

        if can_observe_public_ip:
            public = get_ip()

            if not public.success:
                self.logger.error(
                    "L7 public IP probe failed: unable to fetch a valid " \
                    "public IP from the external IP service | rtt=%.0fms",
                    public.elapsed_ms,
                )

            if public.success and in_promotion_window:
                allow_promotion = self._record_ip_observation(public.ip)


        # ─── Assess: (FSM = single source of truth) ───
        prev = self.readiness.state
        self.readiness.advance(
            wan_path_ok=wan.success,
            allow_promotion = allow_promotion
        )
        current = self.readiness.state

        if prev != current:
            self._log_readiness_change(
                prev=prev,
                current=current,
                promotion_votes=self.promotion_votes,
            ) 

        entering_not_ready = (
            prev != ReadinessState.NOT_READY
            and current == ReadinessState.NOT_READY
        )

        if entering_not_ready:
            # Guarantees fresh evidence after NOT_READY transitions
            # (no promotion carryover, no stale IP stability).
            self.promotion_votes = 0
            self.last_public_ip = None
            self.ready_confirmation_announced = False


        # ─── Act: READY-only side effects ───
        if current == ReadinessState.READY and public and public.ip:
            # DDNS reconciliation (safe to act)
            self._reconcile_dns_if_needed(public.ip)
        
        self._tick_uptime(current)

        # ─── Report: Emit telemetry ───
        required = DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED
        if current == ReadinessState.PROBING:
            readiness_label = f"Verifying IP ... confirmations={self.promotion_votes}/{required}"
            self.ready_confirmation_announced = False
        elif current == ReadinessState.READY:
            confirmations = min(self.promotion_votes, required)
            if not self.ready_confirmation_announced:
                readiness_label = f"Verified DNS ✓ confirmations={confirmations}/{required}"
                self.ready_confirmation_announced = True
            else:
                readiness_label = "Verified DNS ✓"
        elif current == ReadinessState.NOT_READY:
            readiness_label = "Offline ✗"
            self.ready_confirmation_announced = False
        else:
            readiness_label = "Initializing ..."
            self.ready_confirmation_announced = False

        public_ip_summary = public.ip if public and public.success else "unknown"
        if current == ReadinessState.PROBING:
            target_summary = f"ip={public_ip_summary}"
        else:
            target_summary = f"{self.dns_provider.dns_name} → {public_ip_summary}"

        self.logger.info(
            "Summary: %s | %s | uptime=%s",
            readiness_label,
            target_summary,
            self.uptime,
        )