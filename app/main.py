# ─── Standard library imports ───
import sys
import time
import logging

# ─── Project imports ───
from app.config import config
from app.cache import PersistentCache
from app.ddns_controller import DDNSController
from app.logger import get_logger, setup_logging
from app.cloudflare import CloudflareDNSProvider
from app.scheduling_policy import SchedulingPolicy
from app.readiness import ReadinessController


def run_supervisor_loop(
        scheduler: SchedulingPolicy,
        ddns: DDNSController
    ) -> None:
    """
    Top-level supervisor loop.

    Responsibilities:
    • Run the DDNS control cycle
    • Capture and log unhandled failures
    • Delegate timing decisions to the scheduler
    • Maintain steady cadence for long-running operation

    Notes:
    • This loop never exits
    • Scheduling is adaptive to avoid API abuse and tight loops
    """

    logger = get_logger("run_supervisor_loop")
    
    # Intentional infinite loop - lifecycle managed externally by Docker
    while True:

        start = time.monotonic()

        try:
            ddns.run_cycle()
        except Exception as e:
            logger.exception(f"Unhandled exception during run_control_cycle: {e}")

        # Adaptive Polling Engine (APE): compute next poll interval
        elapsed = time.monotonic() - start
        decision = scheduler.next_schedule(
            elapsed=elapsed, 
            readiness=ddns.readiness.state
        )
        logger.debug(
            "Readiness=%s | cadence=%s | elapsed=%.0fms | sleep=%.0fs | jitter=%.0fs",
            ddns.readiness.state.name,
            decision.poll_speed,
            elapsed * 1000,
            decision.sleep_for,
            decision.jitter,
        )

        time.sleep(decision.sleep_for)

def main() -> None:
    """
    Application entry point and composition root.

    • Configure logging and runtime settings
    • Construct external actuators, policies, and controllers
    • Wire dependencies into the DDNS control loop
    • Transfer control to the supervisor loop

    No system state is managed here; this function is responsible only
    for object composition and process startup.
    """

    setup_logging(level=getattr(logging, config.LOG_LEVEL))
    logger = get_logger("main")

    logger.info("🚀 Starting Cloudflare Verified DDNS Application")
    logger.debug(f"Python version: {sys.version}")

    # def validate_config() -> None:
    #     if not config.Cloudflare.DNS_NAME:
    #         raise RuntimeError("CLOUDFLARE_DNS_NAME is required")

    #     if config.MAX_CACHE_AGE_S < config.CYCLE_INTERVAL_S * config.SLOW_POLL_SCALAR:
    #         raise RuntimeError("Cache expires before reuse")

    # ─── External Actuator: DNS Provider ───
    dns_provider = CloudflareDNSProvider(
        api_token=config.Cloudflare.API_TOKEN,
        zone_id=config.Cloudflare.ZONE_ID,
        dns_name=config.Cloudflare.DNS_NAME,
        dns_record_id=config.Cloudflare.DNS_RECORD_ID,
        ttl=config.Cloudflare.MIN_TTL_S,
        proxied=False,
        http_timeout_s=config.API_TIMEOUT_S,
    )

    # ─── Policies (stateless) ───
    scheduler = SchedulingPolicy(
        cycle_interval_s=config.CYCLE_INTERVAL_S,
        polling_jitter_s=config.POLLING_JITTER_S,
        fast_poll_scalar=config.FAST_POLL_SCALAR,
        slow_poll_scalar=config.SLOW_POLL_SCALAR,
    )

    # ─── Controllers (stateful) ───
    readiness = ReadinessController()

    cache = PersistentCache()

    ddns = DDNSController(
        router_ip=config.Hardware.ROUTER_IP,
        max_cache_age_s=config.MAX_CACHE_AGE_S,
        readiness=readiness,
        dns_provider=dns_provider,
        cache=cache,
    )

    logger.info("Entering supervisor loop...")
    run_supervisor_loop(scheduler, ddns)

if __name__ == "__main__":
    main()
