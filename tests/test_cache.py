from app.cache import PersistentCache, Uptime


def test_uptime_string_is_na_until_first_eligible_sample():
    assert str(Uptime()) == "n/a"


def test_cloudflare_cache_write_failure_is_non_fatal(tmp_path, caplog):
    cache = PersistentCache(tmp_path)
    cache.cloudflare_ip_file = tmp_path

    cache.store_cloudflare_ip("203.0.113.10")

    assert "Failed to write Cloudflare IP cache" in caplog.text
