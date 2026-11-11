#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile dashboard stop dashboard >/dev/null 2>&1 || true
docker compose --profile web up -d web
for i in $(seq 1 30); do
  curl -sf -o /dev/null http://127.0.0.1:8502/api/plans && exit 0
  sleep 1
done
echo "Web muette apres 30 s" >&2
docker compose --profile web logs --tail 20 web >&2
exit 1
