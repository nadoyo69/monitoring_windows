from src.utils import format_speed, format_bytes, get_temp_color, is_admin

def test_format_speed():
    assert format_speed(500) == "500 B/s"
    assert format_speed(1024 * 50) == "50.0 KB/s"
    assert format_speed(1024 * 1024 * 4.5) == "4.5 MB/s"
    assert format_speed(1024 * 1024 * 1024 * 2.1) == "2.1 GB/s"

def test_format_bytes():
    assert format_bytes(1024 * 1024 * 1024 * 8) == "8.0 GB"
    assert format_bytes(1024 * 1024 * 1024 * 16.5) == "16.5 GB"

def test_get_temp_color():
    assert get_temp_color(None) == "#94a3b8"   # muted gray
    assert get_temp_color(55) == "#10b981"     # normal green (<70)
    assert get_temp_color(69.9) == "#10b981"   # normal green (<70)
    assert get_temp_color(70) == "#f59e0b"     # warning amber (70-85)
    assert get_temp_color(85) == "#f59e0b"     # warning amber (70-85)
    assert get_temp_color(85.1) == "#ef4444"   # alert red (>85)
    assert get_temp_color(95) == "#ef4444"     # alert red (>85)

def test_is_admin_returns_bool():
    result = is_admin()
    assert isinstance(result, bool)
