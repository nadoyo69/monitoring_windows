import pytest
from PySide6.QtWidgets import QApplication
from src.config import AppConfig
from src.sensor_manager import SystemMetrics
from src.taskbar_widget import TaskbarWidget

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_taskbar_widget_init(qapp):
    cfg = AppConfig()
    widget = TaskbarWidget(config=cfg)
    assert widget.width() == 320
    assert widget.height() == 30

    # Test metric updates
    metrics = SystemMetrics(
        cpu_percent=42.0,
        cpu_temp=58.5,
        ram_percent=60.0,
        ram_used_gb=9.6,
        ram_total_gb=16.0,
        net_download_str="3.2 MB/s",
        net_upload_str="450 KB/s"
    )
    widget.update_metrics(metrics)
    assert widget.cpu_pct_lbl.text() == "42%"
    assert widget.cpu_temp_lbl.text() == "58°C"
    assert widget.ram_pct_lbl.text() == "60%"
    assert widget.net_down_lbl.text() == "↓3.2 MB/s"

def test_taskbar_widget_reset_position_and_lock(qapp):
    cfg = AppConfig()
    cfg.is_locked = True
    widget = TaskbarWidget(config=cfg)

    # Test reset_position
    widget.reset_position()
    assert widget.config.is_locked is True
    assert widget.isVisible()

    # Test toggle lock
    widget._toggle_lock()
    assert widget.config.is_locked is False

    # Test ensure_topmost runs without error
    widget.ensure_topmost()

    # Test dock_inside_taskbar
    widget.dock_inside_taskbar(x=240)
    assert widget.x() == 240
    assert widget.isVisible()

    # Test float_above_taskbar
    widget.float_above_taskbar(x=240)
    assert widget.x() == 240
    assert widget.isVisible()

    widget.close()


