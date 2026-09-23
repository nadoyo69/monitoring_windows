import os
import tempfile
import pytest
from src.youtube_player import extract_youtube_id
from src.config import AppConfig

def test_extract_youtube_id_various_formats():
    valid_id = "jfKfPfyJRdk"
    
    # Standard watch
    assert extract_youtube_id(f"https://www.youtube.com/watch?v={valid_id}") == valid_id
    # Watch with extra params
    assert extract_youtube_id(f"https://www.youtube.com/watch?v={valid_id}&t=120s&feature=shared") == valid_id
    # youtu.be short URL
    assert extract_youtube_id(f"https://youtu.be/{valid_id}") == valid_id
    assert extract_youtube_id(f"https://youtu.be/{valid_id}?t=30") == valid_id
    # embed URL
    assert extract_youtube_id(f"https://www.youtube.com/embed/{valid_id}") == valid_id
    # shorts URL
    assert extract_youtube_id(f"https://www.youtube.com/shorts/{valid_id}") == valid_id
    # live stream URL
    assert extract_youtube_id(f"https://www.youtube.com/live/{valid_id}") == valid_id
    # raw 11-char ID
    assert extract_youtube_id(valid_id) == valid_id

def test_extract_youtube_id_invalid():
    assert extract_youtube_id("") is None
    assert extract_youtube_id("https://google.com") is None
    assert extract_youtube_id("not-a-valid-id") is None
    assert extract_youtube_id(None) is None

def test_config_media_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        cfg = AppConfig(config_file=tmp_path)
        assert cfg.media_volume == 80
        assert "youtube.com" in cfg.last_youtube_url

        cfg.media_volume = 95
        cfg.pip_width = 480
        cfg.pip_height = 270
        cfg.pip_pos_x = 500
        cfg.pip_pos_y = 400
        cfg.last_youtube_url = "https://www.youtube.com/watch?v=5yx6BWlEVcY"
        cfg.save()

        cfg2 = AppConfig(config_file=tmp_path)
        assert cfg2.media_volume == 95
        assert cfg2.pip_width == 480
        assert cfg2.pip_height == 270
        assert cfg2.pip_pos_x == 500
        assert cfg2.pip_pos_y == 400
        assert cfg2.last_youtube_url == "https://www.youtube.com/watch?v=5yx6BWlEVcY"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
