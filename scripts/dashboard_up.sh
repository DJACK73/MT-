#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile dashboard up -d dashboard
for i in $(seq 1 30); do
  curl -sf -o /dev/null http://127.0.0.1:8502/_stcore/health && exit 0
  sleep 1
done
echo "Dashboard muet apres 30 s" >&2
docker compose --profile dashboard logs --tail 20 dashboard >&2
exit 1
