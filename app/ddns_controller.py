# ─── Standard library imports ───
from enum import Enum, auto
from typing import Optional

# ─── Project imports ───
from .logger import get_logger
from .cache import PersistentCache
from .cloudflare import CloudflareDNSProvider
from .readiness import ReadinessController, ReadinessState
from .utils import ping_host, verify_wan_reachability, get_ip, doh_lookup


class DNSReconcileResult(Enum):
    CACHE_TRUSTED = auto()
    DNS_VERIFIED = auto()
    UPDATE_ACCEPTED = auto()
    CHECK_DEFERRED = auto()


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
    • Fail closed on uncertainty
    """

    # ─── Class Constants ───
    # consecutive stable IPs required for READY
    PROMOTION_CONFIRMATIONS_REQUIRED: int = 2

    def __init__(
        self,
        *,
        router_ip: str,
        max_cache_age_s: int,
        readiness: ReadinessController,
        dns_provider: CloudflareDNSProvider,
        cache: PersistentCache,
    ):
        """
        Initialize the DDNS control loop.

        • Readiness FSM is the single source of truth
            • Startup assumes nothing about network health
        """

        # ─── Core Control Plane (Single Source of Truth) ───
        self.readiness = readiness

        # ─── External Actuators ───
        self.dns_provider = dns_provider

        # ─── Environment & Topology ───
        self.router_ip = router_ip

        # ─── Policy & Control Parameters ───
        self.max_cache_age_s = max_cache_age_s

        # ─── Promotion / Stability Tracking (Probation Logic) ───
        self.last_public_ip: Optional[str] = None
        self.promotion_votes: int = 0  # consecutive confirmations

        # ─── Metrics & Long-Lived Counters ───
        self.cache = cache
        self.uptime = cache.load_uptime()
        self.logger = get_logger("ddns")

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
            self.promotion_votes = min(
                self.promotion_votes + 1,
                DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED,
            )
        else:
            self.promotion_votes = 1
            self.last_public_ip = public_ip

        return self.promotion_votes >= DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED

    def _reconcile_dns_if_needed(self, public_ip: str) -> DNSReconcileResult:
        """
        Reconcile Cloudflare DNS with the current public IP.

        Trust a fresh matching cache, otherwise check public DNS through
        Cloudflare DoH and update Cloudflare only when that check confirms
        drift from the stable public IP.
        """
        cache = self.cache.load_cloudflare_ip()
        cache_is_fresh = (
            cache.hit
            and cache.age_s is not None
            and cache.age_s <= self.max_cache_age_s
        )

        if cache_is_fresh and cache.ip == public_ip:
            self.logger.debug(
                "DNS trusted | source=cache ip=%s age=%.0fs",
                public_ip,
                cache.age_s,
            )
            return DNSReconcileResult.CACHE_TRUSTED

        if not cache.hit:
            cache_reason = "missing"
        elif cache.ip != public_ip:
            cache_reason = "ip-changed"
        else:
            cache_reason = "stale"

        self.logger.debug(
            "DNS cache bypassed | reason=%s cached_ip=%s desired_ip=%s age=%s",
            cache_reason,
            cache.ip or "none",
            public_ip,
            f"{cache.age_s:.0f}s" if cache.age_s is not None else "n/a",
        )

        doh = doh_lookup(self.dns_provider.dns_name)

        if not doh.success:
            self.logger.warning(
                "DNS check unavailable; update deferred | host=%s",
                self.dns_provider.dns_name,
            )
            return DNSReconcileResult.CHECK_DEFERRED

        if doh.ip == public_ip:
            self.cache.store_cloudflare_ip(public_ip)
            self.logger.debug(
                "DNS verified | host=%s ip=%s source=Cloudflare-DoH rtt=%.0fms",
                self.dns_provider.dns_name,
                public_ip,
                doh.elapsed_ms,
            )
            return DNSReconcileResult.DNS_VERIFIED

        _, elapsed_ms = self.dns_provider.update_dns(public_ip)
        self.cache.store_cloudflare_ip(public_ip)

        self.logger.info(
            "🌐 DNS update accepted | host=%s ip=%s→%s rtt=%.0fms",
            self.dns_provider.dns_name,
            doh.ip,
            public_ip,
            elapsed_ms,
        )
        return DNSReconcileResult.UPDATE_ACCEPTED

    def _tick_uptime(self, readiness: ReadinessState) -> None:
        """
        Advance uptime counters for the current loop iteration.

        Only READY and NOT_READY are eligible uptime observations. INIT and
        PROBING are stabilization states and do not affect the counters.
        """
        if readiness in (ReadinessState.READY, ReadinessState.NOT_READY):
            self.uptime.total += 1

            if readiness == ReadinessState.READY:
                self.uptime.up += 1

        self.cache.store_uptime(self.uptime)

    def _log_summary(
        self,
        readiness: ReadinessState,
        public_ip: Optional[str],
        dns_result: Optional[DNSReconcileResult] = None,
    ) -> None:
        """Emit one stable, user-facing status line per control-loop cycle."""
        ip = public_ip or "unknown"

        if readiness == ReadinessState.PROBING:
            status = "VERIFYING"
            target = (
                f"public_ip={ip} "
                f"stability={self.promotion_votes}/"
                f"{DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED}"
            )
        elif readiness == ReadinessState.READY:
            status = {
                DNSReconcileResult.DNS_VERIFIED: "Verified DNS ✓",
                DNSReconcileResult.UPDATE_ACCEPTED: "DNS Update Pending",
                DNSReconcileResult.CHECK_DEFERRED: "DNS Check Deferred",
            }.get(dns_result, "DNS Ready ✓")
            target = f"{self.dns_provider.dns_name} → {ip}"
        elif readiness == ReadinessState.NOT_READY:
            status = "OFFLINE"
            target = f"{self.dns_provider.dns_name} → unknown"
        else:
            status = "STARTING"
            target = f"public_ip={ip}"

        self.logger.info(
            "Summary: %s | %s | uptime=%s",
            status,
            target,
            self.uptime,
        )

    def run_cycle(self) -> None:
        """
        Execute one autonomous control-loop cycle.

        Phases:
        1. Observe raw network signals
        2. Assess readiness (FSM)
        3. Perform READY-only side effects (DDNS)
        4. Emit cycle summary and diagnostics
        """

        # Observe network signals.
        lan = ping_host(self.router_ip)
        if not lan.success:
            self.logger.debug(
                "LAN probe failed | router=%s rtt=%.0fms",
                self.router_ip,
                lan.elapsed_ms,
            )

        wan = verify_wan_reachability(host="1.1.1.1", port=443)
        if not wan.success:
            if self.readiness.state == ReadinessState.NOT_READY:
                self.logger.debug(
                    "WAN still unavailable | destination=1.1.1.1:443 rtt=%.0fms",
                    wan.elapsed_ms,
                )
            else:
                self.logger.error(
                    "WAN unavailable | destination=1.1.1.1:443 rtt=%.0fms",
                    wan.elapsed_ms,
                )

        public = get_ip() if wan.success else None
        public_ip = public.ip if public and public.success else None

        if public and not public.success:
            self.logger.warning(
                "Public IP unavailable | rtt=%.0fms",
                public.elapsed_ms,
            )

        # Every public-IP observation uses the same stability tracker.
        previous_ip = self.last_public_ip
        previous_state = self.readiness.state
        ip_stable = self._record_ip_observation(public_ip)
        ip_changed = (
            previous_ip is not None
            and public_ip is not None
            and public_ip != previous_ip
        )

        # A READY system re-enters verification when its public IP changes or
        # cannot be observed despite a healthy WAN path.
        if (
            previous_state == ReadinessState.READY
            and wan.success
            and (ip_changed or public_ip is None)
        ):
            self.readiness.reprobe()

            if ip_changed:
                self.logger.warning(
                    "Public IP changed; stability verification restarted | %s→%s",
                    previous_ip,
                    public_ip,
                )

        self.readiness.advance(
            wan_path_ok=wan.success,
            allow_promotion=ip_stable,
        )
        current = self.readiness.state

        # Cloudflare mutation is permitted only after IP stability earns READY.
        dns_result = None
        if current == ReadinessState.READY and public_ip:
            dns_result = self._reconcile_dns_if_needed(public_ip)

        self._tick_uptime(current)
        self._log_summary(current, public_ip, dns_result)
