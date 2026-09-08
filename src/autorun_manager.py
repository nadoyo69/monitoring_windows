"""
Windows Task Scheduler Auto-Run Manager.
Registers and unregisters TaskbarHardwareMonitor as an elevated task on logon,
bypassing UAC prompts.
"""
import os
import subprocess
import sys

TASK_NAME = "TaskbarHardwareMonitor"

def get_launch_command() -> str:
    """Return the absolute path to the launch target (run.bat or pythonw.exe)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_bat = os.path.join(base_dir, "run.bat")
    if os.path.exists(run_bat):
        return run_bat

    # Fallback directly to pythonw.exe with main.py
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    main_py = os.path.join(base_dir, "src", "main.py")
    return f'"{pythonw}" "{main_py}"'

def is_autorun_enabled() -> bool:
    """Check if the scheduled task is already registered."""
    try:
        cmd = ["schtasks", "/query", "/tn", TASK_NAME]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return res.returncode == 0
    except Exception:
        return False

def enable_autorun() -> bool:
    """Register task in Windows Task Scheduler with highest privileges."""
    try:
        target = get_launch_command()
        # Enclose target in quotes
        tr_arg = f'"{target}"' if not target.startswith('"') else target
        cmd = [
            "schtasks", "/create",
            "/tn", TASK_NAME,
            "/tr", tr_arg,
            "/sc", "onlogon",
            "/rl", "highest",
            "/f"
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return res.returncode == 0
    except Exception:
        return False

def disable_autorun() -> bool:
    """Remove task from Windows Task Scheduler."""
    try:
        cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return res.returncode == 0
    except Exception:
        return False

def toggle_autorun() -> bool:
    """Toggle auto-run on/off and return the new status."""
    if is_autorun_enabled():
        disable_autorun()
        return False
    else:
        enable_autorun()
        return True
