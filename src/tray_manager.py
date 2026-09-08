"""
System Tray Manager for Taskbar Hardware Monitor.
Provides an icon in the Windows notification area with menu and flyout integration.
"""
from PySide6.QtCore import Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from src.config import AppConfig
from src.sensor_manager import SystemMetrics

def create_default_tray_icon() -> QIcon:
    """Dynamically generate a sleek hardware monitor tray icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Rounded background
    painter.setBrush(QColor(15, 23, 42))
    painter.setPen(QColor(56, 189, 248))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

    # Activity bars
    painter.setPen(QColor(0, 0, 0, 0))
    # Bar 1 (cyan)
    painter.setBrush(QColor(56, 189, 248))
    painter.drawRect(7, 14, 4, 11)
    # Bar 2 (purple)
    painter.setBrush(QColor(168, 85, 247))
    painter.drawRect(14, 8, 4, 17)
    # Bar 3 (emerald)
    painter.setBrush(QColor(16, 185, 129))
    painter.drawRect(21, 11, 4, 14)

    painter.end()
    return QIcon(pixmap)

class TrayManager(QSystemTrayIcon):
    toggle_widget_requested = Signal(bool)
    toggle_dashboard_requested = Signal()
    autorun_toggle_requested = Signal()
    exit_requested = Signal()

    def __init__(self, config: AppConfig, icon: QIcon = None, parent=None):
        tray_icon = icon or create_default_tray_icon()
        super().__init__(tray_icon, parent)
        self.config = config
        self.setToolTip("Taskbar Hardware Monitor\nMemulai...")

        self._init_menu()
        self.activated.connect(self._on_activated)

    def _init_menu(self):
        menu = QMenu()
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

        act_dash = menu.addAction("📊 Open Dashboard")
        act_dash.triggered.connect(lambda: self.toggle_dashboard_requested.emit())

        menu.addSeparator()

        self.act_show_widget = menu.addAction("📌 Show Taskbar Bar")
        self.act_show_widget.setCheckable(True)
        self.act_show_widget.setChecked(self.config.show_taskbar_widget)
        self.act_show_widget.toggled.connect(self._on_widget_toggled)

        self.act_autorun = menu.addAction("🚀 Start on Windows Boot")
        self.act_autorun.setCheckable(True)
        self.act_autorun.setChecked(self.config.autorun_enabled)
        self.act_autorun.triggered.connect(lambda: self.autorun_toggle_requested.emit())

        menu.addSeparator()

        act_exit = menu.addAction("❌ Exit")
        act_exit.triggered.connect(lambda: self.exit_requested.emit())

        self.setContextMenu(menu)

    def _on_widget_toggled(self, checked: bool):
        self.config.show_taskbar_widget = checked
        self.config.save()
        self.toggle_widget_requested.emit(checked)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_dashboard_requested.emit()

    def update_metrics(self, m: SystemMetrics):
        temp_str = f"{m.cpu_temp:.0f}°C" if m.cpu_temp is not None else "--°C"
        tip = (
            f"Hardware Monitor\n"
            f"CPU: {m.cpu_percent:.0f}% ({temp_str})\n"
            f"RAM: {m.ram_used_gb:.1f}/{m.ram_total_gb:.1f} GB ({m.ram_percent:.0f}%)\n"
            f"Net: ↓{m.net_download_str} ↑{m.net_upload_str}"
        )
        self.setToolTip(tip)
