@echo off
set OLLAMA_KEEP_ALIVE=30m

echo [Startup] Checking port 11434...
netstat -ano | findstr :11434 >nul 2>&1
if %errorlevel% == 0 (
    echo [Startup] Ollama already running on port 11434.
) else (
    echo [Startup] Starting Ollama server...
    start /B ollama serve
    timeout /t 4 /nobreak > nul
)

echo [Startup] Warming up model...
ollama run phi3.5 "What is the capital of France?" >nul 2>&1

echo [Startup] Starting FastAPI...
uvicorn main:app --host 0.0.0.0 --port 8000 --reload