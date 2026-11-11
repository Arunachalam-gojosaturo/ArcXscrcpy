"""
Hotspot Watcher for ARC-LINK.
Detects active Wi-Fi interfaces, default routes (hotspot gateway), SSIDs,
and signal levels dynamically without hardcoding interface names.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal


@dataclass(frozen=True)
class HotspotInfo:
    """Current Wi-Fi connection snapshot."""
    interface: str
    gateway: str
    ssid: str
    signal_pct: int
    bssid: str = ""

    @property
    def is_connected(self) -> bool:
        return bool(self.interface and self.gateway and self.gateway != "0.0.0.0")


class HotspotWatcherWorker(QThread):
    """
    Background polling worker monitoring system routing tables and Wi-Fi state.
    Emits hotspot_detected and hotspot_lost events.
    """
    hotspot_detected = pyqtSignal(str, str, str, int)  # interface, gateway, ssid, signal
    hotspot_lost = pyqtSignal(str)                     # interface

    def __init__(
        self,
        target_ssid: str = "",
        poll_interval: float = 2.0,
        interface_override: str = "",
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.target_ssid = target_ssid.strip()
        self.interface_override = interface_override.strip()
        self.poll_interval = poll_interval
        self._running = True
        self._last_state: Optional[HotspotInfo] = None

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def set_target_ssid(self, ssid: str) -> None:
        self.target_ssid = ssid.strip()

    def run(self) -> None:
        while self._running:
            current = self.detect_hotspot(self.interface_override)
            if current and current.is_connected:
                # If target_ssid is set, filter by SSID
                if self.target_ssid and self.target_ssid.lower() not in current.ssid.lower():
                    if self._last_state and self._last_state.is_connected:
                        self.hotspot_lost.emit(self._last_state.interface)
                        self._last_state = None
                else:
                    if (
                        self._last_state is None
                        or self._last_state.interface != current.interface
                        or self._last_state.gateway != current.gateway
                        or self._last_state.ssid != current.ssid
                        or abs(self._last_state.signal_pct - current.signal_pct) >= 10
                    ):
                        self._last_state = current
                        self.hotspot_detected.emit(
                            current.interface,
                            current.gateway,
                            current.ssid,
                            current.signal_pct,
                        )
            else:
                if self._last_state and self._last_state.is_connected:
                    self.hotspot_lost.emit(self._last_state.interface)
                    self._last_state = None

            steps = int(self.poll_interval / 0.25)
            for _ in range(max(1, steps)):
                if not self._running:
                    break
                time.sleep(0.25)

    @classmethod
    def detect_hotspot(cls, interface_override: str = "") -> Optional[HotspotInfo]:
        """Discovers active Wi-Fi interface and default gateway."""
        iface, gateway = cls._get_wifi_default_route(interface_override)
        if not iface or not gateway:
            return None

        ssid, signal, bssid = cls._get_wifi_details(iface)
        return HotspotInfo(
            interface=iface,
            gateway=gateway,
            ssid=ssid or "Wi-Fi Hotspot",
            signal_pct=signal,
            bssid=bssid,
        )

    @classmethod
    def _get_wifi_default_route(cls, override: str = "") -> Tuple[str, str]:
        if override:
            # Check gateway for specific interface
            try:
                out = subprocess.check_output(
                    ["ip", "route", "show", "default", "dev", override],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=1.5,
                )
                m = re.search(r"default via ([\d\.]+)", out)
                if m:
                    return override, m.group(1)
            except Exception:
                pass

        try:
            output = subprocess.check_output(
                ["ip", "route", "show", "default"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1.5,
            )
            for line in output.splitlines():
                if "default via" in line:
                    parts = line.split()
                    if "via" in parts and "dev" in parts:
                        via_idx = parts.index("via")
                        dev_idx = parts.index("dev")
                        gw = parts[via_idx + 1]
                        dev = parts[dev_idx + 1]
                        if cls._is_wireless_interface(dev):
                            return dev, gw
        except Exception:
            pass

        try:
            with open("/proc/net/route", "r") as f:
                for line in f.readlines()[1:]:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == "00000000":
                        iface = fields[0]
                        if cls._is_wireless_interface(iface):
                            gw_hex = fields[2]
                            gw_ip = ".".join(
                                str(int(gw_hex[i:i+2], 16))
                                for i in (6, 4, 2, 0)
                            )
                            return iface, gw_ip
        except Exception:
            pass

        return "", ""

    @classmethod
    def _is_wireless_interface(cls, iface: str) -> bool:
        if os.path.exists(f"/sys/class/net/{iface}/wireless") or os.path.exists(f"/sys/class/net/{iface}/phy80211"):
            return True
        return iface.startswith(("wl", "wlan", "wifi", "ath", "ra"))

    @classmethod
    def _get_wifi_details(cls, iface: str) -> Tuple[str, int, str]:
        if shutil.which("nmcli"):
            try:
                out = subprocess.check_output(
                    ["nmcli", "-t", "-f", "DEVICE,ACTIVE,SSID,SIGNAL,BSSID", "dev", "wifi"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2.0,
                )
                for line in out.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 4 and parts[1].lower() == "yes":
                        ssid = parts[2]
                        try:
                            signal = int(parts[3])
                        except ValueError:
                            signal = 75
                        bssid = ":".join(parts[4:]) if len(parts) > 4 else ""
                        return ssid, signal, bssid
            except Exception:
                pass

        if shutil.which("iw"):
            try:
                out = subprocess.check_output(
                    ["iw", "dev", iface, "link"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=1.5,
                )
                ssid = ""
                signal_pct = 70
                bssid = ""
                m_bssid = re.search(r"Connected to ([0-9a-fA-F:]{17})", out)
                if m_bssid:
                    bssid = m_bssid.group(1)
                m_ssid = re.search(r"SSID:\s*(.+)", out)
                if m_ssid:
                    ssid = m_ssid.group(1).strip()
                m_sig = re.search(r"signal:\s*(-?\d+)\s*dBm", out)
                if m_sig:
                    dbm = int(m_sig.group(1))
                    signal_pct = max(0, min(100, int(2 * (dbm + 100))))
                if ssid:
                    return ssid, signal_pct, bssid
            except Exception:
                pass

        return "Android Hotspot", 80, ""


class HotspotWatcher(QObject):
    """
    High-level controller and facade for hotspot tracking.
    """
    hotspot_connected = pyqtSignal(str, str, str)  # (interface, ssid, gateway)
    hotspot_disconnected = pyqtSignal(str)         # (interface)

    def __init__(
        self,
        interface_override: str = "",
        ssid_filter: Optional[List[str]] = None,
        poll_interval: float = 2.0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.interface_override = interface_override
        self.ssid_filter = ssid_filter or []
        self.current_interface: str = ""
        self.current_gateway: str = ""
        self.current_ssid: str = ""
        self.current_signal: int = 0

        self._worker = HotspotWatcherWorker(
            poll_interval=poll_interval,
            interface_override=interface_override,
        )
        self._worker.hotspot_detected.connect(self._on_hotspot_detected)
        self._worker.hotspot_lost.connect(self._on_hotspot_lost)

    @property
    def is_connected(self) -> bool:
        return bool(self.current_interface and self.current_gateway)

    def start(self) -> None:
        if not self._worker.isRunning():
            self._worker.start()

    def stop(self) -> None:
        if self._worker.isRunning():
            self._worker.stop()

    def _on_hotspot_detected(self, iface: str, gateway: str, ssid: str, signal: int) -> None:
        if self.ssid_filter and not any(f.lower() in ssid.lower() for f in self.ssid_filter):
            return

        self.current_interface = iface
        self.current_gateway = gateway
        self.current_ssid = ssid
        self.current_signal = signal
        self.hotspot_connected.emit(iface, ssid, gateway)

    def _on_hotspot_lost(self, iface: str) -> None:
        self.current_interface = ""
        self.current_gateway = ""
        self.current_ssid = ""
        self.current_signal = 0
        self.hotspot_disconnected.emit(iface)
