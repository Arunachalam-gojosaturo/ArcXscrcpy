"""
Device Discovery Engine for ARC-LINK.
Locates the Android wireless debugging port via UDP knock handshakes,
mDNS discovery services, and cached fallback endpoints.
"""

from __future__ import annotations

import re
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from arc_link.core.config import AppConfig, ArcConfig, load_config
from arc_link.core.knock import KnockClient, KnockError, KnockReply, KnockResult, send_knock


@dataclass(frozen=True)
class DiscoveredTarget:
    """Discovered network target ready for ADB connection."""
    ip: str
    port: int
    source: str          # "KNOCK", "MDNS", "SAVED", "PORT_SCAN"
    device_name: str
    model: str
    battery: int = -1

    @property
    def endpoint(self) -> str:
        return f"{self.ip}:{self.port}"


class DiscoveryEngine:
    """Orchestrates multi-strategy resolution of the Android target."""

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None) -> None:
        self.log = log_callback or (lambda msg, lvl: None)

    def discover(
        self,
        gateway_ip: str,
        config: AppConfig | ArcConfig,
    ) -> Optional[DiscoveredTarget]:
        """
        Executes discovery in order:
        1. UDP Knock to gateway:knock_port (contains exact dynamic port).
        2. mDNS discovery via `adb mdns services`.
        3. Saved endpoint verification.
        4. Gateway fallback scan (common ADB port 5555).
        """
        # Strategy 1: UDP Knock (Fastest & Canonical)
        knock_port = getattr(config, "knock_port", None) or getattr(getattr(config, "network", None), "knock_port", 9099)
        secret = getattr(config, "secret", None) or getattr(getattr(config, "auth", None), "shared_secret", "")

        if gateway_ip and gateway_ip != "0.0.0.0":
            self.log(f"Initiating UDP knock on gateway {gateway_ip}:{knock_port}...", "DEBUG")
            try:
                knock_client = KnockClient(port=knock_port, timeout=2.0)
                reply = knock_client.knock(gateway_ip, secret)
                if reply and reply.adb_port:
                    self.log(
                        f"Knock acknowledged by {reply.device_name} ({reply.model}). Target port: {reply.adb_port}",
                        "SUCCESS",
                    )
                    # Determine target IP address:
                    # Prefer responder_ip (the network address from which the UDP reply actually arrived)
                    # or gateway_ip over payload reply.ip, because the host has proven network reachability to it.
                    target_ip = reply.responder_ip or gateway_ip
                    if not target_ip or target_ip == "0.0.0.0":
                        target_ip = reply.ip or gateway_ip

                    if reply.ip and reply.ip != target_ip:
                        self.log(
                            f"Knock reply payload IP '{reply.ip}' differs from active responder '{target_ip}'. "
                            f"Routing to responsive endpoint {target_ip}:{reply.adb_port}.",
                            "INFO",
                        )

                    return DiscoveredTarget(
                        ip=target_ip,
                        port=reply.adb_port,
                        source="KNOCK",
                        device_name=reply.device_name,
                        model=reply.model,
                        battery=reply.battery,
                    )
            except Exception as e:
                self.log(f"UDP Knock attempt failed: {e}", "DEBUG")

        # Strategy 2: mDNS Resolution via adb mdns services
        self.log("Querying ADB mDNS services...", "DEBUG")
        mdns_target = self._discover_mdns(gateway_ip)
        if mdns_target:
            self.log(f"Target located via mDNS: {mdns_target.endpoint}", "SUCCESS")
            return mdns_target

        # Strategy 3: Saved Endpoint from Config
        saved_endpoint = getattr(config, "saved_endpoint", "") or ""
        if saved_endpoint and ":" in saved_endpoint:
            self.log(f"Evaluating saved fallback endpoint: {saved_endpoint}", "DEBUG")
            try:
                saved_ip, saved_port_str = saved_endpoint.split(":", 1)
                saved_port = int(saved_port_str)
                if self._check_tcp_port(saved_ip, saved_port, timeout=1.0):
                    self.log(f"Saved endpoint {saved_endpoint} is responsive", "INFO")
                    return DiscoveredTarget(
                        ip=saved_ip,
                        port=saved_port,
                        source="SAVED",
                        device_name="Saved Target",
                        model="Cached Device",
                    )
            except Exception as e:
                self.log(f"Saved endpoint check error: {e}", "DEBUG")

        # Strategy 4: Gateway Fallback (Standard ADB port 5555)
        default_port = getattr(getattr(config, "network", None), "default_adb_port", 5555)
        if gateway_ip and gateway_ip != "0.0.0.0":
            self.log(f"Testing default ADB port {default_port} on gateway {gateway_ip}...", "DEBUG")
            if self._check_tcp_port(gateway_ip, default_port, timeout=1.2):
                self.log(f"Gateway {gateway_ip}:{default_port} is open", "SUCCESS")
                return DiscoveredTarget(
                    ip=gateway_ip,
                    port=default_port,
                    source="PORT_SCAN",
                    device_name="Android Gateway",
                    model="Generic",
                )

        self.log("Discovery completed with no active targets located.", "WARN")
        return None

    def _discover_mdns(self, expected_ip: Optional[str] = None) -> Optional[DiscoveredTarget]:
        """Runs `adb mdns services` and parses `_adb-tls-connect._tcp`."""
        adb_bin = shutil.which("adb") or "adb"
        try:
            res = subprocess.run(
                [adb_bin, "mdns", "services"],
                capture_output=True,
                text=True,
                timeout=2.5,
            )
            lines = res.stdout.splitlines()
            for line in lines:
                if "_adb-tls-connect._tcp" in line or "_adb._tcp" in line:
                    match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)", line)
                    if match:
                        ip = match.group(1)
                        port = int(match.group(2))
                        if not expected_ip or ip == expected_ip:
                            return DiscoveredTarget(
                                ip=ip,
                                port=port,
                                source="MDNS",
                                device_name="mDNS Device",
                                model="Wireless Debugging",
                            )
        except Exception:
            pass
        return None

    @staticmethod
    def _check_tcp_port(ip: str, port: int, timeout: float = 1.0) -> bool:
        """Simple TCP connect check to see if port is open."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((ip, port))
            return result == 0
        except socket.error:
            return False
        finally:
            sock.close()


class DeviceDiscoveryWorker(QThread):
    """
    QThread worker executing discovery and connection steps asynchronously.
    """
    step_progress = pyqtSignal(str)
    endpoint_found = pyqtSignal(str, dict)
    discovery_failed = pyqtSignal(str)

    def __init__(
        self,
        shared_secret: str,
        gateway_ip: str,
        knock_port: int = 9099,
        default_adb_port: int = 5555,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.shared_secret = shared_secret
        self.gateway_ip = gateway_ip
        self.knock_port = knock_port
        self.default_adb_port = default_adb_port
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
        self.wait(1500)

    def run(self) -> None:
        engine = DiscoveryEngine(log_callback=lambda msg, lvl: self.step_progress.emit(msg))

        if not self.gateway_ip:
            # Fallback auto-detect default gateway via `ip route`
            try:
                out = subprocess.check_output(["ip", "route", "show", "default"], text=True)
                m = re.search(r"default via ([\d\.]+)", out)
                if m:
                    self.gateway_ip = m.group(1)
            except Exception:
                self.gateway_ip = "192.168.43.1"

        self.step_progress.emit(f"Knocking on gateway {self.gateway_ip}:{self.knock_port}...")

        cfg = load_config()
        cfg.auth.shared_secret = self.shared_secret
        cfg.network.knock_port = self.knock_port
        cfg.network.default_adb_port = self.default_adb_port

        target = engine.discover(self.gateway_ip, cfg)
        if not self._is_running:
            return

        if not target:
            self.discovery_failed.emit(f"No responding Android target on {self.gateway_ip}")
            return

        endpoint = target.endpoint
        self.step_progress.emit(f"Connecting to ADB endpoint {endpoint}...")

        # Run adb connect
        adb_bin = shutil.which("adb") or "adb"
        try:
            res = subprocess.run([adb_bin, "connect", endpoint], capture_output=True, text=True, timeout=5.0)
            out = res.stdout + res.stderr
            if "connected to" in out.lower():
                details = {
                    "device_name": target.device_name,
                    "model": target.model,
                    "ip": target.ip,
                    "port": target.port,
                    "endpoint": endpoint,
                    "battery_level": target.battery,
                }
                self.endpoint_found.emit(endpoint, details)
            elif self.gateway_ip and self.gateway_ip != target.ip and self.gateway_ip != "0.0.0.0":
                # Fallback attempt to gateway_ip if target.ip failed
                gw_endpoint = f"{self.gateway_ip}:{target.port}"
                self.step_progress.emit(f"Retrying connection with gateway endpoint {gw_endpoint}...")
                res_gw = subprocess.run([adb_bin, "connect", gw_endpoint], capture_output=True, text=True, timeout=5.0)
                out_gw = res_gw.stdout + res_gw.stderr
                if "connected to" in out_gw.lower():
                    details = {
                        "device_name": target.device_name,
                        "model": target.model,
                        "ip": self.gateway_ip,
                        "port": target.port,
                        "endpoint": gw_endpoint,
                        "battery_level": target.battery,
                    }
                    self.endpoint_found.emit(gw_endpoint, details)
                else:
                    self.discovery_failed.emit(f"ADB Connect rejected: {out.strip()} / {out_gw.strip()}")
            else:
                self.discovery_failed.emit(f"ADB Connect rejected: {out.strip()}")
        except Exception as e:
            self.discovery_failed.emit(f"Failed to execute adb connect: {e}")
