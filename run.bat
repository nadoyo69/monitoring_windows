@echo off
setlocal
cd /d "%~dp0"

:: Kill previous instance if running
taskkill /f /im pythonw.exe 2>nul
timeout /t 1 /nobreak >nul

:: Use pythonw to launch silently in the background without terminal console
start "" "C:\Users\vdipr\AppData\Local\Programs\Python\Python312\pythonw.exe" "src\main.py"
exit

