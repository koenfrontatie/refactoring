@echo off
REM Navigate to the project root (assuming the script is in the project root)
cd /d "%~dp0"

REM Start the Node.js application with dashboard
call npm start

REM If the dashboard is closed, keep the command prompt open
cmd /k