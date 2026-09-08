"""
Flyout Dashboard for Taskbar Hardware Monitor.
A modern fluent glassmorphism popup card showing deep metrics, sparkline graphs, and top processes.
"""
from typing import Deque
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QPushButton, QApplication
)

from src.sensor_manager import SystemMetrics
from src.utils import get_temp_color

class SparklineWidget(QWidget):
    """Custom micro-graph widget rendering a 60-second historical sparkline."""
    def __init__(self, color: str = "#38bdf8", max_val: float = 100.0, parent=None):
        super().__init__(parent)
        self.line_color = QColor(color)
        self.max_val = max_val
        self.data = []
        self.setFixedHeight(36)

    def set_data(self, history_deque: Deque):
        self.data = list(history_deque)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background grid line
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawLine(0, h - 1, w, h - 1)
        painter.drawLine(0, h // 2, w, h // 2)

        if len(self.data) < 2:
            return

        # Calculate points
        points = []
        step = w / max(1, len(self.data) - 1)
        for i, val in enumerate(self.data):
            x = i * step
            norm = min(1.0, max(0.0, val / self.max_val))
            y = h - (norm * (h - 6)) - 3
            points.append(QPoint(int(x), int(y)))

        # Draw line
        pen = QPen(self.line_color, 2)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

class FlyoutDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(360)
        self.setFixedHeight(450)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("FlyoutCard")
        self.card.setStyleSheet("""
            QFrame#FlyoutCard {
                background-color: rgba(15, 23, 42, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 12px;
            }
            QLabel {
                color: #f8fafc;
            }
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                color: transparent;
                height: 6px;
            }
            QProgressBar::chunk {
                border-radius: 3px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        # 1. Header
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("⚡ Hardware Monitor")
        title.setFont(QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")

        self.hardware_name = QLabel("Intel Core Ultra 7 155H")
        self.hardware_name.setFont(QFont("Segoe UI", 8))
        self.hardware_name.setStyleSheet("color: #94a3b8;")

        header_text.addWidget(title)
        header_text.addWidget(self.hardware_name)
        header_layout.addLayout(header_text)

        header_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ef4444;
                color: white;
            }
        """)
        btn_close.clicked.connect(self.hide)
        header_layout.addWidget(btn_close)

        card_layout.addLayout(header_layout)

        # 2. CPU Card
        cpu_box = self._create_card_frame()
        cpu_box_layout = QVBoxLayout(cpu_box)
        cpu_box_layout.setContentsMargins(10, 8, 10, 8)
        cpu_box_layout.setSpacing(4)

        cpu_head = QHBoxLayout()
        cpu_lbl = QLabel("CPU Utilization")
        cpu_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        cpu_lbl.setStyleSheet("color: #38bdf8;")
        self.cpu_stat_lbl = QLabel("0% | --°C")
        self.cpu_stat_lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        cpu_head.addWidget(cpu_lbl)
        cpu_head.addStretch()
        cpu_head.addWidget(self.cpu_stat_lbl)
        cpu_box_layout.addLayout(cpu_head)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #38bdf8; }")
        cpu_box_layout.addWidget(self.cpu_bar)

        self.cpu_sparkline = SparklineWidget(color="#38bdf8", max_val=100.0)
        cpu_box_layout.addWidget(self.cpu_sparkline)

        card_layout.addWidget(cpu_box)

        # 3. RAM Card
        ram_box = self._create_card_frame()
        ram_box_layout = QVBoxLayout(ram_box)
        ram_box_layout.setContentsMargins(10, 8, 10, 8)
        ram_box_layout.setSpacing(4)

        ram_head = QHBoxLayout()
        ram_lbl = QLabel("Memory (RAM)")
        ram_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        ram_lbl.setStyleSheet("color: #a855f7;")
        self.ram_stat_lbl = QLabel("0 GB / 0 GB (0%)")
        self.ram_stat_lbl.setFont(QFont("Consolas", 8))
        ram_head.addWidget(ram_lbl)
        ram_head.addStretch()
        ram_head.addWidget(self.ram_stat_lbl)
        ram_box_layout.addLayout(ram_head)

        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setStyleSheet("QProgressBar::chunk { background-color: #a855f7; }")
        ram_box_layout.addWidget(self.ram_bar)

        card_layout.addWidget(ram_box)

        # 4. Network Throughput Card
        net_box = self._create_card_frame()
        net_box_layout = QVBoxLayout(net_box)
        net_box_layout.setContentsMargins(10, 8, 10, 8)
        net_box_layout.setSpacing(4)

        net_head = QHBoxLayout()
        net_lbl = QLabel("Network Throughput")
        net_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        net_lbl.setStyleSheet("color: #10b981;")
        net_head.addWidget(net_lbl)
        net_head.addStretch()

        self.net_down_stat = QLabel("↓ 0 B/s")
        self.net_down_stat.setFont(QFont("Consolas", 8))
        self.net_down_stat.setStyleSheet("color: #34d399;")

        self.net_up_stat = QLabel("↑ 0 B/s")
        self.net_up_stat.setFont(QFont("Consolas", 8))
        self.net_up_stat.setStyleSheet("color: #38bdf8; margin-left: 8px;")

        net_head.addWidget(self.net_down_stat)
        net_head.addWidget(self.net_up_stat)
        net_box_layout.addLayout(net_head)

        card_layout.addWidget(net_box)

        # 5. Top Processes Card
        proc_box = self._create_card_frame()
        self.proc_layout = QVBoxLayout(proc_box)
        self.proc_layout.setContentsMargins(10, 8, 10, 8)
        self.proc_layout.setSpacing(3)

        proc_title = QLabel("Top Active Processes")
        proc_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        proc_title.setStyleSheet("color: #f59e0b;")
        self.proc_layout.addWidget(proc_title)

        self.proc_labels = []
        for _ in range(3):
            lbl = QLabel("-")
            lbl.setFont(QFont("Consolas", 7))
            lbl.setStyleSheet("color: #cbd5e1;")
            self.proc_layout.addWidget(lbl)
            self.proc_labels.append(lbl)

        card_layout.addWidget(proc_box)

        main_layout.addWidget(self.card)

    def _create_card_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(30, 41, 59, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        return frame

    def update_data(self, metrics: SystemMetrics, history_cpu: Deque):
        """Update dashboard UI with new metrics snapshot."""
        # CPU
        temp_str = f"{metrics.cpu_temp:.0f}°C" if metrics.cpu_temp is not None else "--°C"
        self.cpu_stat_lbl.setText(f"{metrics.cpu_percent:.0f}%  |  {temp_str}")
        if metrics.cpu_temp is not None:
            self.cpu_stat_lbl.setStyleSheet(f"color: {get_temp_color(metrics.cpu_temp)};")

        self.cpu_bar.setValue(int(metrics.cpu_percent))
        self.cpu_sparkline.set_data(history_cpu)

        # RAM
        self.ram_stat_lbl.setText(
            f"{metrics.ram_used_gb:.1f} GB / {metrics.ram_total_gb:.1f} GB ({int(metrics.ram_percent)}%)"
        )
        self.ram_bar.setValue(int(metrics.ram_percent))

        # Network
        self.net_down_stat.setText(f"↓ {metrics.net_download_str}")
        self.net_up_stat.setText(f"↑ {metrics.net_upload_str}")

        # Top processes
        for i, lbl in enumerate(self.proc_labels):
            if i < len(metrics.top_processes):
                p = metrics.top_processes[i]
                lbl.setText(f"{p['name'][:18]:<18} {p['cpu']:>4.1f}% CPU  {p['mem_mb']:>5.0f} MB")
            else:
                lbl.setText("")

    def toggle_at(self, target_point: QPoint):
        """Toggle visibility and position adjacent to the target anchor point."""
        if self.isVisible():
            self.hide()
        else:
            # Position above anchor point by default
            screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry() if screen else None

            target_x = target_point.x() - (self.width() // 2)
            target_y = target_point.y() - self.height() - 10

            # Screen bounds check
            if screen_geo:
                if target_x + self.width() > screen_geo.x() + screen_geo.width():
                    target_x = screen_geo.x() + screen_geo.width() - self.width() - 10
                if target_x < screen_geo.x():
                    target_x = screen_geo.x() + 10
                if target_y < screen_geo.y():
                    # Place below if no space above
                    target_y = target_point.y() + 40

            self.move(target_x, target_y)
            self.show()
            self.raise_()
            self.activateWindow()
