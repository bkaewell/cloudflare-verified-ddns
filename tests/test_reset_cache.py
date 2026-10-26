import json
import subprocess
from pathlib import Path


def test_reset_cache_script_replaces_ip_and_uptime_state(tmp_path):
    cloudflare_ip_file = tmp_path / "cloudflare_ip.json"
    uptime_file = tmp_path / "uptime.json"
    cloudflare_ip_file.write_text('{"last_ip": "203.0.113.1"}')
    uptime_file.write_text('{"total": 4423, "up": 4096}')

    script = Path(__file__).parents[1] / "reset_cache.sh"
    subprocess.run([script, tmp_path], check=True)

    assert json.loads(cloudflare_ip_file.read_text()) == {
        "last_ip": None,
        "observed_at": None,
    }
    assert json.loads(uptime_file.read_text()) == {
        "total": 0,
        "up": 0,
        "last_update": 0.0,
    }
