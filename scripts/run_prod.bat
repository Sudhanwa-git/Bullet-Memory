@echo off
setlocal
echo Starting Backend API (Production Mode)...
cd ..
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --workers 4
