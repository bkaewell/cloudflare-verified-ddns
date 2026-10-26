# Operator quick start: Mac development to WireGuard end-to-end test

Use this runbook when returning to the project after time away. It separates
three systems that are easy to confuse:

1. **MacBook checkout** — edit and test the DDNS application.
2. **Mini PC deployment** — run and inspect DDNS and WireGuard.
3. **Remote client** — connect from outside the home LAN and prove the whole
   DNS → router → WireGuard path works.

Commands containing `<...>` require a value from your environment. Do not paste
API tokens, WireGuard private keys, or `.env` contents into issues or logs.

## 1. Reorient yourself on the MacBook

Open VS Code's integrated terminal and confirm where you are:

```bash
pwd
git rev-parse --show-toplevel
git status --short --branch
git remote -v
git log --oneline --decorate --graph -10
```

If `git rev-parse` fails, locate or clone the repository:

```bash
cd ~/Documents   # or your preferred source-code directory
git clone https://github.com/bkaewell/cloudflare-verified-ddns.git
cd cloudflare-verified-ddns
code .
```

Before pulling, protect unfinished work. A clean `git status --short` prints
nothing after the branch header.

```bash
git status --short --branch
git stash push -u -m "WIP before sync"   # only if you need to save local work
git switch main
git pull --ff-only
git log -1 --show-signature --format=fuller
```

Use `git stash list` and `git stash pop` later if you created a stash. Prefer
`git pull --ff-only`: it refuses surprising merge commits instead of silently
rewriting your local history.

## 2. Install and verify the local toolchain

This project requires Python 3.13 or newer and uses `uv` to manage Python and
dependencies.

```bash
xcode-select -p
brew --version
uv --version
python3 --version
```

If `uv` is missing:

```bash
brew install uv
```

From the repository root, create/synchronize the project environment and prove
that it works:

```bash
uv python install 3.13
uv sync --dev --frozen
uv run python --version
uv run python -c 'from app.config import config; print(config)'
uv run pytest -q
```

Useful Python commands while developing:

```bash
uv run python -m app.main                # run using exported shell variables
uv run --env-file .env python -m app.main # run using the local .env file
uv run python -m pytest -q               # equivalent test invocation
uv run python -m pytest tests/test_ddns_controller.py -q
uv run python -m pytest -k uptime -vv
```

Stop the long-running application with **Control-C**.

To clear local IP observations and uptime history before a clean startup test,
stop the application and run the repository's reset utility:

```bash
./reset_cache.sh
cat ~/.cache/cloudflare_verified_ddns/cloudflare_ip.json
cat ~/.cache/cloudflare_verified_ddns/uptime.json
```

The utility resets the cached IP fields to `null` and uptime counters to zero.
Pass a directory only when resetting a non-default cache location:

```bash
./reset_cache.sh /tmp/ddns-cache-test
```

## 3. Configure a safe local run

Create `.env` in the repository root. It is ignored by Git, but still protect
it because it contains a Cloudflare credential:

```bash
cat > .env <<'EOF'
CLOUDFLARE_API_TOKEN=replace_me
CLOUDFLARE_ZONE_ID=replace_me
CLOUDFLARE_DNS_NAME=vpn.example.com
CLOUDFLARE_DNS_RECORD_ID=replace_me
ROUTER_IP=192.168.0.1
TZ=America/New_York
CYCLE_INTERVAL_S=60
LOG_LEVEL=DEBUG
LOG_FORMAT=console
EOF
chmod 600 .env
git check-ignore -v .env
```

Use a narrowly scoped Cloudflare token and a test DNS record when possible.
Running this process is **not read-only**: after readiness and stability checks,
it can update the configured record.

Validate the environment without printing secrets:

```bash
uv run --env-file .env python - <<'PY'
from app.config import config

print("dns_name:", config.Cloudflare.DNS_NAME)
print("zone configured:", bool(config.Cloudflare.ZONE_ID))
print("record configured:", bool(config.Cloudflare.DNS_RECORD_ID))
print("token configured:", bool(config.Cloudflare.API_TOKEN))
print("router:", config.Hardware.ROUTER_IP)
PY
```

Run the application locally:

```bash
uv run --env-file .env python -m app.main
```

In a second terminal, independently check public IP and DNS:

```bash
curl -4 --fail --silent https://api.ipify.org; echo
dig +short A vpn.example.com @1.1.1.1
```

The addresses should converge. A newly changed DNS record may require time to
become visible because resolver caches obey TTLs.

## 4. Inspect the mini PC before changing it

Connect over the LAN first; do not use the VPN you are about to restart as your
only administrative path.

```bash
ssh <user>@<mini-pc-lan-ip>
hostname
date
uptime
ip -brief address
```

Find the deployment rather than guessing its directory:

```bash
pwd
find "$HOME" -maxdepth 3 -type d -name cloudflare-verified-ddns 2>/dev/null
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker compose ls
```

If the mini PC has a Git checkout:

```bash
cd <path-to-cloudflare-verified-ddns>
git status --short --branch
git remote -v
git log --oneline --decorate -10
git rev-parse HEAD
git fetch --prune
git status --short --branch
git log --oneline HEAD..origin/main   # commits available remotely
git log --oneline origin/main..HEAD   # local-only commits
```

