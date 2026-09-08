"""
Main Entry Point for Taskbar Hardware Monitor.
Initializes QApplication, single-instance lock, sensor worker, and UI components.
"""
import atexit
import os
import sys
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

# Ensure package root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.autorun_manager import is_autorun_enabled, toggle_autorun
from src.config import AppConfig
from src.flyout_dashboard import FlyoutDashboard
from src.sensor_manager import SensorWorker, SystemMetrics
from src.taskbar_widget import TaskbarWidget
from src.tray_manager import TrayManager

LOCK_FILE_PATH = os.path.join(BASE_DIR, ".app.lock")

def acquire_single_instance_lock() -> bool:
    """Ensure only one instance of Taskbar Hardware Monitor runs at a time."""
    try:
        if os.path.exists(LOCK_FILE_PATH):
            try:
                os.remove(LOCK_FILE_PATH)
            except OSError:
                return False  # File is locked by another running process

        lock_fd = open(LOCK_FILE_PATH, "w")
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()

        def cleanup():
            try:
                lock_fd.close()
                if os.path.exists(LOCK_FILE_PATH):
                    os.remove(LOCK_FILE_PATH)
            except Exception:
                pass

        atexit.register(cleanup)
        return True
    except Exception:
        return True

def main():
    if not acquire_single_instance_lock():
        print("Taskbar Hardware Monitor is already running.")
        sys.exit(0)

    # Initialize QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Load configuration
    config = AppConfig()
    config.autorun_enabled = is_autorun_enabled()

    # Create components
    taskbar_widget = TaskbarWidget(config=config)
    flyout_dashboard = FlyoutDashboard()
    tray_manager = TrayManager(config=config)

    # Show initial components based on config
    if config.show_taskbar_widget:
        taskbar_widget.show()

    if config.show_tray_icon:
        tray_manager.show()

    # Initialize Sensor Worker thread
    sensor_worker = SensorWorker(interval=config.refresh_interval)

    # Signal Wiring: Metrics distribution
    def handle_metrics_ready(m: SystemMetrics):
        taskbar_widget.update_metrics(m)
        tray_manager.update_metrics(m)
        if flyout_dashboard.isVisible():
            flyout_dashboard.update_data(m, sensor_worker.history_cpu)

    sensor_worker.metrics_ready.connect(handle_metrics_ready)

    # Toggle Dashboard Handler
    def toggle_dashboard_from_widget():
        widget_rect = taskbar_widget.geometry()
        # Anchor at center-top of widget
        anchor = QPoint(widget_rect.x() + (widget_rect.width() // 2), widget_rect.y())
        flyout_dashboard.toggle_at(anchor)

    def toggle_dashboard_from_tray():
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None
        if screen_geo:
            anchor = QPoint(screen_geo.x() + screen_geo.width() - 40, screen_geo.y() + screen_geo.height() - 10)
        else:
            anchor = QPoint(800, 600)
        flyout_dashboard.toggle_at(anchor)

    taskbar_widget.toggle_dashboard_requested.connect(toggle_dashboard_from_widget)
    tray_manager.toggle_dashboard_requested.connect(toggle_dashboard_from_tray)

    # Toggle Taskbar Widget visibility
    def on_widget_visibility_toggled(show: bool):
        if show:
            taskbar_widget.show()
        else:
            taskbar_widget.hide()

    tray_manager.toggle_widget_requested.connect(on_widget_visibility_toggled)

    # Refresh rate changes
    def on_refresh_rate_changed(rate: float):
        sensor_worker.interval = rate

    taskbar_widget.refresh_rate_changed.connect(on_refresh_rate_changed)

    # Auto-run toggle
    def on_autorun_toggle():
        new_state = toggle_autorun()
        config.autorun_enabled = new_state
        config.save()
        tray_manager.act_autorun.setChecked(new_state)

    taskbar_widget.autorun_toggle_requested.connect(on_autorun_toggle)
    tray_manager.autorun_toggle_requested.connect(on_autorun_toggle)

    # Position reset, Docking and Lock synchronizing
    tray_manager.reset_position_requested.connect(taskbar_widget.reset_position)
    tray_manager.dock_inside_taskbar_requested.connect(taskbar_widget.dock_inside_taskbar)
    tray_manager.float_above_taskbar_requested.connect(taskbar_widget.float_above_taskbar)
    tray_manager.toggle_lock_requested.connect(taskbar_widget._toggle_lock)
    taskbar_widget.lock_toggled.connect(tray_manager.sync_lock_state)

    # Exit Handler
    def exit_app():
        sensor_worker.stop()
        flyout_dashboard.close()
        taskbar_widget.close()
        tray_manager.hide()
        app.quit()

    taskbar_widget.exit_requested.connect(exit_app)
    tray_manager.exit_requested.connect(exit_app)

    # Start sensor sampling thread
    sensor_worker.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
