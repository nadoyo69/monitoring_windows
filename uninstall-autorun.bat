@echo off
setlocal

echo [Taskbar Hardware Monitor] Menghapus auto-start dari Windows Task Scheduler...
schtasks /delete /tn "TaskbarHardwareMonitor" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUKSES] Auto-start berhasil dimatikan.
) else (
    echo.
    echo [INFO] Task tidak ditemukan atau sudah dihapus sebelumnya.
)

echo.
pause
