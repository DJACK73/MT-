@echo off
wsl -d Ubuntu -- bash -lc "cd ~/MT && docker compose --profile web stop web"
echo Web arretee.
pause
