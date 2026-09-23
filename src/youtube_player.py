"""
YouTube Player and Floating Picture-in-Picture (PiP) Window.
Lightweight, frameless, hardware-accelerated video playback using QtWebEngine.
Supports both YouTube Embed and Fallback Clean Watch mode to bypass Error 152 embed restrictions.
"""
import os
import re
from typing import Optional
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QUrl
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineSettings, QWebEnginePage, QWebEngineProfile, QWebEngineScript
)

from src.config import AppConfig

def extract_youtube_id(url_or_id: str) -> Optional[str]:
    """Extract 11-character YouTube video ID from various URL formats or raw ID."""
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if re.fullmatch(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/|\/live\/)([a-zA-Z0-9_-]{11})",
        r"[?&]v=([a-zA-Z0-9_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None

CLEAN_THEATER_CSS = """
#masthead-container, #guide, #related, #comments, #secondary, #below,
#chat-container, ytd-banner-promo-renderer, tp-yt-app-drawer, #chat, #panels,
ytd-miniplayer, #header, #info, #meta, ytd-merch-shelf-renderer {
    display: none !important;
}
html, body {
    overflow: hidden !important;
    background: #000 !important;
}
#player-container-outer, #player-container-inner, #player-container, #movie_player,
.html5-video-player, video {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    max-width: 100vw !important;
    max-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    z-index: 999999 !important;
    background: #000 !important;
}
"""

INJECT_JS = """
(function() {
    function setupVideoControls() {
        var v = document.querySelector('video');
        if (v && !v._attachedTaskbar) {
            v._attachedTaskbar = true;
            v.addEventListener('play', function() { console.log('STATUS:PLAYING'); });
            v.addEventListener('pause', function() { console.log('STATUS:PAUSED'); });
            v.addEventListener('ended', function() { console.log('STATUS:ENDED'); });
            if (!v.paused) console.log('STATUS:PLAYING');
        }

        // Auto click un-mute if video started muted
        if (v && v.muted) {
            v.muted = false;
        }

        // Check for embed error 152 / unavailable error
        var errorScreen = document.querySelector('.ytp-error, .ytp-error-content');
        if (errorScreen && errorScreen.offsetParent !== null) {
            console.log('STATUS:EMBED_ERROR');
        }
    }

    // Inject clean styling if on youtube.com/watch
    if (window.location.href.indexOf('/watch') !== -1) {
        var style = document.getElementById('taskbar-clean-css');
        if (!style) {
            style = document.createElement('style');
            style.id = 'taskbar-clean-css';
            style.textContent = `{CSS_CONTENT}`;
            document.head.appendChild(style);
        }
    }

    setInterval(setupVideoControls, 800);
})();

function jsPlay() {
    var v = document.querySelector('video');
    if (v) v.play();
}
function jsPause() {
    var v = document.querySelector('video');
    if (v) v.pause();
}
function jsToggle() {
    var v = document.querySelector('video');
    if (v) {
        if (v.paused) v.play();
        else v.pause();
    }
}
function jsSetVolume(val) {
    var v = document.querySelector('video');
    if (v) v.volume = Math.max(0, Math.min(1, val / 100.0));
}
"""

class CustomWebEnginePage(QWebEnginePage):
    """Custom page to intercept console logs for playback state and embed error detection."""
    status_signal = Signal(str)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if message.startswith("STATUS:"):
            self.status_signal.emit(message.replace("STATUS:", ""))


