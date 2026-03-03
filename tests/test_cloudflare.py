import pytest
import requests

from app.cloudflare import CloudflareDNSProvider


class DummyResponse:
    def __init__(self, payload=None, status_error=None, json_error=None):
        self._payload = payload or {}
        self._status_error = status_error
        self._json_error = json_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


def _mock_validate_ok(monkeypatch):
    monkeypatch.setattr(
        "app.cloudflare.requests.get",
        lambda *args, **kwargs: DummyResponse(
            payload={"success": True, "result": {"name": "vpn.example.com"}}
        ),
    )


def _provider(monkeypatch):
    _mock_validate_ok(monkeypatch)
    return CloudflareDNSProvider(
        api_token="token",
        zone_id="zone-1",
        dns_name="vpn.example.com",
        dns_record_id="record-1",
        ttl=60,
    )


def test_validate_config_raises_on_name_mismatch(monkeypatch):
    monkeypatch.setattr(
        "app.cloudflare.requests.get",
        lambda *args, **kwargs: DummyResponse(
            payload={"success": True, "result": {"name": "wrong.example.com"}}
        ),
    )

    with pytest.raises(ValueError, match="DNS record mismatch"):
        CloudflareDNSProvider(
            api_token="token",
            zone_id="zone-1",
            dns_name="vpn.example.com",
            dns_record_id="record-1",
            ttl=60,
        )


def test_update_dns_success(monkeypatch):
    provider = _provider(monkeypatch)

    monkeypatch.setattr(
        "app.cloudflare.requests.put",
        lambda *args, **kwargs: DummyResponse(
            payload={"result": {"id": "record-1", "content": "1.2.3.4"}}
        ),
    )

    result, elapsed_ms = provider.update_dns("1.2.3.4")

    assert result["content"] == "1.2.3.4"
    assert elapsed_ms >= 0


def test_update_dns_wraps_request_exceptions(monkeypatch):
    provider = _provider(monkeypatch)

    def _raise(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr("app.cloudflare.requests.put", _raise)

    with pytest.raises(RuntimeError, match="Cloudflare PUT failed"):
        provider.update_dns("1.2.3.4")


def test_get_dns_record_returns_first_result(monkeypatch):
    provider = _provider(monkeypatch)

    monkeypatch.setattr(
        "app.cloudflare.requests.get",
        lambda *args, **kwargs: DummyResponse(
            payload={"result": [{"id": "record-1", "content": "1.2.3.4"}]}
        ),
    )

    record = provider.get_dns_record()

    assert record["id"] == "record-1"


def test_get_dns_record_raises_on_empty_result(monkeypatch):
    provider = _provider(monkeypatch)

    monkeypatch.setattr(
        "app.cloudflare.requests.get",
        lambda *args, **kwargs: DummyResponse(payload={"result": []}),
    )

    with pytest.raises(RuntimeError, match="no DNS record"):
        provider.get_dns_record()
