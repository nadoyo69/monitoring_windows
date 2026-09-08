"""
Taskbar Mini Bar Widget for Taskbar Hardware Monitor.
A frameless, translucent, always-on-top compact widget docked near the Windows taskbar.
"""
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QAction, QFont, QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QMenu, QApplication
)

from src.config import AppConfig
from src.sensor_manager import SystemMetrics
from src.utils import get_temp_color

class TaskbarWidget(QWidget):
    toggle_dashboard_requested = Signal()
    refresh_rate_changed = Signal(float)
    autorun_toggle_requested = Signal()
    exit_requested = Signal()

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._drag_pos = QPoint()
        self._is_dragging = False

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

    def _init_ui(self):
        self.setObjectName("TaskbarWidgetContainer")
        self.setFixedHeight(30)
        self.setFixedWidth(310)

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

        main_layout.addWidget(self.container)

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.18);")
        sep.setFixedHeight(14)
        return sep

    def _apply_initial_geometry(self):
        """Set initial position from config or dock to bottom-right near taskbar."""
        pos = self.config.get_window_pos()
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None

        if pos is not None:
            self.move(pos[0], pos[1])
        elif screen_geo:
            # Position just above the bottom taskbar on the right side
            target_x = screen_geo.x() + screen_geo.width() - self.width() - 20
            target_y = screen_geo.y() + screen_geo.height() - self.height() - 6
            self.move(target_x, target_y)

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
            self.move(new_pos)
            self._is_dragging = True
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                # Save new position
                self.config.set_window_pos(self.x(), self.y())
                self._is_dragging = False
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

        act_dashboard = menu.addAction("📊 Open Flyout Dashboard")
        act_dashboard.triggered.connect(lambda: self.toggle_dashboard_requested.emit())

        menu.addSeparator()

        act_lock = menu.addAction("🔒 Lock Position")
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

    def _set_refresh_rate(self, rate: float):
        self.config.refresh_interval = rate
        self.config.save()
        self.refresh_rate_changed.emit(rate)
