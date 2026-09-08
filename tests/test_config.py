import os
import tempfile
from src.config import AppConfig

def test_app_config_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        cfg = AppConfig(config_file=config_path)
        assert cfg.pos_x is None
        assert cfg.pos_y is None
        assert cfg.is_locked is False
        assert cfg.refresh_interval == 1.0
        assert cfg.show_taskbar_widget is True

def test_app_config_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        cfg = AppConfig(config_file=config_path)
        cfg.set_window_pos(350, 800)
        cfg.is_locked = True
        cfg.refresh_interval = 2.0
        cfg.save()

        # Reload from same file
        cfg2 = AppConfig(config_file=config_path)
        assert cfg2.pos_x == 350
        assert cfg2.pos_y == 800
        assert cfg2.is_locked is True
        assert cfg2.refresh_interval == 2.0
