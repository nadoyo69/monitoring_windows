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
    assert widget.width() == 310
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
