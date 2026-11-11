"""
Configuration management for ARC-LINK.
Handles loading, saving, and defaults for ~/.config/arc-link/config.toml.
Supports both structured sections and flat configuration access.
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "arc-link"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"


@dataclass
class AuthConfig:
    shared_secret: str = "arcx_secure_token_broken_screen"


@dataclass
class NetworkConfig:
    knock_port: int = 9099
    default_adb_port: int = 5555
    ssid_filter: List[str] = field(default_factory=list)
    interface_override: str = ""


@dataclass
class ScrcpyConfig:
    default_args: List[str] = field(default_factory=lambda: [
        "--no-audio",
        "--max-size",
        "1024",
        "-b",
        "4M",
        "--max-fps",
        "60",
    ])
    preset: str = "low_latency"


@dataclass
class BehaviorConfig:
    auto_connect: bool = True
    auto_launch_scrcpy: bool = True
    auto_disconnect_on_loss: bool = True
    autostart_minimized: bool = False
    show_notifications: bool = True
    backoff_initial: float = 1.0
    backoff_max: float = 30.0


@dataclass
class ArcConfig:
    """Strongly typed multi-section application configuration."""
    auth: AuthConfig = field(default_factory=AuthConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    scrcpy: ScrcpyConfig = field(default_factory=ScrcpyConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    saved_endpoint: str = ""
    config_path: Path = field(default_factory=lambda: DEFAULT_CONFIG_FILE)

    # Backward-compatible convenience properties
    @property
    def secret(self) -> str:
        return self.auth.shared_secret

    @secret.setter
    def secret(self, val: str) -> None:
        self.auth.shared_secret = val

    @property
    def knock_port(self) -> int:
        return self.network.knock_port

    @knock_port.setter
    def knock_port(self, val: int) -> None:
        self.network.knock_port = val

    def save(self, path: Optional[Path] = None) -> None:
        dest = path or self.config_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = [
            "# ARC-LINK Configuration File",
            "# Automatically managed by ARC-LINK Desktop Controller",
            "",
            "[auth]",
            f'shared_secret = "{self.auth.shared_secret}"',
            "",
            "[network]",
            f"knock_port = {self.network.knock_port}",
            f"default_adb_port = {self.network.default_adb_port}",
            f"ssid_filter = {[s for s in self.network.ssid_filter]}",
            f'interface_override = "{self.network.interface_override}"',
            "",
            "[scrcpy]",
            f"default_args = {[s for s in self.scrcpy.default_args]}",
            f'preset = "{self.scrcpy.preset}"',
            "",
            "[behavior]",
            f"auto_connect = {'true' if self.behavior.auto_connect else 'false'}",
            f"auto_launch_scrcpy = {'true' if self.behavior.auto_launch_scrcpy else 'false'}",
            f"auto_disconnect_on_loss = {'true' if self.behavior.auto_disconnect_on_loss else 'false'}",
            f"autostart_minimized = {'true' if self.behavior.autostart_minimized else 'false'}",
            f"show_notifications = {'true' if self.behavior.show_notifications else 'false'}",
            f"backoff_initial = {self.behavior.backoff_initial}",
            f"backoff_max = {self.behavior.backoff_max}",
            "",
            f'saved_endpoint = "{self.saved_endpoint}"',
            "",
        ]
        with open(dest, "w", encoding="utf-8") as f:
            f.write("\n".join(content))


# Alias AppConfig for compatibility
AppConfig = ArcConfig


def load_config(config_path: Path | None = None) -> ArcConfig:
    path = config_path or DEFAULT_CONFIG_FILE
    cfg = ArcConfig(config_path=path)
    if not path.exists():
        return cfg

    try:
        with open(path, "rb") as f:
            if tomllib:
                data = tomllib.load(f)
            else:
                data = {}

        if "auth" in data:
            if "shared_secret" in data["auth"]:
                cfg.auth.shared_secret = str(data["auth"]["shared_secret"])
        elif "secret" in data:
            cfg.auth.shared_secret = str(data["secret"])

        if "network" in data:
            net = data["network"]
            if "knock_port" in net:
                cfg.network.knock_port = int(net["knock_port"])
            if "default_adb_port" in net:
                cfg.network.default_adb_port = int(net["default_adb_port"])
            if "ssid_filter" in net:
                cfg.network.ssid_filter = list(net["ssid_filter"])
            if "interface_override" in net:
                cfg.network.interface_override = str(net["interface_override"])

        if "scrcpy" in data:
            scr = data["scrcpy"]
            if "default_args" in scr:
                cfg.scrcpy.default_args = list(scr["default_args"])
            if "preset" in scr:
                cfg.scrcpy.preset = str(scr["preset"])

        if "behavior" in data:
            beh = data["behavior"]
            if "auto_connect" in beh:
                cfg.behavior.auto_connect = bool(beh["auto_connect"])
            if "auto_launch_scrcpy" in beh:
                cfg.behavior.auto_launch_scrcpy = bool(beh["auto_launch_scrcpy"])
            if "auto_disconnect_on_loss" in beh:
                cfg.behavior.auto_disconnect_on_loss = bool(beh["auto_disconnect_on_loss"])
            if "autostart_minimized" in beh:
                cfg.behavior.autostart_minimized = bool(beh["autostart_minimized"])
            if "show_notifications" in beh:
                cfg.behavior.show_notifications = bool(beh["show_notifications"])

        if "saved_endpoint" in data:
            cfg.saved_endpoint = str(data["saved_endpoint"])

    except Exception:
        pass

    return cfg


class ConfigManager:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self._config = load_config(self.config_path)

    @property
    def config(self) -> ArcConfig:
        return self._config

    def save(self, cfg: ArcConfig | None = None) -> None:
        if cfg:
            self._config = cfg
        self._config.save(self.config_path)
