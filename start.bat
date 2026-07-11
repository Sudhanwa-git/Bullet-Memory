@echo off
setlocal
echo Starting Backend API (Localhost Development)...
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
