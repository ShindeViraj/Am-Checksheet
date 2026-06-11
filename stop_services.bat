@echo off
echo Stopping background TPM Dashboard services...

:: Kill any running Python processes (closes app.py)
taskkill /F /IM python.exe /T >nul 2>&1

:: Kill any running Node processes (closes Node-RED)
taskkill /F /IM node.exe /T >nul 2>&1

echo.
echo All services have been successfully stopped!
pause
