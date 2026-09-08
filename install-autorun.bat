@echo off
setlocal
cd /d "%~dp0"

echo [Taskbar Hardware Monitor] Mendaftarkan auto-start saat Windows boot...
schtasks /create /tn "TaskbarHardwareMonitor" /tr "\"%~dp0run.bat\"" /sc onlogon /rl highest /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUKSES] Aplikasi berhasil didaftarkan ke Windows Task Scheduler!
    echo Aplikasi akan otomatis berjalan saat login dengan hak akses tertinggi tanpa dialog UAC.
) else (
    echo.
    echo [GAGAL] Gagal mendaftarkan task. Pastikan Anda menjalankan script ini sebagai Administrator (Klik Kanan ^> Run as administrator).
)

echo.
pause
