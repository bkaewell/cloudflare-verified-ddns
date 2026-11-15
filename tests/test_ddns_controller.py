import pytest

from app.ddns_controller import DDNSController, DNSReconcileResult
from app.readiness import ReadinessController, ReadinessState
from app.utils import DoHLookupResult, IPResolutionResult, ReachabilityResult


class FakeCacheResult:
    def __init__(self, hit, age_s=None, ip=None):
        self.hit = hit
        self.age_s = age_s
        self.ip = ip
        self.elapsed_ms = 0.1


class FakeCache:
    def __init__(self, lookup_result):
        self.lookup_result = lookup_result
        self.stored_ips = []

    def load_cloudflare_ip(self):
        return self.lookup_result

    def store_cloudflare_ip(self, ip):
        self.stored_ips.append(ip)

    def load_uptime(self):
        class Uptime:
            total = 0
            up = 0

        return Uptime()

    def store_uptime(self, uptime):
        return None


class FakeProvider:
    dns_name = "vpn.example.com"
    ttl = 60

    def __init__(self):
        self.update_calls = []

    def update_dns(self, new_ip):
        self.update_calls.append(new_ip)
        return {"content": new_ip}, 12.0


class FailingProvider(FakeProvider):
    def update_dns(self, new_ip):
        self.update_calls.append(new_ip)
        raise RuntimeError("boom")


def _controller(cache, provider):
    return DDNSController(
        router_ip="192.168.0.1",
        max_cache_age_s=3600,
        readiness=ReadinessController(),
        dns_provider=provider,
        cache=cache,
    )


def _reachable():
    return ReachabilityResult(success=True, elapsed_ms=1)


def _public_ip(ip=None):
    return IPResolutionResult(
        ip=ip,
        elapsed_ms=1,
        attempts=1,
        max_attempts=1,
        success=ip is not None,
    )


def _doh(ip=None):
    return DoHLookupResult(ip=ip, elapsed_ms=10, success=ip is not None)


def test_reconcile_dns_noop_on_fresh_cache_match(monkeypatch):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    result = controller._reconcile_dns_if_needed("8.8.8.8")

    assert result == DNSReconcileResult.CACHE_TRUSTED
    assert provider.update_calls == []
    assert cache.stored_ips == []


def test_reconcile_dns_updates_when_doh_mismatch(monkeypatch):
    cache = FakeCache(FakeCacheResult(hit=False, age_s=None, ip=None))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr("app.ddns_controller.doh_lookup", lambda host: _doh("4.4.4.4"))

    result = controller._reconcile_dns_if_needed("8.8.8.8")

    assert result == DNSReconcileResult.UPDATE_ACCEPTED
    assert provider.update_calls == ["8.8.8.8"]
    assert cache.stored_ips == ["8.8.8.8"]


