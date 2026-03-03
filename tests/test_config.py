import importlib

from app import config as config_module


def test_cloudflare_config_reads_environment(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token-123")
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", "zone-abc")
    monkeypatch.setenv("CLOUDFLARE_DNS_NAME", "vpn.example.com")
    monkeypatch.setenv("CLOUDFLARE_DNS_RECORD_ID", "record-xyz")

    cfg = config_module.CloudflareConfig()

    assert cfg.API_TOKEN == "token-123"
    assert cfg.ZONE_ID == "zone-abc"
    assert cfg.DNS_NAME == "vpn.example.com"
    assert cfg.DNS_RECORD_ID == "record-xyz"


def test_top_level_config_reads_env_at_module_import(monkeypatch):
    monkeypatch.setenv("CYCLE_INTERVAL_S", "120")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    reloaded = importlib.reload(config_module)
    cfg = reloaded.Config()

    assert cfg.CYCLE_INTERVAL_S == 120
    assert cfg.LOG_LEVEL == "DEBUG"
