import requests

from app.utils import doh_lookup, get_ip, is_valid_ip


class DummyResponse:
    def __init__(self, text="", json_payload=None, status_error=None):
        self.text = text
        self._json_payload = json_payload or {}
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._json_payload


def test_is_valid_ip_checks_ipv4_addresses():
    assert is_valid_ip("1.2.3.4") is True
    assert is_valid_ip("999.2.3.4") is False


def test_get_ip_uses_first_valid_service(monkeypatch):
    responses = [
        DummyResponse(text="not-an-ip"),
        DummyResponse(text="8.8.8.8"),
    ]

    monkeypatch.setattr("app.utils.requests.get", lambda *args, **kwargs: responses.pop(0))

    result = get_ip()

    assert result.success is True
    assert result.ip == "8.8.8.8"
    assert result.attempts == 2


def test_get_ip_returns_failure_when_all_services_fail(monkeypatch):
    def _raise(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("app.utils.requests.get", _raise)

    result = get_ip()

    assert result.success is False
    assert result.ip is None
    assert result.attempts == result.max_attempts


def test_doh_lookup_success(monkeypatch):
    monkeypatch.setattr(
        "app.utils.requests.get",
        lambda *args, **kwargs: DummyResponse(
            json_payload={"Answer": [{"data": "1.1.1.1"}]}
        ),
    )

    result = doh_lookup("vpn.example.com")

    assert result.success is True
    assert result.ip == "1.1.1.1"


def test_doh_lookup_returns_failure_for_request_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("app.utils.requests.get", _raise)

    result = doh_lookup("vpn.example.com")

    assert result.success is False
    assert result.ip is None
