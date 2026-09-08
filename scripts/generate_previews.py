import sys
import os
sys.path.insert(0, os.path.abspath("."))
from collections import deque

from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPixmap, QLinearGradient
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QFrame

from src.config import AppConfig
from src.sensor_manager import SystemMetrics
from src.taskbar_widget import TaskbarWidget
from src.flyout_dashboard import FlyoutDashboard

def generate_screenshots():
    app = QApplication.instance() or QApplication(sys.argv)

    os.makedirs("assets", exist_ok=True)

    # 1. Prepare realistic dummy data
    history_cpu = deque([
        22, 24, 28, 35, 45, 52, 48, 40, 38, 36, 42, 55, 62, 58, 45,
        38, 34, 30, 28, 32, 40, 48, 52, 49, 42, 38, 35, 34, 38, 42,
        45, 48, 50, 46, 42, 38, 35, 36, 38, 40, 45, 48, 52, 50, 44,
        38, 35, 36, 38, 42, 45, 48, 46, 42, 39, 36, 35, 37, 38, 38
    ], maxlen=60)

    metrics = SystemMetrics(
        cpu_percent=38.0,
        cpu_temp=54.0,
        cpu_temp_status="ok",
        ram_percent=58.0,
        ram_used_gb=18.6,
        ram_total_gb=32.0,
        net_download_bps=3800000.0,
        net_upload_bps=420000.0,
        net_download_str="3.8 MB/s",
        net_upload_str="420 KB/s",
        top_processes=[
            {"name": "chrome.exe", "cpu": 12.4, "mem_mb": 1420.0},
            {"name": "Code.exe", "cpu": 8.2, "mem_mb": 860.0},
            {"name": "pythonw.exe", "cpu": 4.5, "mem_mb": 42.0},
        ]
    )

    # 2. Render Flyout Dashboard
    dashboard = FlyoutDashboard()
    dashboard.update_data(metrics, history_cpu)
    dashboard.show()
    app.processEvents()

    # Grab the dashboard card
    dashboard_pixmap = dashboard.grab()
    dashboard_pixmap.save("assets/flyout_dashboard_preview.png", "PNG")
    print("Saved assets/flyout_dashboard_preview.png")

    # 3. Render Taskbar Widget alone
    config = AppConfig()
    widget = TaskbarWidget(config)
    widget.update_metrics(metrics)
    widget.show()
    app.processEvents()

    widget_pixmap = widget.grab()
    widget_pixmap.save("assets/taskbar_widget_alone.png", "PNG")
    print("Saved assets/taskbar_widget_alone.png")

    # 4. Render Windows 11 Taskbar Context Mockup
    tb_width = 960
    tb_height = 52
    canvas = QPixmap(tb_width, tb_height)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background taskbar acrylic glass
    painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
    painter.setBrush(QBrush(QColor(15, 23, 42, 235)))
    painter.drawRoundedRect(0, 0, tb_width, tb_height, 8, 8)

    # Left: Windows 11 Start & Search icons simulation
    painter.setPen(Qt.PenStyle.NoPen)
    # Win logo 4 squares
    colors = [QColor("#00adef"), QColor("#00adef"), QColor("#00adef"), QColor("#00adef")]
    coords = [(20, 18), (30, 18), (20, 28), (30, 28)]
    for color, (x, y) in zip(colors, coords):
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(x, y, 8, 8, 1, 1)

    # Search pill
    painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
    painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
    painter.drawRoundedRect(48, 13, 130, 26, 13, 13)
    painter.setPen(QColor("#94a3b8"))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(60, 30, "🔍 Search")

    # App icons simulation (Explorer, Edge, VS Code, Terminal)
    app_colors = [QColor("#eab308"), QColor("#0ea5e9"), QColor("#3b82f6"), QColor("#10b981")]
    for i, ac in enumerate(app_colors):
        px = 195 + (i * 34)
        painter.setBrush(QBrush(ac))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(px, 14, 24, 24, 6, 6)

    # Place Taskbar Widget at center-right
    widget_x = 450
    widget_y = 11
    painter.drawPixmap(widget_x, widget_y, widget_pixmap)

    # Right side: System tray icons + Clock
    tray_x = 780
    painter.setPen(QColor("#94a3b8"))
    painter.setFont(QFont("Segoe UI", 8))
    painter.drawText(tray_x, 31, "ENG")
    painter.drawText(tray_x + 36, 31, "📶 🔊")

    # Clock
    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
    painter.setPen(QColor("#f8fafc"))
    painter.drawText(tb_width - 78, 24, "10:42 AM")
    painter.setFont(QFont("Segoe UI", 7))
    painter.setPen(QColor("#94a3b8"))
    painter.drawText(tb_width - 78, 38, "9/8/2026")

    painter.end()
    canvas.save("assets/taskbar_widget_preview.png", "PNG")
    print("Saved assets/taskbar_widget_preview.png")

    # 5. Render Combined Full Interactive Experience
    comp_w = 1000
    comp_h = 570
    comp = QPixmap(comp_w, comp_h)
    comp.fill(Qt.GlobalColor.transparent)

    p2 = QPainter(comp)
    p2.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Desktop wallpaper gradient background
    grad = QLinearGradient(0, 0, comp_w, comp_h)
    grad.setColorAt(0.0, QColor("#090d16"))
    grad.setColorAt(0.5, QColor("#0f172a"))
    grad.setColorAt(1.0, QColor("#1e1b4b"))
    p2.fillRect(0, 0, comp_w, comp_h, grad)

    # Subtle desktop glow
    p2.setBrush(QBrush(QColor(56, 189, 248, 18)))
    p2.setPen(Qt.PenStyle.NoPen)
    p2.drawEllipse(380, 80, 450, 320)

    # Draw Flyout Dashboard anchored directly above widget
    tb_draw_x = 20
    tb_draw_y = comp_h - tb_height - 14

    dash_x = tb_draw_x + widget_x - 20
    dash_y = tb_draw_y - dashboard_pixmap.height() - 12

    # Dashboard subtle drop shadow
    p2.setBrush(QBrush(QColor(0, 0, 0, 140)))
    p2.drawRoundedRect(dash_x - 6, dash_y - 6, dashboard_pixmap.width() + 12, dashboard_pixmap.height() + 12, 16, 16)

    p2.drawPixmap(dash_x, dash_y, dashboard_pixmap)

    # Draw Taskbar along bottom
    p2.drawPixmap(tb_draw_x, tb_draw_y, canvas)

    p2.end()
    comp.save("assets/full_showcase_preview.png", "PNG")
    print("Saved assets/full_showcase_preview.png")

    dashboard.close()
    widget.close()

if __name__ == "__main__":
    generate_screenshots()
