@echo off
echo ============================================
echo   Sagarwave AI Agent - Setup & Launch
echo ============================================
echo.

:: Create .env if not exists
if not exist .env (
    copy .env.example .env
    echo [FIRST TIME] Created .env file - Edit it to add your GROQ_API_KEY
    echo Get a free key at: https://console.groq.com
    echo.
)

:: Check if all deps are installed
echo [CHECK] Dependencies...
python -c "import streamlit, httpx, edge_tts, moviepy, faster_whisper, insightface" 2>nul
if %errorlevel% neq 0 (
    echo [INSTALL] Installing requirements...
    pip install -r requirements.txt
) else (
    echo [OK] All dependencies found
)

:: Launch Streamlit app
echo.
echo [LAUNCH] Starting Sagarwave AI Agent...
echo.
streamlit run app.py
pause
