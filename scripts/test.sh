#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
docker compose --profile web run --rm --no-deps -v "$PWD/app:/app/app:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/docs:/app/docs:ro" \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python web -m unittest discover -s /app/tests "$@"
