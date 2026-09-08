@echo off
setlocal
cd /d "%~dp0"

echo [Taskbar Hardware Monitor] Memulai build standalone .exe...
python -m pip install pyinstaller

echo.
echo Mengompilasi aplikasi...
pyinstaller --noconsole --onefile ^
    --name "TaskbarHardwareMonitor" ^
    --add-data "src;src" ^
    src\main.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUKSES] File executable telah berhasil dibuat di: dist\TaskbarHardwareMonitor.exe
) else (
    echo.
    echo [ERROR] Gagal melakukan compile.
)

pause
