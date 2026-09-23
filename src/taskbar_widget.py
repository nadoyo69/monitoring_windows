import sys
import ctypes
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QEvent
from PySide6.QtGui import QAction, QFont, QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QMenu, QApplication, QInputDialog
)

from src.config import AppConfig
from src.sensor_manager import SystemMetrics
from src.utils import get_temp_color, get_taskbar_geometry

class AudioWaveWidget(QWidget):
    """Miniature animated audio wave bars."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 14)
        self.is_active = False
        self._bars = [3, 6, 9, 5]
        self._step = 0
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._animate_step)

    def set_active(self, active: bool):
        self.is_active = active
        if active:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._bars = [2, 3, 2, 3]
            self.update()

    def _animate_step(self):
        patterns = [
            [3, 8, 12, 6],
            [6, 12, 5, 10],
            [10, 4, 11, 7],
            [5, 11, 7, 4],
            [8, 5, 12, 8]
        ]
        self._step = (self._step + 1) % len(patterns)
        self._bars = patterns[self._step]
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        color = QColor("#38bdf8") if self.is_active else QColor("#64748b")
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)

        x_coords = [1, 6, 11, 16]
        w = 3
        h_max = self.height()
        for i, h in enumerate(self._bars):
            y = h_max - h
            painter.drawRect(x_coords[i], max(1, y), w, min(h, h_max - 1))


class TaskbarWidget(QWidget):
    toggle_dashboard_requested = Signal()
    refresh_rate_changed = Signal(float)
    autorun_toggle_requested = Signal()
    exit_requested = Signal()
    lock_toggled = Signal(bool)
    play_pause_clicked = Signal()
    pip_toggle_clicked = Signal()
    play_youtube_url_requested = Signal(str)

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._drag_pos = QPoint()
        self._is_dragging = False
        self._is_closing = False
        self._is_playing = False

        # Configure window flags: frameless, always-on-top, tool window (no Alt+Tab entry)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._init_ui()
        self._apply_initial_geometry()
        self._init_win32_behavior()

    def _init_ui(self):
        self.setObjectName("TaskbarWidgetContainer")
        self.setFixedHeight(30)
        self.setFixedWidth(415)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Background container frame
        self.container = QFrame(self)
        self.container.setObjectName("MetricBar")
        self.container.setStyleSheet("""
            QFrame#MetricBar {
                background-color: rgba(15, 23, 42, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
            }
            QFrame#MetricBar:hover {
                border: 1px solid rgba(56, 189, 248, 0.5);
                background-color: rgba(15, 23, 42, 0.98);
            }
        """)

        bar_layout = QHBoxLayout(self.container)
        bar_layout.setContentsMargins(8, 2, 8, 2)
        bar_layout.setSpacing(6)

        font_family = "Segoe UI Variable Display, Segoe UI, sans-serif"
        label_font = QFont(font_family, 8, QFont.Weight.Bold)
        val_font = QFont("Consolas, monospace", 8)

        # 1. CPU Section
        cpu_title = QLabel("CPU")
        cpu_title.setFont(label_font)
        cpu_title.setStyleSheet("color: #38bdf8;")
        self.cpu_pct_lbl = QLabel("0%")
        self.cpu_pct_lbl.setFont(val_font)
        self.cpu_pct_lbl.setStyleSheet("color: #f8fafc;")

        self.cpu_temp_lbl = QLabel("--°C")
        self.cpu_temp_lbl.setFont(val_font)
        self.cpu_temp_lbl.setStyleSheet("color: #94a3b8; padding: 1px 3px; border-radius: 3px;")

        bar_layout.addWidget(cpu_title)
        bar_layout.addWidget(self.cpu_pct_lbl)
        bar_layout.addWidget(self.cpu_temp_lbl)

        bar_layout.addWidget(self._create_separator())

        # 2. RAM Section
        ram_title = QLabel("RAM")
        ram_title.setFont(label_font)
        ram_title.setStyleSheet("color: #a855f7;")
        self.ram_pct_lbl = QLabel("0%")
        self.ram_pct_lbl.setFont(val_font)
        self.ram_pct_lbl.setStyleSheet("color: #f8fafc;")

        bar_layout.addWidget(ram_title)
        bar_layout.addWidget(self.ram_pct_lbl)

        bar_layout.addWidget(self._create_separator())

        # 3. Network Section (↓ Down / ↑ Up)
        net_title = QLabel("NET")
        net_title.setFont(label_font)
        net_title.setStyleSheet("color: #10b981;")

        self.net_down_lbl = QLabel("↓ 0K")
        self.net_down_lbl.setFont(val_font)
        self.net_down_lbl.setStyleSheet("color: #34d399;")

        self.net_up_lbl = QLabel("↑ 0K")
        self.net_up_lbl.setFont(val_font)
        self.net_up_lbl.setStyleSheet("color: #38bdf8;")

        bar_layout.addWidget(net_title)
        bar_layout.addWidget(self.net_down_lbl)
        bar_layout.addWidget(self.net_up_lbl)

        # 4. Media Player Integrated Section
        bar_layout.addWidget(self._create_separator())

        # Play / Pause Button
        self.media_play_btn = QLabel("▶")
        self.media_play_btn.setFixedSize(18, 18)
        self.media_play_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.media_play_btn.setStyleSheet("""
            QLabel {
                color: #38bdf8;
                font-size: 11px;
                font-weight: bold;
                border-radius: 3px;
                padding-left: 1px;
            }
            QLabel:hover {
                background-color: rgba(56, 189, 248, 0.25);
                color: #ffffff;
            }
        """)
        self.media_play_btn.setToolTip("Play / Pause YouTube")
        self.media_play_btn.mousePressEvent = lambda e: self._on_play_btn_clicked(e)
        bar_layout.addWidget(self.media_play_btn)

        # Audio Wave Bar Animation
        self.audio_wave = AudioWaveWidget()
        self.audio_wave.setToolTip("YouTube Audio Stream")
        bar_layout.addWidget(self.audio_wave)

        # PiP Pop-up Button
        self.media_pip_btn = QLabel("⤢")
        self.media_pip_btn.setFixedSize(18, 18)
        self.media_pip_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_pip_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.media_pip_btn.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 13px;
                font-weight: bold;
                border-radius: 3px;
            }
            QLabel:hover {
                background-color: rgba(148, 163, 184, 0.2);
                color: #38bdf8;
            }
        """)
        self.media_pip_btn.setToolTip("Buka / Tutup Layar Video PiP")
        self.media_pip_btn.mousePressEvent = lambda e: self._on_pip_btn_clicked(e)
        bar_layout.addWidget(self.media_pip_btn)

        main_layout.addWidget(self.container)

    def _on_play_btn_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_pause_clicked.emit()
            event.accept()

    def _on_pip_btn_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pip_toggle_clicked.emit()
            event.accept()

    def set_playback_state(self, is_playing: bool):
        self._is_playing = is_playing
        self.media_play_btn.setText("⏸" if is_playing else "▶")
        self.media_play_btn.setStyleSheet(f"""
            QLabel {{
                color: {'#10b981' if is_playing else '#38bdf8'};
                font-size: 11px;
                font-weight: bold;
                border-radius: 3px;
            }}
            QLabel:hover {{
                background-color: rgba(56, 189, 248, 0.25);
                color: #ffffff;
            }}
        """)
        self.audio_wave.set_active(is_playing)

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.18);")
        sep.setFixedHeight(14)
        return sep

    def _init_win32_behavior(self):
        """Configure Windows-specific topmost behavior and watchdog timer."""
        # Periodic watchdog to keep widget above Windows Shell_TrayWnd even when taskbar is clicked
        self._topmost_timer = QTimer(self)
        self._topmost_timer.setInterval(200)  # 200ms interval for immediate topmost recovery
        self._topmost_timer.timeout.connect(self.ensure_topmost)
        self._topmost_timer.start()

    def ensure_topmost(self):
        """Reassert topmost Z-order above Windows Shell_TrayWnd without stealing focus."""
        if sys.platform == "win32" and self.isVisible() and not self._is_closing:
            try:
                hwnd = int(self.winId())
                HWND_TOPMOST = -1
                # SWP_NOSIZE (1) | SWP_NOMOVE (2) | SWP_NOACTIVATE (0x10) | SWP_SHOWWINDOW (0x40) = 0x53
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0053)
            except Exception:
                pass

    def dock_inside_taskbar(self, x: int | None = None):
        """Snap and dock the widget centered cleanly inside the Windows taskbar."""
        tb_left, tb_top, tb_right, tb_bottom = get_taskbar_geometry()
        tb_height = tb_bottom - tb_top
        target_y = tb_top + max(0, (tb_height - self.height()) // 2)
        target_x = x if x is not None else max(10, min(self.x(), tb_right - self.width() - 20))
        if target_x < 100:
            target_x = 240  # Ideal slot between Windows 11 Weather widget and centered icons
        self.move(target_x, target_y)
        self.config.set_window_pos(target_x, target_y)
        self.config.is_locked = False
        self.config.show_taskbar_widget = True
        self.config.save()
        self.show()
        self.showNormal()
        self.raise_()
        self.ensure_topmost()
        self.lock_toggled.emit(False)

    def float_above_taskbar(self, x: int | None = None):
        """Dock the widget flush directly on top of the Windows taskbar (Option 2)."""
        tb_left, tb_top, tb_right, tb_bottom = get_taskbar_geometry()
        target_y = tb_top - self.height() - 2
        target_x = x if x is not None else 10
        self.move(target_x, target_y)
        self.config.set_window_pos(target_x, target_y)
        self.config.is_locked = True
        self.config.show_taskbar_widget = True
        self.config.save()
        self.show()
        self.showNormal()
        self.raise_()
        self.ensure_topmost()
        self.lock_toggled.emit(True)

    def reset_position(self):
        """Reset widget position to Option 2: flush directly above taskbar at (10, 1120)."""
        self.float_above_taskbar(x=10)

    def enterEvent(self, event):
        """Ensure widget is brought to top immediately on hover."""
        super().enterEvent(event)
        self.ensure_topmost()
        self.raise_()

    def changeEvent(self, event):
        """Prevent widget from remaining minimized when Show Desktop (Win+D) is pressed."""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and self.config.show_taskbar_widget and not self._is_closing:
                self.showNormal()
                self.ensure_topmost()
        super().changeEvent(event)

    def hideEvent(self, event):
        """Prevent unexpected hiding from Windows shell (e.g. Win+D or desktop toggle)."""
        super().hideEvent(event)
        if self.config.show_taskbar_widget and not self._is_closing:
            QTimer.singleShot(100, self._restore_visibility)

    def _restore_visibility(self):
        if self.config.show_taskbar_widget and not self._is_closing:
            self.show()
            self.showNormal()
            self.raise_()
            self.ensure_topmost()

    def closeEvent(self, event):
        self._is_closing = True
        if hasattr(self, '_topmost_timer'):
            self._topmost_timer.stop()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.ensure_topmost()

    def _apply_initial_geometry(self):
        """Set initial position from config or dock flush above taskbar."""
        pos = self.config.get_window_pos()
        tb_left, tb_top, tb_right, tb_bottom = get_taskbar_geometry()
        max_y = tb_top - self.height() - 2
        max_x = tb_right - self.width() - 10

        if pos is not None:
            x, y = pos
            clamped_x = max(tb_left + 10, min(x, max_x))
            clamped_y = max(10, min(y, max_y))
            self.move(clamped_x, clamped_y)
        else:
            # Default dock flush above taskbar near bottom-left or bottom-right
            target_x = 240
            self.move(target_x, max_y)

    def update_metrics(self, m: SystemMetrics):
        """Update display elements with latest metrics."""
        self.cpu_pct_lbl.setText(f"{int(m.cpu_percent)}%")

        # Temperature handling
        if m.cpu_temp is not None:
            temp_color = get_temp_color(m.cpu_temp)
            self.cpu_temp_lbl.setText(f"{int(m.cpu_temp)}°C")
            self.cpu_temp_lbl.setStyleSheet(
                f"color: {temp_color}; background-color: rgba(255, 255, 255, 0.08); padding: 1px 3px; border-radius: 3px;"
            )
            self.cpu_temp_lbl.setToolTip(f"CPU Package Temperature: {m.cpu_temp:.1f}°C")
        else:
            self.cpu_temp_lbl.setText("--°")
            status_tip = "Suhu CPU memerlukan Run as Administrator" if m.cpu_temp_status == "needs_admin" else "Sensor suhu tidak terdeteksi"
            self.cpu_temp_lbl.setToolTip(status_tip)
            self.cpu_temp_lbl.setStyleSheet("color: #64748b;")

        # RAM
        self.ram_pct_lbl.setText(f"{int(m.ram_percent)}%")
        self.ram_pct_lbl.setToolTip(f"RAM Used: {m.ram_used_gb:.1f} GB / {m.ram_total_gb:.1f} GB")

        # Network
        self.net_down_lbl.setText(f"↓{m.net_download_str}")
        self.net_up_lbl.setText(f"↑{m.net_upload_str}")

        # Keep topmost above taskbar during metric updates
        self.ensure_topmost()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and not self.config.is_locked:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            
            # Snap flush directly above taskbar to prevent falling into Windows 11 taskbar band
            tb_left, tb_top, tb_right, tb_bottom = get_taskbar_geometry()
            flush_dock_y = tb_top - self.height() - 2
            if new_pos.y() > flush_dock_y - 12:
                new_pos.setY(flush_dock_y)

            self.move(new_pos)
            self._is_dragging = True
            self.ensure_topmost()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                # Save new position
                self.config.set_window_pos(self.x(), self.y())
                self._is_dragging = False
                self.raise_()
                self.ensure_topmost()
            else:
                # Regular click: Toggle flyout dashboard
                self.toggle_dashboard_requested.emit()
            event.accept()

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """)

        act_dashboard = menu.addAction("📊 Buka Flyout Dashboard")
        act_dashboard.triggered.connect(lambda: self.toggle_dashboard_requested.emit())

        menu.addSeparator()

        # YouTube Media Player Menu
        act_pip = menu.addAction("🎦 Tampilkan / Sembunyikan Layar PiP")
        act_pip.triggered.connect(lambda: self.pip_toggle_clicked.emit())

        act_yt_url = menu.addAction("🎵 Masukkan URL YouTube...")
        act_yt_url.triggered.connect(self._prompt_youtube_url)

        yt_presets = menu.addMenu("📻 Preset Radio / Lofi 24/7")
        presets = [
            ("☕ Lofi Girl - Beats to relax/study", "https://www.youtube.com/watch?v=jfKfPfyJRdk"),
            ("🎹 Chillhop Radio - Jazzy Beats", "https://www.youtube.com/watch?v=5yx6BWlEVcY"),
            ("🌧️ Deep Focus Piano & Rain", "https://www.youtube.com/watch?v=WPni755-Krg"),
            ("🎧 Synthwave Radio - Chill Beats", "https://www.youtube.com/watch?v=4xDzrJKXOOY")
        ]
        for name, url in presets:
            act_preset = yt_presets.addAction(name)
            act_preset.triggered.connect(lambda checked=False, u=url: self.play_youtube_url_requested.emit(u))

        menu.addSeparator()

        act_dock_tb = menu.addAction("📌 Tempel di Dalam Taskbar")
        act_dock_tb.triggered.connect(lambda: self.dock_inside_taskbar(self.x()))

        act_float_tb = menu.addAction("📌 Pasang di Atas Taskbar")
        act_float_tb.triggered.connect(lambda: self.float_above_taskbar(self.x()))

        act_reset = menu.addAction("🎯 Reset Posisi Default")
        act_reset.triggered.connect(self.reset_position)

        act_lock = menu.addAction("🔒 Kunci Posisi")
        act_lock.setCheckable(True)
        act_lock.setChecked(self.config.is_locked)
        act_lock.triggered.connect(self._toggle_lock)

        # Refresh rate submenu
        rate_menu = menu.addMenu("⏱️ Refresh Rate")
        for rate, label in [(0.5, "0.5 Detik (Cepat)"), (1.0, "1.0 Detik (Default)"), (2.0, "2.0 Detik (Hemat)"), (5.0, "5.0 Detik (Sangat Hemat)")]:
            act_rate = rate_menu.addAction(label)
            act_rate.setCheckable(True)
            act_rate.setChecked(abs(self.config.refresh_interval - rate) < 0.01)
            act_rate.triggered.connect(lambda checked=False, r=rate: self._set_refresh_rate(r))

        act_autorun = menu.addAction("🚀 Start on Windows Boot")
        act_autorun.setCheckable(True)
        act_autorun.setChecked(self.config.autorun_enabled)
        act_autorun.triggered.connect(lambda: self.autorun_toggle_requested.emit())

        menu.addSeparator()

        act_exit = menu.addAction("❌ Exit")
        act_exit.triggered.connect(lambda: self.exit_requested.emit())

        menu.exec(global_pos)

    def _toggle_lock(self):
        self.config.is_locked = not self.config.is_locked
        self.config.save()
        self.lock_toggled.emit(self.config.is_locked)

    def _set_refresh_rate(self, rate: float):
        self.config.refresh_interval = rate
        self.config.save()
        self.refresh_rate_changed.emit(rate)

    def _prompt_youtube_url(self):
        url, ok = QInputDialog.getText(
            self,
            "Putar YouTube",
            "Masukkan Link Video / Live Stream YouTube:",
            text=self.config.last_youtube_url
        )
        if ok and url.strip():
            self.play_youtube_url_requested.emit(url.strip())

