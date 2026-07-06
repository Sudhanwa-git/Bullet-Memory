@echo off
setlocal

if "%~1"=="" (
    echo.
    echo   ERROR: No commit message provided.
    echo   Usage: ship "your commit message"
    echo.
    exit /b 1
)

echo.
echo   ── SHIP ──────────────────────────────────────────
echo.

git add -A
if errorlevel 1 (
    echo.
    echo   ✗ UNSUCCESSFUL
    echo   Reason: git add failed
    echo   ──────────────────────────────────────────────────
    echo.
    exit /b 1
)

git commit -m "%~1"
if errorlevel 1 (
    echo.
    echo   ✗ UNSUCCESSFUL
    echo   Reason: nothing to commit, or commit failed
    echo   ──────────────────────────────────────────────────
    echo.
    exit /b 1
)

git push origin main
if errorlevel 1 (
    echo.
    echo   ✗ UNSUCCESSFUL
    echo   Reason: push failed — check remote and auth
    echo   ──────────────────────────────────────────────────
    echo.
    exit /b 1
)

echo.
echo   ✓ SHIPPED
echo   Committed: "%~1"
echo   ──────────────────────────────────────────────────
echo.
echo   Streamlit Cloud setup:
echo     Main file  →  streamlit_app.py
echo     Secret     →  API_BASE_URL = "http://your-backend"
echo.
echo   Local stack:
echo     docker-compose up --build
echo     UI   →  http://localhost:8501
echo     API  →  http://localhost:8000/docs
echo   ──────────────────────────────────────────────────
echo.