#!/usr/bin/env bash
set -eu

CACHE_DIR="${1:-${HOME}/.cache/cloudflare_verified_ddns}"

mkdir -p "${CACHE_DIR}"

cat > "${CACHE_DIR}/cloudflare_ip.json" <<'EOF'
{
  "last_ip": null,
  "observed_at": null
}
EOF

cat > "${CACHE_DIR}/uptime.json" <<'EOF'
{
  "total": 0,
  "up": 0,
  "last_update": 0.0
}
EOF

echo "DDNS cache reset: ${CACHE_DIR}"
