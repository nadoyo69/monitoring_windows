"""
Sensor Manager for Taskbar Hardware Monitor.
Samples CPU usage, temperature, RAM, network throughput, and top processes asynchronously.
"""
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

import psutil
from PySide6.QtCore import QThread, Signal

from src.utils import is_admin, format_speed, format_bytes

@dataclass
class SystemMetrics:
    cpu_percent: float = 0.0
    cpu_temp: Optional[float] = None
    cpu_temp_status: str = "needs_admin"  # "ok", "needs_admin", "unsupported", "error"
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    net_download_bps: float = 0.0
    net_upload_bps: float = 0.0
    net_download_str: str = "0 B/s"
    net_upload_str: str = "0 B/s"
    top_processes: List[Dict] = field(default_factory=list)

class SensorWorker(QThread):
    metrics_ready = Signal(object)  # Emits SystemMetrics instance

    def __init__(self, interval: float = 1.0, parent=None):
        super().__init__(parent)
        self.interval = interval
        self._running = True
        self.has_admin = is_admin()

        # Network calculation state
        self.last_net_bytes: Optional[Tuple[int, int]] = None  # (recv, sent)
        self.last_sample_time: float = 0.0

        # Circular buffers for 60 seconds history
        self.history_cpu = deque(maxlen=60)
        self.history_temp = deque(maxlen=60)
        self.history_ram = deque(maxlen=60)
        self.history_net_down = deque(maxlen=60)
        self.history_net_up = deque(maxlen=60)

        # Hardware monitor instance (LibreHardwareMonitorLib)
        self._hardware_computer = None
        self._init_hardware_monitor()

        # Prime psutil CPU counter
        psutil.cpu_percent(interval=None)

    def _init_hardware_monitor(self):
        """Initialize LibreHardwareMonitorLib for hardware temperature sensor access."""
        try:
            dll_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
            dll_path = os.path.join(dll_dir, "LibreHardwareMonitorLib.dll")
            if os.path.exists(dll_path):
                import sys
                if dll_dir not in sys.path:
                    sys.path.append(dll_dir)
                import clr
                clr.AddReference(dll_path)
                from LibreHardwareMonitor.Hardware import Computer
                comp = Computer()
                comp.IsCpuEnabled = True
                comp.Open()
                self._hardware_computer = comp
        except Exception:
            self._hardware_computer = None

    def _read_cpu_temperature(self) -> Tuple[Optional[float], str]:
        """Read CPU temperature via LibreHardwareMonitorLib or ACPI WMI fallback."""
        # Try LibreHardwareMonitor if initialized
        if self._hardware_computer:
            try:
                for hardware in self._hardware_computer.Hardware:
                    hardware.Update()
                    package_temp = None
                    core_temps = []
                    for sensor in hardware.Sensors:
                        if str(sensor.SensorType) == "Temperature":
                            val = sensor.Value
                            if val is not None and float(val) > 0:
                                name_lower = sensor.Name.lower()
                                if "package" in name_lower or "cpu total" in name_lower or "core max" in name_lower:
                                    package_temp = float(val)
                                elif "core" in name_lower:
                                    core_temps.append(float(val))

                    if package_temp is not None:
                        return package_temp, "ok"
                    elif core_temps:
                        return sum(core_temps) / len(core_temps), "ok"
            except Exception:
                pass

        # Fallback to WMI ACPI if possible
        try:
            import wmi
            w = wmi.WMI(namespace="root/wmi")
            thermal = w.MSAcpi_ThermalZoneTemperature()
            if thermal:
                temp_c = (thermal[0].CurrentTemperature - 2732) / 10.0
                if 20.0 <= temp_c <= 120.0:
                    return temp_c, "ok"
        except Exception:
            pass

        if not self.has_admin:
            return None, "needs_admin"
        return None, "unsupported"

    def _calc_net_rates(self, bytes_recv: int, bytes_sent: int, current_time: float) -> Tuple[float, float]:
        """Calculate upload and download throughput in bytes per second."""
        if self.last_net_bytes is None or self.last_sample_time == 0.0:
            self.last_net_bytes = (bytes_recv, bytes_sent)
            self.last_sample_time = current_time
            return 0.0, 0.0

        dt = current_time - self.last_sample_time
        if dt <= 0.0:
            return 0.0, 0.0

        last_recv, last_sent = self.last_net_bytes

        # If bytes count decreased (e.g. adapter reset/reconnected), reset baseline
        if bytes_recv < last_recv or bytes_sent < last_sent:
            self.last_net_bytes = (bytes_recv, bytes_sent)
            self.last_sample_time = current_time
            return 0.0, 0.0

        down_rate = (bytes_recv - last_recv) / dt
        up_rate = (bytes_sent - last_sent) / dt

        self.last_net_bytes = (bytes_recv, bytes_sent)
        self.last_sample_time = current_time
        return down_rate, up_rate

    def _get_top_processes(self, limit: int = 3) -> List[Dict]:
        """Fetch top CPU-consuming processes safely."""
        procs = []
        try:
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                try:
                    info = p.info
                    name = info.get('name') or "Unknown"
                    cpu = info.get('cpu_percent') or 0.0
                    mem_info = info.get('memory_info')
                    mem_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
                    # Filter out idle process
                    if name.lower() not in ("system idle process", "idle"):
                        procs.append({"name": name, "cpu": cpu, "mem_mb": mem_mb})
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Sort descending by CPU
            procs.sort(key=lambda x: x['cpu'], reverse=True)
            return procs[:limit]
        except Exception:
            return []

    def sample_metrics(self) -> SystemMetrics:
        """Sample all hardware and system metrics synchronously."""
        now = time.time()

        # CPU Usage
        cpu_pct = psutil.cpu_percent(interval=None)

        # CPU Temperature
        temp_val, temp_status = self._read_cpu_temperature()

        # Memory (RAM)
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_used_gb = mem.used / (1024 * 1024 * 1024)
        ram_total_gb = mem.total / (1024 * 1024 * 1024)

        # Network
        net = psutil.net_io_counters()
        down_rate, up_rate = self._calc_net_rates(net.bytes_recv, net.bytes_sent, now)

        # Top processes
        top_procs = self._get_top_processes(limit=3)

        # Record history for graphs
        self.history_cpu.append(cpu_pct)
        if temp_val is not None:
            self.history_temp.append(temp_val)
        self.history_ram.append(ram_pct)
        self.history_net_down.append(down_rate)
        self.history_net_up.append(up_rate)

        return SystemMetrics(
            cpu_percent=cpu_pct,
            cpu_temp=temp_val,
            cpu_temp_status=temp_status,
            ram_percent=ram_pct,
            ram_used_gb=ram_used_gb,
            ram_total_gb=ram_total_gb,
            net_download_bps=down_rate,
            net_upload_bps=up_rate,
            net_download_str=format_speed(down_rate),
            net_upload_str=format_speed(up_rate),
            top_processes=top_procs
        )

    def run(self):
        """Worker thread loop."""
        while self._running:
            metrics = self.sample_metrics()
            self.metrics_ready.emit(metrics)
            # Sleep in small increments for responsive stop
            sleep_chunks = int(self.interval / 0.1)
            for _ in range(max(1, sleep_chunks)):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self):
        """Stop worker loop and cleanup hardware monitor."""
        self._running = False
        self.wait(2000)
        if self._hardware_computer:
            try:
                self._hardware_computer.Close()
            except Exception:
                pass
            self._hardware_computer = None
