@echo off
title AutoTube AI - Autonomous Studio Launcher
cd /d "%~dp0"

echo ========================================================
echo            AutoTube AI - Studio Launcher
echo ========================================================
echo.

set PYTHONPATH=.

echo [1/3] Starting Streamlit Studio on localhost:8501...
start "" ".\.venv\Scripts\python.exe" -m streamlit run app/dashboard.py --server.port=8501 --server.headless=true --server.address=0.0.0.0 --browser.gatherUsageStats=false

timeout /t 3 /nobreak >nul

echo [2/3] Starting Cloudflare Public Subdomain Tunnel...
if exist logs\tunnel.log del /f /q logs\tunnel.log
start "" cloudflared tunnel --url http://127.0.0.1:8501 --logfile logs\tunnel.log

echo [3/3] Waiting for live public URL...
timeout /t 6 /nobreak >nul

powershell -Command "$m = Select-String -Path logs\tunnel.log -Pattern 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1; if ($m) { $url = $m.Matches[0].Value; Write-Host ''; Write-Host '========================================================' -ForegroundColor Green; Write-Host ('  LIVE PUBLIC LINK: ' + $url) -ForegroundColor Yellow; Write-Host '========================================================' -ForegroundColor Green; Start-Process $url; } else { Start-Process 'http://localhost:8501'; }"

echo.
echo ========================================================
echo   AutoTube AI is running!
echo   Local Address: http://localhost:8501
echo ========================================================
echo.
pause
