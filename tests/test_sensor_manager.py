import time
from src.sensor_manager import SensorWorker, SystemMetrics

def test_sensor_worker_sample():
    worker = SensorWorker(interval=1.0)
    # Take initial sample to establish network baseline
    m1 = worker.sample_metrics()
    assert isinstance(m1, SystemMetrics)
    assert 0.0 <= m1.cpu_percent <= 100.0
    assert 0.0 <= m1.ram_percent <= 100.0
    assert m1.ram_total_gb > 0.0
    assert m1.ram_used_gb >= 0.0
    assert m1.net_download_bps >= 0.0
    assert m1.net_upload_bps >= 0.0
    assert isinstance(m1.net_download_str, str)
    assert isinstance(m1.net_upload_str, str)

    # Let a moment pass and sample again
    time.sleep(0.1)
    m2 = worker.sample_metrics()
    assert isinstance(m2, SystemMetrics)
    assert len(worker.history_cpu) >= 2

def test_sensor_worker_admin_fallback():
    worker = SensorWorker()
    m = worker.sample_metrics()
    # If not admin, temp should be None and status needs_admin
    if not worker.has_admin:
        assert m.cpu_temp is None
        assert m.cpu_temp_status == "needs_admin"
    else:
        assert m.cpu_temp_status in ("ok", "unsupported")

def test_sensor_worker_network_spike_protection():
    worker = SensorWorker()
    worker.last_net_bytes = (100000, 100000)
    worker.last_sample_time = time.time() - 1.0

    # Simulate adapter reset where new bytes is less than last bytes
    down_rate, up_rate = worker._calc_net_rates(50000, 50000, time.time())
    assert down_rate == 0.0
    assert up_rate == 0.0
