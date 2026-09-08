@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Taskbar Hardware Monitor - Setup & Auto-Start
echo ========================================================
echo.

echo [1/2] Memeriksa Driver Sensor Suhu CPU (PawnIO)...
python -c "import os, sys, clr; sys.path.append(os.path.join(os.getcwd(), 'lib')); clr.AddReference(os.path.join(os.getcwd(), 'lib', 'LibreHardwareMonitorLib.dll')); from LibreHardwareMonitor.PawnIo import PawnIo; sys.exit(0 if PawnIo.IsInstalled else 1)" 2>nul

if %ERRORLEVEL% equ 0 (
    echo [SUKSES] Driver sensor suhu (PawnIO) sudah terpasang.
) else (
    echo [INFO] Driver PawnIO diperlukan untuk membaca suhu CPU Intel Core Ultra / Windows 11.
    if not exist "%~dp0PawnIO_setup.exe" (
        echo Mengunduh installer resmi PawnIO...
        powershell -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe' -OutFile '%~dp0PawnIO_setup.exe'"
    )
    echo Menjalankan installer PawnIO... Silakan klik "Install" pada jendela yang muncul.
    start "" "%~dp0PawnIO_setup.exe"
)

echo.
echo [2/2] Mendaftarkan auto-start saat Windows boot (Support Baterai Laptop)...
powershell -ExecutionPolicy Bypass -Command "$action = New-ScheduledTaskAction -Execute '\"%~dp0run.bat\"'; $trigger = New-ScheduledTaskTrigger -AtLogOn; $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0; $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest; Register-ScheduledTask -TaskName 'TaskbarHardwareMonitor' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force"

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUKSES] Aplikasi berhasil didaftarkan ke Windows Task Scheduler!
    echo - Otomatis berjalan saat Windows dinyalakan/login.
    echo - Tetap aktif saat laptop menggunakan Baterai (tidak mati sendiri).
    echo - Hak akses tertinggi (Administrator) otomatis aktif tanpa dialog UAC.
) else (
    echo.
    echo Menggunakan fallback schtasks standar...
    schtasks /create /tn "TaskbarHardwareMonitor" /tr "\"%~dp0run.bat\"" /sc onlogon /rl highest /f
)

echo.
pause
