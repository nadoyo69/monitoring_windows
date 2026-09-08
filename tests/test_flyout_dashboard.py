from collections import deque
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from src.flyout_dashboard import FlyoutDashboard, SparklineWidget
from src.sensor_manager import SystemMetrics

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_sparkline_widget(qapp):
    spark = SparklineWidget(color="#38bdf8", max_val=100.0)
    data = deque([10.0, 20.0, 50.0, 80.0], maxlen=60)
    spark.set_data(data)
    assert len(spark.data) == 4

def test_flyout_dashboard_init_and_update(qapp):
    dash = FlyoutDashboard()
    assert dash.width() == 360
    assert dash.height() == 450

    metrics = SystemMetrics(
        cpu_percent=45.0,
        cpu_temp=62.0,
        ram_percent=55.0,
        ram_used_gb=8.8,
        ram_total_gb=16.0,
        net_download_str="5.2 MB/s",
        net_upload_str="1.1 MB/s",
        top_processes=[{"name": "chrome.exe", "cpu": 15.0, "mem_mb": 500}]
    )
    history = deque([30.0, 40.0, 45.0], maxlen=60)
    dash.update_data(metrics, history)

    assert "45%" in dash.cpu_stat_lbl.text()
    assert "62°C" in dash.cpu_stat_lbl.text()
    assert dash.cpu_bar.value() == 45
    assert dash.ram_bar.value() == 55

    # Test toggle positioning
    dash.toggle_at(QPoint(500, 800))
    assert dash.isVisible()
    dash.toggle_at(QPoint(500, 800))
    assert not dash.isVisible()
