"""
ADB Manager for ARC-LINK.
Wraps the `adb` executable for connection handshake, state verification,
and telemetry polling without fragile grep pipelines.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from arc_link.core.state import DeviceInfo


class AdbError(Exception):
    """Raised when ADB commands fail or device state is invalid."""
    pass


class AdbUnauthorizedError(AdbError):
    """Raised when the laptop is not RSA authorized on the Android device."""
    pass


class AdbOfflineError(AdbError):
    """Raised when the Android device is in offline state."""
    pass


class AdbManager:
    """Manages adb daemon interactions, connection status, and device metadata queries."""

    def __init__(self, adb_path: Optional[str] = None) -> None:
        self.adb_bin = adb_path or shutil.which("adb") or "adb"

    def get_version(self) -> str:
        """Returns the installed ADB version string."""
        try:
            out = subprocess.check_output(
                [self.adb_bin, "version"],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=2.0,
            )
            match = re.search(r"Android Debug Bridge version ([\d\.]+)", out)
            if match:
                return f"ADB v{match.group(1)}"
            return out.splitlines()[0] if out else "ADB Available"
        except Exception as e:
            return f"ADB Unavailable ({e})"

    def connect(self, endpoint: str, timeout: float = 4.0) -> Tuple[bool, str]:
        """
        Executes `adb connect IP:PORT`.
        Returns (success: bool, raw_message: str).
        """
        try:
            res = subprocess.run(
                [self.adb_bin, "connect", endpoint],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (res.stdout + res.stderr).strip()
            if "connected to" in output.lower():
                return True, output
            return False, output or "Unknown adb connect response"
        except subprocess.TimeoutExpired:
            return False, f"Connection to {endpoint} timed out after {timeout}s"
        except Exception as e:
            return False, f"Failed to execute adb connect: {e}"

    def get_state(self, endpoint: str, timeout: float = 3.0) -> str:
        """
        Executes `adb -s <endpoint> get-state`.
        Returns: 'device', 'offline', 'unauthorized', or raises AdbError.
        Notice: Never pipes through grep -q; strictly parses direct output.
        """
        try:
            res = subprocess.run(
                [self.adb_bin, "-s", endpoint, "get-state"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = res.stdout.strip().lower()
            stderr = res.stderr.strip().lower()

            if "device" in stdout:
                return "device"
            if "unauthorized" in stderr or "unauthorized" in stdout:
                raise AdbUnauthorizedError(
                    f"Device {endpoint} is unauthorized. RSA key confirmation required on device."
                )
            if "offline" in stderr or "offline" in stdout:
                raise AdbOfflineError(f"Device {endpoint} reported offline.")
            if res.returncode != 0:
                raise AdbError(f"ADB get-state failed (code {res.returncode}): {stderr or stdout}")
            return stdout or "unknown"
        except subprocess.TimeoutExpired:
            raise AdbError(f"get-state timed out on {endpoint}")

    def get_device_state(self, endpoint: str) -> str:
        """Safe wrapper around get_state returning string state."""
        try:
            return self.get_state(endpoint)
        except Exception as e:
            err_str = str(e).lower()
            if "unauthorized" in err_str:
                return "unauthorized"
            return "offline"

    def verify_connected(self, endpoint: str) -> bool:
        """Returns True if the target device is actively authorized and ready."""
        try:
            return self.get_state(endpoint) == "device"
        except Exception:
            return False

    def disconnect(self, endpoint: str, timeout: float = 3.0) -> bool:
        """Executes `adb disconnect <endpoint>`."""
        try:
            subprocess.run(
                [self.adb_bin, "disconnect", endpoint],
                capture_output=True,
                timeout=timeout,
            )
            return True
        except Exception:
            return False

    def pair(self, ip: str, port: int, pairing_code: str, timeout: float = 8.0) -> Tuple[bool, str]:
        """Executes `adb pair IP:PORT CODE`."""
        endpoint = f"{ip}:{port}"
        try:
            proc = subprocess.Popen(
                [self.adb_bin, "pair", endpoint, pairing_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            out, err = proc.communicate(timeout=timeout)
            combined = (out + err).strip()
            if "successfully paired" in combined.lower():
                return True, combined
            return False, combined or "Pairing failed"
        except Exception as e:
            return False, str(e)

    def fetch_device_info(self, ip: str, port: int) -> DeviceInfo:
        """
        Gathers live device specifications and telemetry from the connected device.
        """
        endpoint = f"{ip}:{port}"
        import time
        now = time.time()

        # 1. Device Name
        device_name = self._run_shell(endpoint, "settings get global device_name")
        if not device_name or device_name == "null":
            device_name = self._run_shell(endpoint, "getprop ro.product.model") or "Android Device"

        # 2. Model & Manufacturer & Android Release
        model = self._run_shell(endpoint, "getprop ro.product.model") or "Generic Model"
        manufacturer = self._run_shell(endpoint, "getprop ro.product.manufacturer") or "Unknown"
        android_ver = self._run_shell(endpoint, "getprop ro.build.version.release") or "Android"

        # 3. Battery statistics
        battery_out = self._run_shell(endpoint, "dumpsys battery")
        battery_pct = -1
        is_charging = False
        if battery_out:
            m_level = re.search(r"level:\s*(\d+)", battery_out)
            if m_level:
                battery_pct = int(m_level.group(1))
            m_status = re.search(r"status:\s*(\d+)", battery_out)
            if m_status:
                is_charging = m_status.group(1) in ("2", "5")
            if not is_charging:
                m_ac = re.search(r"(AC powered|USB powered|Wireless powered):\s*true", battery_out)
                if m_ac:
                    is_charging = True

        # 4. Storage
        storage_free = "N/A"
        df_out = self._run_shell(endpoint, "df -h /data")
        if df_out:
            lines = df_out.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 4:
                    storage_free = f"{parts[3]} free ({parts[1]} total)"

        # 5. Uptime
        uptime_out = self._run_shell(endpoint, "uptime")
        uptime_str = uptime_out.strip() if uptime_out else "Active"
        m_up = re.search(r"up\s+([^,]+(?:,\s*[^,]+)?)", uptime_str)
        if m_up:
            uptime_str = m_up.group(0)

        return DeviceInfo(
            device_name=device_name,
            model=model,
            manufacturer=manufacturer.capitalize(),
            android_version=f"Android {android_ver}",
            ip=ip,
            port=port,
            battery_level=battery_pct,
            is_charging=is_charging,
            storage_free=storage_free,
            uptime=uptime_str,
            last_seen=now,
        )

    def get_device_telemetry(self, endpoint: str) -> Dict[str, Any]:
        """Convenience method returning telemetry dictionary for endpoint."""
        if ":" in endpoint:
            ip, port_str = endpoint.split(":", 1)
            port = int(port_str)
        else:
            ip, port = endpoint, 5555

        info = self.fetch_device_info(ip, port)
        return {
            "device_name": info.device_name,
            "model": info.model,
            "manufacturer": info.manufacturer,
            "android_version": info.android_version,
            "endpoint": endpoint,
            "ip": ip,
            "port": port,
            "battery_level": info.battery_level,
            "is_charging": info.is_charging,
            "storage_free": info.storage_free,
            "uptime": info.uptime,
        }

    def _run_shell(self, endpoint: str, cmd: str, timeout: float = 3.0) -> str:
        """Executes a command via `adb -s <endpoint> shell <cmd>` safely."""
        try:
            res = subprocess.run(
                [self.adb_bin, "-s", endpoint, "shell", cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return ""


# Alias AdbDeviceManager for compatibility
AdbDeviceManager = AdbManager
