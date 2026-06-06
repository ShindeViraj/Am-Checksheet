@echo off
echo Starting TPM Checkpoint Reporting System (Python)...
echo ====================================================
echo Make sure you have configured your .env file and run database_setup.sql
echo Access the system at: http://localhost:8000
echo Press Ctrl+C to stop the server.
echo.

cd /d "%~dp0"
python app.py