def test_reconcile_dns_verifies_expired_cache_with_doh(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=3601, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr(
        "app.ddns_controller.doh_lookup",
        lambda host: _doh("8.8.8.8"),
    )

    with caplog.at_level("DEBUG", logger="ddns"):
        result = controller._reconcile_dns_if_needed("8.8.8.8")

    assert result == DNSReconcileResult.DNS_VERIFIED
    assert provider.update_calls == []
    assert cache.stored_ips == ["8.8.8.8"]
    assert "DNS cache bypassed | reason=stale" in caplog.text
    assert "DNS verified" in caplog.text


def test_reconcile_dns_prioritizes_ip_change_over_stale_cache(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=3601, ip="4.4.4.4"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr("app.ddns_controller.doh_lookup", lambda host: _doh("4.4.4.4"))

    with caplog.at_level("DEBUG", logger="ddns"):
        result = controller._reconcile_dns_if_needed("8.8.8.8")

    assert result == DNSReconcileResult.UPDATE_ACCEPTED
    assert "DNS cache bypassed | reason=ip-changed" in caplog.text
    assert provider.update_calls == ["8.8.8.8"]


def test_reconcile_dns_info_summary_when_dns_update_happens(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=20, ip="4.4.4.4"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr("app.ddns_controller.doh_lookup", lambda host: _doh("4.4.4.4"))

    with caplog.at_level("INFO", logger="ddns"):
        result = controller._reconcile_dns_if_needed("8.8.8.8")

    assert result == DNSReconcileResult.UPDATE_ACCEPTED
    assert provider.update_calls == ["8.8.8.8"]
    assert cache.stored_ips == ["8.8.8.8"]
    assert (
        "🌐 DNS update accepted | host=vpn.example.com ip=4.4.4.4→8.8.8.8"
        in caplog.text
    )


def test_reconcile_dns_defers_update_when_doh_fails(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=False, age_s=None, ip=None))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr(
        "app.ddns_controller.doh_lookup",
        lambda host: _doh(),
    )

    with caplog.at_level("WARNING", logger="ddns"):
        result = controller._reconcile_dns_if_needed("8.8.8.8")

    assert result == DNSReconcileResult.CHECK_DEFERRED
    assert provider.update_calls == []
    assert cache.stored_ips == []
    assert "DNS check unavailable; update deferred" in caplog.text


def test_reconcile_dns_propagates_provider_failure(monkeypatch):
    cache = FakeCache(FakeCacheResult(hit=False, age_s=None, ip=None))
    provider = FailingProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr(
        "app.ddns_controller.doh_lookup",
        lambda host: _doh("4.4.4.4"),
    )

    with pytest.raises(RuntimeError, match="boom"):
        controller._reconcile_dns_if_needed("8.8.8.8")

    assert cache.stored_ips == []


def test_uptime_excludes_warmup_and_counts_ready_as_up():
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    controller._tick_uptime(ReadinessState.INIT)
    controller._tick_uptime(ReadinessState.PROBING)
    controller._tick_uptime(ReadinessState.READY)
    controller._tick_uptime(ReadinessState.NOT_READY)

    assert controller.uptime.total == 2
    assert controller.uptime.up == 1


@pytest.mark.parametrize(
    ("dns_result", "status"),
    [
        (DNSReconcileResult.CACHE_TRUSTED, "DNS Ready ✓"),
        (DNSReconcileResult.DNS_VERIFIED, "Verified DNS ✓"),
        (DNSReconcileResult.UPDATE_ACCEPTED, "DNS Update Pending"),
        (DNSReconcileResult.CHECK_DEFERRED, "DNS Check Deferred"),
    ],
)
def test_summary_reports_dns_outcome(dns_result, status, caplog):
    controller = _controller(
        FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8")),
        FakeProvider(),
    )

    with caplog.at_level("INFO", logger="ddns"):
        controller._log_summary(ReadinessState.READY, "8.8.8.8", dns_result)

    assert f"Summary: {status} | vpn.example.com → 8.8.8.8" in caplog.text


def test_run_cycle_reprobes_when_ready_public_ip_changes(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)
    controller.readiness.state = ReadinessState.READY
    controller.last_public_ip = "8.8.8.8"
    controller.promotion_votes = DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED

    monkeypatch.setattr(
        "app.ddns_controller.ping_host",
        lambda host: _reachable(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.verify_wan_reachability",
        lambda host, port: _reachable(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.get_ip",
        lambda: _public_ip("9.9.9.9"),
    )

    with caplog.at_level("WARNING", logger="ddns"):
        controller.run_cycle()

    assert controller.readiness.state == ReadinessState.PROBING
    assert controller.last_public_ip == "9.9.9.9"
    assert controller.promotion_votes == 1
    assert provider.update_calls == []
    assert cache.stored_ips == []
    assert (
        "Public IP changed; stability verification restarted | 8.8.8.8→9.9.9.9"
        in caplog.text
    )


def test_run_cycle_reaches_ready_after_two_matching_observations(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    controller = _controller(cache, FakeProvider())

    monkeypatch.setattr(
        "app.ddns_controller.ping_host",
        lambda host: _reachable(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.verify_wan_reachability",
        lambda host, port: _reachable(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.get_ip",
        lambda: _public_ip("8.8.8.8"),
    )

    with caplog.at_level("INFO", logger="ddns"):
        controller.run_cycle()
        controller.run_cycle()

    assert controller.readiness.state == ReadinessState.READY
    assert controller.promotion_votes == 2
    assert controller.uptime.total == 1
    assert controller.uptime.up == 1
    assert "Summary: VERIFYING | public_ip=8.8.8.8 stability=1/2" in caplog.text
    assert "Summary: DNS Ready ✓ | vpn.example.com → 8.8.8.8" in caplog.text


def test_run_cycle_reprobes_when_public_ip_is_unavailable(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    controller = _controller(cache, FakeProvider())
    controller.readiness.state = ReadinessState.READY
    controller.last_public_ip = "8.8.8.8"
    controller.promotion_votes = DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED

    monkeypatch.setattr(
        "app.ddns_controller.ping_host",
        lambda host: _reachable(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.verify_wan_reachability",
        lambda host, port: _reachable(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.get_ip",
        lambda: _public_ip(),
    )

    with caplog.at_level("INFO", logger="ddns"):
        controller.run_cycle()

    assert controller.readiness.state == ReadinessState.PROBING
    assert controller.promotion_votes == 0
    assert "Public IP unavailable" in caplog.text
    assert "Summary: VERIFYING | public_ip=unknown stability=0/2" in caplog.text
