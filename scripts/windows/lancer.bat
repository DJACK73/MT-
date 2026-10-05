@echo off
wsl -d Ubuntu -- bash -lc "docker info >/dev/null 2>&1"
if errorlevel 1 (
  echo Docker Desktop n'est pas pret. Lance-le, attends qu'il demarre, puis relance.
  pause
  exit /b 1
)
wsl -d Ubuntu -- bash -lc "cd ~/MT && docker compose --profile dashboard up -d dashboard && for i in $(seq 1 30); do curl -sf -o /dev/null http://127.0.0.1:8502/_stcore/health && exit 0; sleep 1; done; exit 1"
if errorlevel 1 (
  echo Le dashboard ne repond pas apres 30 s.
  pause
  exit /b 1
)
start "" explorer "\\wsl.localhost\Ubuntu\home\x1_yoga2045\MT\inbox"
start "" "http://127.0.0.1:8502"
