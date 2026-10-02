@echo off
title AgentOps
echo ========================================================
echo Starting AgentOps (Database, Backend, Worker, Frontend)
echo ========================================================
uv run python run_project.py
pause
