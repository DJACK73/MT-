#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
docker compose run --rm --no-deps -v "$PWD/tests:/app/tests:ro" -v "$PWD/docs:/app/docs:ro" \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python mt -m unittest discover -s /app/tests "$@"
