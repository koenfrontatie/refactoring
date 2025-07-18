@echo off
REM Start the Socket Test GUI in the virtual environment
call "..\venv\Scripts\activate.bat"
start /b pythonw socket_test_gui.py
exit