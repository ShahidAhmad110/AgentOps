# AgentOps PowerShell Startup Script
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting AgentOps (Database, Backend, Worker, Frontend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Set-Location -Path $PSScriptRoot
python run_project.py