Only pull after reviewing status and logs:

```bash
git pull --ff-only
```

If production uses the GHCR image, the checkout commit does **not** prove what
is running. Inspect the container and immutable image identity instead:

```bash
docker inspect cloudflare-verified-ddns \
  --format 'image={{.Config.Image}} started={{.State.StartedAt}} id={{.Image}}'
docker image inspect \
  "$(docker inspect cloudflare-verified-ddns --format '{{.Image}}')" \
  --format 'repo_digests={{json .RepoDigests}} created={{.Created}}'
docker logs --tail 100 cloudflare-verified-ddns
docker logs --follow --since 10m cloudflare-verified-ddns
```

Use **Control-C** to stop following logs; it does not stop the container.

To deploy a newer published image deliberately:

```bash
cd <directory-containing-docker-compose.yaml>
docker compose pull app
docker compose up -d app
docker compose ps
docker compose logs --tail 100 app
```

## 5. Start and inspect WireGuard on the mini PC

First identify whether WireGuard is a host service or a container:

```bash
sudo systemctl list-unit-files 'wg-quick@*'
sudo wg show
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -Ei 'wireguard|wg-easy'
```

### Host-managed WireGuard

Replace `wg0` if your interface has another name:

```bash
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0
sudo systemctl status wg-quick@wg0 --no-pager
sudo wg show wg0
sudo journalctl -u wg-quick@wg0 --since '15 minutes ago' --no-pager
```

### Docker Compose / wg-easy

Run these commands from the WireGuard repository or Compose directory (which
may be separate from this DDNS repository):

```bash
docker compose config --services
docker compose up -d
docker compose ps
docker compose logs --tail 100
sudo wg show
```

If the service was given a container name such as `wg-easy`, these are useful:

```bash
docker logs --tail 100 wg-easy
docker inspect wg-easy --format 'image={{.Config.Image}} status={{.State.Status}}'
```

Also verify the router forwards WireGuard's UDP port (commonly UDP 51820) to
the mini PC's stable LAN address. Do not expose a management web UI directly to
the internet.

## 6. Full end-to-end remote test

The test is only meaningful from **outside** the home LAN. On the MacBook,
disable Wi-Fi and use a phone hotspot, or test from another external network.
Keep an independent LAN/console recovery path while changing VPN services.

### Before connecting

```bash
dig +short A vpn.example.com @1.1.1.1
curl -4 --fail --silent https://api.ipify.org; echo
```

The DNS answer should equal the home router's public IPv4 address. If your ISP
uses CGNAT, ordinary inbound port forwarding may not work even when DDNS is
correct.

Activate the imported tunnel in the macOS WireGuard app. If you intentionally
manage the tunnel with the CLI instead, use its configured interface name:

```bash
sudo wg-quick up <client-interface>
sudo wg show
```

Then test the VPN path:

```bash
ping -c 4 <wireguard-server-tunnel-ip>
ssh <user>@<mini-pc-wireguard-ip>
```

If the client is configured as a full tunnel, verify egress too:

```bash
curl -4 --fail --silent https://api.ipify.org; echo
```

On the mini PC, confirm a recent handshake and increasing transfer counters:

```bash
sudo wg show
watch -n 2 sudo wg show
```

A successful end-to-end result has all of these signals:

- `vpn.example.com` resolves to the home public IP.
- The DDNS container is healthy and its logs show stable/verified operation.
- The WireGuard interface/container is running.
- `wg show` reports a recent handshake for the remote client.
- Traffic counters increase while pinging or using SSH through the tunnel.
- The mini PC is reachable by its **WireGuard tunnel IP**, not accidentally by
  a LAN route.

Disconnect when finished:

```bash
sudo wg-quick down <client-interface>
```

Or deactivate the tunnel in the macOS WireGuard app.

## 7. Fast troubleshooting map

| Symptom | Check first |
| --- | --- |
| `uv` command not found | `brew install uv` |
| Imports or packages missing | `uv sync --dev --frozen` |
| DDNS exits during startup | Required `.env` values and Cloudflare token/record permissions |
| DNS differs from public IP | DDNS logs, readiness state, cache age, then `dig ... @1.1.1.1` |
| DNS is correct but no VPN handshake | Router UDP forwarding, host firewall, WireGuard service, endpoint port |
| Handshake works but no LAN/Internet traffic | AllowedIPs, forwarding, NAT, and firewall rules |
| `git pull` refuses | Inspect `git status` and local commits; do not discard work blindly |
| Unsure what production runs | Container image ID/digest, not only the checkout's Git SHA |

## 8. A short repeatable session

Once the environment is familiar again, this is the compact routine:

```bash
# MacBook
cd <path-to-cloudflare-verified-ddns>
git status --short --branch
git pull --ff-only
uv sync --dev --frozen
uv run pytest -q
uv run --env-file .env python -m app.main
```

```bash
# Mini PC, in a separate terminal
ssh <user>@<mini-pc-lan-ip>
docker ps
docker logs --follow --since 10m cloudflare-verified-ddns
sudo wg show
```

Then move the MacBook to an external network, activate its WireGuard tunnel,
and verify DNS, handshake, ping, and SSH in that order.
