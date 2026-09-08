"""
Configuration Manager for Taskbar Hardware Monitor.
Handles user preferences and window position persistence.
"""
import json
import os
from typing import Optional, Tuple

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.json"
)

class AppConfig:
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or DEFAULT_CONFIG_PATH
        self.pos_x: Optional[int] = None
        self.pos_y: Optional[int] = None
        self.is_locked: bool = False
        self.refresh_interval: float = 1.0
        self.show_taskbar_widget: bool = True
        self.show_tray_icon: bool = True
        self.autorun_enabled: bool = False
        self.load()

    def load(self):
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_file):
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.pos_x = data.get("pos_x")
                self.pos_y = data.get("pos_y")
                self.is_locked = bool(data.get("is_locked", False))
                self.refresh_interval = float(data.get("refresh_interval", 1.0))
                self.show_taskbar_widget = bool(data.get("show_taskbar_widget", True))
                self.show_tray_icon = bool(data.get("show_tray_icon", True))
                self.autorun_enabled = bool(data.get("autorun_enabled", False))
        except Exception:
            pass

    def save(self):
        """Save current configuration to JSON file."""
        data = {
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "is_locked": self.is_locked,
            "refresh_interval": self.refresh_interval,
            "show_taskbar_widget": self.show_taskbar_widget,
            "show_tray_icon": self.show_tray_icon,
            "autorun_enabled": self.autorun_enabled,
        }
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_window_pos(self) -> Optional[Tuple[int, int]]:
        """Return saved (x, y) coordinates if available."""
        if self.pos_x is not None and self.pos_y is not None:
            return (self.pos_x, self.pos_y)
        return None

    def set_window_pos(self, x: int, y: int):
        """Update window position and save immediately."""
        self.pos_x = x
        self.pos_y = y
        self.save()
