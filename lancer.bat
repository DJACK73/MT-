@echo off
wsl -d Ubuntu --cd /home/x1_yoga2045/MT -- bash scripts/dashboard_up.sh
if errorlevel 1 (
  echo Echec : voir le message ci-dessus.
  pause
  exit /b 1
)
start "" explorer "\\wsl.localhost\Ubuntu\home\x1_yoga2045\MT\inbox"
start "" "http://127.0.0.1:8502"
