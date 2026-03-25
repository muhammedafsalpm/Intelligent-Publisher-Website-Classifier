@echo off
REM setup.bat - For Windows
echo Setting up Publisher Classifier...

REM Create directories
mkdir chroma_db 2>nul
mkdir data 2>nul
mkdir app\policies 2>nul

REM Install playwright browsers
echo Installing Playwright browsers...
playwright install chromium

REM Create .env if not exists
if not exist .env (
    copy .env.example .env
    echo Created .env file. Please edit it with your configuration.
)

echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env file with your configuration
echo 2. Run: python test_setup.py
echo 3. Run: uvicorn app.main:app --reload
