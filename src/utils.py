"""
Utility functions for Taskbar Hardware Monitor.
Includes metric formatting, color thresholds, and Windows privilege checks.
"""
import ctypes

def is_admin() -> bool:
    """Check if the current process is running with Windows Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def format_speed(bytes_per_sec: float) -> str:
    """Format bytes per second into human-readable network throughput (e.g. 4.5 MB/s)."""
    if bytes_per_sec < 1024:
        return f"{int(bytes_per_sec)} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 * 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    return f"{bytes_per_sec / (1024 * 1024 * 1024):.1f} GB/s"

def format_bytes(bytes_val: float) -> str:
    """Format raw byte counts to human-readable size in GB."""
    gb = bytes_val / (1024 * 1024 * 1024)
    return f"{gb:.1f} GB"

def get_temp_color(temp_c: float | None) -> str:
    """
    Return hex color based on CPU temperature threshold:
    - Normal (<70°C): Emerald Green (#10b981)
    - Warning (70-85°C): Amber Orange (#f59e0b)
    - Critical (>85°C): Red (#ef4444)
    - None/Unknown: Slate Muted Gray (#94a3b8)
    """
    if temp_c is None:
        return "#94a3b8"
    if temp_c < 70.0:
        return "#10b981"
    elif temp_c <= 85.0:
        return "#f59e0b"
    return "#ef4444"

def get_taskbar_geometry() -> tuple[int, int, int, int]:
    """
    Get Windows Taskbar bounding box (left, top, right, bottom).
    Fallback to standard bottom 48px if Win32 API is unavailable.
    """
    try:
        from ctypes import wintypes
        class APPBARDATA(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('hWnd', wintypes.HWND),
                ('uCallbackMessage', wintypes.UINT),
                ('uEdge', wintypes.UINT),
                ('rc', wintypes.RECT),
                ('lParam', wintypes.LPARAM),
            ]
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        res = ctypes.windll.shell32.SHAppBarMessage(5, ctypes.byref(abd)) # ABM_GETTASKBARPOS = 5
        if res and (abd.rc.right > abd.rc.left) and (abd.rc.bottom > abd.rc.top):
            return (abd.rc.left, abd.rc.top, abd.rc.right, abd.rc.bottom)
    except Exception:
        pass

    try:
        tray = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        if tray:
            rect = (ctypes.c_long * 4)()
            if ctypes.windll.user32.GetWindowRect(tray, rect):
                return (rect[0], rect[1], rect[2], rect[3])
    except Exception:
        pass

    # Default fallback: 1920x1200 bottom taskbar (48px)
    return (0, 1152, 1920, 1200)