class YouTubePipWindow(QWidget):
    """
    Picture-in-Picture floating mini player.
    Always on top, frameless with acrylic border, draggable and resizable.
    """
    playback_state_changed = Signal(bool)  # True = playing, False = paused

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_video_id = extract_youtube_id(self.config.last_youtube_url) or "jfKfPfyJRdk"
        self.is_playing = False
        self._drag_pos = QPoint()
        self._is_dragging = False
        self._is_fallback_mode = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._init_ui()
        self._load_video(self.current_video_id)

    def _init_ui(self):
        self.setObjectName("YouTubePipWindow")
        w = max(280, self.config.pip_width)
        h = max(160, self.config.pip_height)
        self.resize(w, h)

        # Restore position if available
        if self.config.pip_pos_x is not None and self.config.pip_pos_y is not None:
            self.move(self.config.pip_pos_x, self.config.pip_pos_y)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        # Main Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("PipCard")
        self.card.setStyleSheet("""
            QFrame#PipCard {
                background-color: #0f172a;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 10px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Overlay Title / Drag Bar
        self.top_bar = QFrame(self.card)
        self.top_bar.setFixedHeight(28)
        self.top_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.95);
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)

        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(8, 2, 8, 2)
        top_layout.setSpacing(6)

        icon_lbl = QLabel("▶")
        icon_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
        top_layout.addWidget(icon_lbl)

        self.title_lbl = QLabel("YouTube Mini Player")
        self.title_lbl.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 500;")
        top_layout.addWidget(self.title_lbl, 1)

        # Minimize to taskbar button
        min_btn = QPushButton("—")
        min_btn.setFixedSize(20, 20)
        min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover { color: #f8fafc; }
        """)
        min_btn.clicked.connect(self.hide)
        top_layout.addWidget(min_btn)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { color: #ef4444; }
        """)
        close_btn.clicked.connect(self.stop_and_hide)
        top_layout.addWidget(close_btn)

        card_layout.addWidget(self.top_bar)

        # 2. Web Engine View
        self.web_view = QWebEngineView(self.card)
        self.custom_page = CustomWebEnginePage(self.web_view)
        self.custom_page.status_signal.connect(self._on_player_status)
        self.web_view.setPage(self.custom_page)

        # Set realistic desktop browser User-Agent
        profile = self.custom_page.profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

        # Configure WebEngine settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.setStyleSheet("background-color: #000; border-bottom-left-radius: 9px; border-bottom-right-radius: 9px;")
        card_layout.addWidget(self.web_view, 1)

        main_layout.addWidget(self.card)

    def _load_video(self, video_id: str, force_watch_mode: bool = False):
        """Load video in embed mode or clean watch mode."""
        self.current_video_id = video_id
        if force_watch_mode:
            self._is_fallback_mode = True
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            self._is_fallback_mode = False
            # Standard embed URL with autoplay, playsinline, and high priority
            url = f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1&playsinline=1&enablejsapi=1&rel=0"

        self.web_view.load(QUrl(url))

    def _on_load_finished(self, ok: bool):
        if ok:
            # Inject control and tracking scripts
            clean_css = CLEAN_THEATER_CSS.replace("\n", " ").replace('"', '\\"')
            js = INJECT_JS.replace("{CSS_CONTENT}", clean_css)
            self.web_view.page().runJavaScript(js)
            # Set initial volume
            self.set_volume(self.config.media_volume)

    def _on_player_status(self, status: str):
        if status == "PLAYING":
            self.is_playing = True
            self.playback_state_changed.emit(True)
        elif status in ("PAUSED", "ENDED"):
            self.is_playing = False
            self.playback_state_changed.emit(False)
        elif status == "EMBED_ERROR":
            # Video owner restricted embeds (Error 152). Fallback to clean watch mode!
            if not self._is_fallback_mode:
                self._load_video(self.current_video_id, force_watch_mode=True)

    def load_url(self, url_or_id: str):
        vid = extract_youtube_id(url_or_id)
        if vid:
            self.current_video_id = vid
            self.config.last_youtube_url = url_or_id
            self.config.save()
            self._load_video(vid, force_watch_mode=False)
            self.show()
            self.raise_()

    def play(self):
        self.web_view.page().runJavaScript("jsPlay();")

    def pause(self):
        self.web_view.page().runJavaScript("jsPause();")

    def toggle_play(self):
        self.web_view.page().runJavaScript("jsToggle();")

    def set_volume(self, vol: int):
        self.config.media_volume = vol
        self.config.save()
        self.web_view.page().runJavaScript(f"jsSetVolume({vol});")

    def stop_and_hide(self):
        self.pause()
        self.hide()

    def toggle_pip_visible(self, anchor_point: Optional[QPoint] = None):
        """Toggle PiP window visibility. Anchor above taskbar if opening for first time."""
        if self.isVisible():
            self.hide()
        else:
            if self.config.pip_pos_x is None and anchor_point is not None:
                target_x = max(10, anchor_point.x() - self.width() + 40)
                target_y = max(10, anchor_point.y() - self.height() - 10)
                self.move(target_x, target_y)
            self.show()
            self.raise_()

    # Window drag handling
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and self._is_dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.config.pip_pos_x = self.x()
            self.config.pip_pos_y = self.y()
            self.config.save()
            event.accept()
