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
