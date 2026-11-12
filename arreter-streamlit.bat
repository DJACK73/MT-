@echo off
wsl -d Ubuntu -- bash -lc "cd ~/MT && docker compose --profile dashboard stop dashboard"
echo Dashboard arrete.
pause
