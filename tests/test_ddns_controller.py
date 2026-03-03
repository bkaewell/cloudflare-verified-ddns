from app.ddns_controller import DDNSController
from app.readiness import ReadinessController


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

    class DohResult:
        success = True
        ip = "4.4.4.4"
        elapsed_ms = 10

    monkeypatch.setattr("app.ddns_controller.doh_lookup", lambda host: DohResult())

    controller._reconcile_dns_if_needed("8.8.8.8")

    assert provider.update_calls == ["8.8.8.8"]
    assert cache.stored_ips == ["8.8.8.8"]
