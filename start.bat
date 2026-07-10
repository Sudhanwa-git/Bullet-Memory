@echo off
setlocal
echo Starting Backend...
start /b cmd /c ".\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"
echo Starting Frontend...
start /b cmd /c ".\.venv\Scripts\streamlit.exe run streamlit_app.py --server.port 8501"
echo Both servers started!
echo Frontend: http://localhost:8501
echo Backend:  http://localhost:8000
