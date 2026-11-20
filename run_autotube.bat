@echo off
title AutoTube AI - Autonomous Studio Launcher
cd /d "%~dp0"

echo ========================================================
echo            AutoTube AI - Studio Launcher
echo ========================================================
echo.

set PYTHONPATH=.

echo [1/2] Starting Streamlit Studio on localhost:8501...
start "" ".\.venv\Scripts\python.exe" -m streamlit run app/dashboard.py --server.port=8501 --server.headless=true --server.address=0.0.0.0 --browser.gatherUsageStats=false

timeout /t 3 /nobreak >nul

echo [2/2] Starting Cloudflare Public Subdomain Tunnel...
start "" cloudflared tunnel --url http://127.0.0.1:8501 --logfile logs\tunnel.log

timeout /t 5 /nobreak >nul

echo.
echo ========================================================
echo   AutoTube AI is now live!
echo.
echo   Local Address:  http://localhost:8501
echo   Tunnel Log:     logs\tunnel.log
echo ========================================================
echo.
pause
