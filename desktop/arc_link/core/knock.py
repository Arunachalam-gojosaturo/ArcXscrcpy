"""
UDP Knock Client for ARC-LINK.
Transmits the shared secret to the Android companion listener and parses
the device handshake metadata.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any, Dict, Optional


class KnockError(Exception):
    """Base exception for knock exchange failures."""
    pass


class KnockTimeoutError(KnockError):
    """Raised when the Android device fails to respond within timeout."""
    pass


class KnockInvalidResponseError(KnockError):
    """Raised when the response payload is malformed or invalid."""
    pass


@dataclass(frozen=True)
class KnockResult:
    """Parsed handshake response from the Android companion app."""
    device_name: str
    model: str
    ip: str
    adb_port: int
    adb_wifi_enabled: bool
    hotspot: bool
    battery: int
    raw_payload: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], raw: str = "") -> KnockResult:
        return cls(
            device_name=str(data.get("device_name", data.get("model", "Android Device"))),
            model=str(data.get("model", "Unknown")),
            ip=str(data.get("ip", "")),
            adb_port=int(data.get("adb_port", 0)),
            adb_wifi_enabled=bool(data.get("adb_wifi_enabled", False)),
            hotspot=bool(data.get("hotspot", True)),
            battery=int(data.get("battery", -1)),
            raw_payload=raw,
        )

    @classmethod
    def from_json(cls, raw: str) -> KnockResult:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise KnockInvalidResponseError(f"Malformed JSON response: {e}") from e

        required_keys = {"ip", "adb_port", "adb_wifi_enabled"}
        missing = required_keys - set(data.keys())
        if missing:
            raise KnockInvalidResponseError(f"Missing required keys in reply: {missing}")

        return cls.from_dict(data, raw=raw)


# Alias KnockReply to KnockResult
KnockReply = KnockResult


def send_knock(
    gateway_ip: str,
    secret: str,
    port: int = 9099,
    timeout: float = 2.0,
    retries: int = 2,
) -> KnockResult:
    """
    Sends UDP knock "ARCX-KNOCK:<secret>" to the Android device gateway and waits for JSON response.
    Retries on timeout.
    """
    if not gateway_ip or gateway_ip == "0.0.0.0":
        raise KnockError("Invalid gateway IP for knock")

    message = f"ARCX-KNOCK:{secret}".encode("utf-8")
    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(message, (gateway_ip, port))
            data, _ = sock.recvfrom(4096)
            decoded = data.decode("utf-8", errors="replace").strip()
            return KnockResult.from_json(decoded)
        except socket.timeout:
            last_error = KnockTimeoutError(
                f"Knock timed out after {timeout}s on {gateway_ip}:{port} (attempt {attempt + 1}/{retries + 1})"
            )
        except socket.error as e:
            last_error = KnockError(f"Socket transmission failure: {e}")
        finally:
            sock.close()

    if last_error:
        raise last_error
    raise KnockError("Unknown knock failure")


class KnockClient:
    """Client class providing object-oriented knock interface."""

    def __init__(self, port: int = 9099, timeout: float = 2.0, retries: int = 2) -> None:
        self.port = port
        self.timeout = timeout
        self.retries = retries

    def knock(self, gateway_ip: str, secret: str) -> Optional[KnockResult]:
        try:
            return send_knock(gateway_ip, secret, port=self.port, timeout=self.timeout, retries=self.retries)
        except Exception:
            return None
