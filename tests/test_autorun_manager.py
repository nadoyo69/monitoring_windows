from unittest.mock import patch, MagicMock
from src.autorun_manager import is_autorun_enabled, enable_autorun, disable_autorun, toggle_autorun

def test_is_autorun_enabled_true():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert is_autorun_enabled() is True

def test_is_autorun_enabled_false():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert is_autorun_enabled() is False

def test_enable_autorun():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert enable_autorun() is True

def test_disable_autorun():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert disable_autorun() is True

def test_toggle_autorun():
    with patch("src.autorun_manager.is_autorun_enabled", side_effect=[False, True]):
        with patch("src.autorun_manager.enable_autorun", return_value=True):
            res = toggle_autorun()
            assert res is True
