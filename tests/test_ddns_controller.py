from app.ddns_controller import DDNSController
from app.readiness import ReadinessController, ReadinessState


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


def test_reconcile_dns_noop_on_fresh_cache_match(monkeypatch):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    controller._reconcile_dns_if_needed("8.8.8.8")

    assert provider.update_calls == []
    assert cache.stored_ips == []


def test_reconcile_dns_updates_when_doh_mismatch(monkeypatch):
    cache = FakeCache(FakeCacheResult(hit=False, age_s=None, ip=None))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    values = iter([
        type("DohResult", (), {"success": True, "ip": "4.4.4.4", "elapsed_ms": 10})(),
    ])
    monkeypatch.setattr("app.ddns_controller.doh_lookup", lambda host: next(values))

    controller._reconcile_dns_if_needed("8.8.8.8")

    assert provider.update_calls == ["8.8.8.8"]
    assert cache.stored_ips == ["8.8.8.8"]


def test_reconcile_dns_warns_when_cache_expired_and_refreshes_from_doh(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=3601, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr(
        "app.ddns_controller.doh_lookup",
        lambda host: type("DohResult", (), {"success": True, "ip": "8.8.8.8", "elapsed_ms": 10})(),
    )

    with caplog.at_level("DEBUG", logger="ddns"):
        controller._reconcile_dns_if_needed("8.8.8.8")

    assert provider.update_calls == []
    assert cache.stored_ips == ["8.8.8.8"]
    assert "DDNS cache IP expired; refreshing to 8.8.8.8" in caplog.text
    assert "status=doh-verified" in caplog.text


def test_reconcile_dns_info_summary_when_dns_update_happens(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=20, ip="4.4.4.4"))
    provider = FakeProvider()
    controller = _controller(cache, provider)

    values = iter([
        type("DohResult", (), {"success": True, "ip": "4.4.4.4", "elapsed_ms": 10})(),
    ])
    monkeypatch.setattr("app.ddns_controller.doh_lookup", lambda host: next(values))

    with caplog.at_level("INFO", logger="ddns"):
        controller._reconcile_dns_if_needed("8.8.8.8")

    assert provider.update_calls == ["8.8.8.8"]
    assert cache.stored_ips == ["8.8.8.8"]
    assert "🌐 DNS updated: 4.4.4.4 → 8.8.8.8 | host=vpn.example.com" in caplog.text


def test_reconcile_dns_logs_error_when_update_fails(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=False, age_s=None, ip=None))
    provider = FailingProvider()
    controller = _controller(cache, provider)

    monkeypatch.setattr(
        "app.ddns_controller.doh_lookup",
        lambda host: type("DohResult", (), {"success": False, "ip": None, "elapsed_ms": 10})(),
    )

    with caplog.at_level("ERROR", logger="ddns"):
        controller._reconcile_dns_if_needed("8.8.8.8")

    assert provider.update_calls == ["8.8.8.8"]
    assert cache.stored_ips == []
    assert "DDNS update failed" in caplog.text


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


def test_run_cycle_reprobes_when_ready_public_ip_changes(monkeypatch, caplog):
    cache = FakeCache(FakeCacheResult(hit=True, age_s=10, ip="8.8.8.8"))
    provider = FakeProvider()
    controller = _controller(cache, provider)
    controller.readiness.state = ReadinessState.READY
    controller.last_public_ip = "8.8.8.8"
    controller.promotion_votes = DDNSController.PROMOTION_CONFIRMATIONS_REQUIRED
    controller.ready_confirmation_announced = True

    monkeypatch.setattr(
        "app.ddns_controller.ping_host",
        lambda host: type("ProbeResult", (), {"success": True, "elapsed_ms": 1})(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.verify_wan_reachability",
        lambda host, port: type("ProbeResult", (), {"success": True, "elapsed_ms": 1})(),
    )
    monkeypatch.setattr(
        "app.ddns_controller.get_ip",
        lambda: type("PublicIpResult", (), {"success": True, "ip": "9.9.9.9", "elapsed_ms": 1})(),
    )

    with caplog.at_level("WARNING", logger="ddns"):
        controller.run_cycle()

    assert controller.readiness.state == ReadinessState.PROBING
    assert controller.last_public_ip == "9.9.9.9"
    assert controller.promotion_votes == 1
    assert provider.update_calls == []
    assert cache.stored_ips == []
    assert "WAN IP changed; re-checking stability 8.8.8.8 → 9.9.9.9" in caplog.text
