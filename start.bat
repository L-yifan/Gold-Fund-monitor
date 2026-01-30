@echo off
echo ================================================
echo   Gold Price Monitor - Au99.99
echo   Data Source: Shanghai Gold Exchange
echo ================================================
echo.

call D:\anaconda3\Scripts\activate.bat
call conda activate yolotrain

echo Checking dependencies...
pip install flask requests -q

echo.
echo Starting server...
echo Press Ctrl+C to stop
echo ================================================

start "" cmd /c "timeout /t 2 >nul && start http://localhost:5000"

python -u "D:\programdata\code\test\gold-monitor\app.py"
pause
