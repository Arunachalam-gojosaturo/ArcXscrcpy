<div align="center">

![ArcXscrcpy Banner](assets/banner.jpg)

# ArcXscrcpy
### Autonomous Wireless ADB & Screen Recovery Bridge for Broken Android Displays

[![Arch Linux](https://img.shields.io/badge/Platform-Arch%20Linux-1793D1?style=for-the-badge&logo=arch-linux&logoColor=white)](https://archlinux.org)
[![Android](https://img.shields.io/badge/Android-API%2030%2B%20(11--14)-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6%20Cyber--HUD-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com)
[![Jetpack Compose](https://img.shields.io/badge/UI-Jetpack%20Compose%20M3-4285F4?style=for-the-badge&logo=jetpackcompose&logoColor=white)](https://developer.android.com/jetpack/compose)
[![scrcpy](https://img.shields.io/badge/Mirroring-scrcpy%20v2.0%2B-FF6F00?style=for-the-badge)](https://github.com/Genymobile/scrcpy)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)

<br/>

**ArcXscrcpy** (powered by the **ARC-LINK** engine) is an autonomous, zero-touch wireless recovery bridge designed for Android smartphones with dead, shattered, or unresponsive touch displays. When your laptop connects to the phone's Wi-Fi hotspot, ArcXscrcpy automatically authenticates, discovers the dynamic wireless debugging port, triggers wireless ADB, and mirrors the phone screen onto your Arch Linux workstation with **zero physical touches required on the phone**.

</div>

---

## ⚡ The 4-Step Autonomous State Machine

```
   ┌─────────────────────────────────────────────────────────┐
   │ 1. Phone Reboots / Cold Boot                            │
   │    └─► BootReceiver triggers ArcLinkService daemon       │
   │    └─► DirectBootAware + Partial WakeLock active         │
   └────────────────────────────┬────────────────────────────┘
                                │
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 2. Hotspot Turns ON & Laptop Joins Wi-Fi                │
   │    └─► HotspotWatcher detects gateway route              │
   │    └─► Desktop sends UDP "ARCX-KNOCK:<secret>" to :9099 │
   │    └─► AdbController activates adb_wifi_enabled=1        │
   │    └─► NsdManager resolves dynamic TLS port              │
   │    └─► adb connect <ip>:<port> + scrcpy auto-launches!  │
   └────────────────────────────┬────────────────────────────┘
                                │
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 3. Hotspot Turns OFF                                    │
   │    └─► HotspotMonitor detects loss                       │
   │    └─► AdbController disables adb_wifi_enabled=0        │
   │    └─► Wireless ports closed to protect private networks │
   └────────────────────────────┬────────────────────────────┘
                                │
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │ 4. Laptop Loses Hotspot                                 │
   │    └─► Desktop HotspotWatcher detects route teardown     │
   │    └─► Cleanly terminates scrcpy process                 │
   │    └─► adb disconnect + UI state reset + notification    │
   └─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Complete Build & Installation Commands

### 1. Prerequisites (Arch Linux Workstation)

Install the required host dependencies using `pacman`:

```bash
sudo pacman -S --needed \
    base-devel \
    git \
    python \
    python-pyqt6 \
    python-setuptools \
    android-tools \
    scrcpy \
    python-scapy \
    libnotify \
    polkit \
    jdk17-openjdk
```

---

### 2. Desktop Application Build (`arc-link`)

You can install the desktop controller using Arch Linux's native `makepkg` or via standard Python `setup.py`:

#### Option A: Native Arch Linux Package (Recommended)
```bash
cd desktop

# Build and install the Arch package with all symlinks, desktop files, polkit, and systemd units
makepkg -si

# Enable the systemd user service for automated background startup on login
systemctl --user daemon-reload
systemctl --user enable --now arc-link.service
```

*This installs:*
- `/usr/bin/arc-link` (Main desktop GUI launcher)
- `/usr/lib/arc-link/arc-link-sniffer` (Privileged Scapy packet sniffer helper)
- `/usr/share/polkit-1/actions/org.arclink.sniffer.policy` (Polkit authorization rule)
- `/usr/share/applications/arc-link.desktop` (XDG desktop launcher)
- `/usr/share/icons/hicolor/scalable/apps/arc-link.svg` (Neon vector application icon)
- `/usr/lib/systemd/user/arc-link.service` (Systemd background daemon unit)

#### Option B: Development Installation
```bash
cd desktop

# Install directly in editable mode
python3 setup.py build
pip install -e .

# Launch directly from CLI
arc-link
# or
python3 -m arc_link
```

---

### 3. Android Companion App Build (`com.arcx.arclink`)

Ensure Java 17 and Android SDK Command-Line Tools are configured:

```bash
cd android

# Build the debug APK with Gradle
./gradlew assembleDebug

# Output APK location:
# android/app/build/outputs/apk/debug/app-debug.apk
```

---

### 4. One-Time Device Provisioning & Setup

Perform this one-time setup while you still have partial screen access, or via USB cable before deploying ArcXscrcpy for emergency recovery:

```bash
# 1. Install companion APK to phone
adb install -r android/app/build/outputs/apk/debug/app-debug.apk

# 2. Perform one-time wireless pairing (Android 11+)
# On phone: Settings -> Developer Options -> Wireless Debugging -> "Pair device with pairing code"
adb pair <PHONE_IP>:<PAIRING_PORT> <6_DIGIT_CODE>

# 3. Grant WRITE_SECURE_SETTINGS (allows rootless toggling of adb_wifi_enabled)
adb shell pm grant com.arcx.arclink android.permission.WRITE_SECURE_SETTINGS

# 4. Whitelist from Android battery optimization & app standby
adb shell dumpsys deviceidle whitelist +com.arcx.arclink
adb shell am set-standby-bucket com.arcx.arclink active

# 5. Verify the permission was successfully granted
adb shell dumpsys package com.arcx.arclink | grep WRITE_SECURE_SETTINGS
```

---

### 5. Running Automated Unit Tests

Both the desktop application and Android subsystems feature unit test suites:

#### Desktop Test Suite
```bash
cd desktop
python3 -m unittest discover -s tests -v
```
*Tests coverage:*
- `test_state.py`: Connection state machine transitions (`DISCONNECTED` -> `SEARCHING` -> `KNOCKING` -> `CONNECTING` -> `CONNECTED`).
- `test_knock.py`: UDP socket packet encoding, secret verification, and JSON payload deserialization.
- `test_discovery.py`: Dynamic mDNS resolution (`_adb-tls-connect._tcp`) and port fallback inspection.
- `test_config.py`: TOML configuration parser, serialization, and disk sync.

#### Android Test Suite
```bash
cd android
./gradlew test
```
*Tests coverage:*
- `KnockPayloadTest.kt`: Device metadata serialization (`battery`, `adb_port`, `hotspot`).
- `HotspotDetectorTest.kt`: AP state tracking across multiple network interfaces (`ap0`, `wlan1`).

---

## ⌨️ Desktop Keyboard Shortcuts & Scrcpy Presets

| Shortcut | Action | Description |
|---|---|---|
| <kbd>F1</kbd> | **Scrcpy Normal** | Launch full screen mirroring with video and synced audio |
| <kbd>F2</kbd> | **Scrcpy Screen-Off** | Launch mirror while keeping physical phone display unpowered (`--turn-screen-off`) |
| <kbd>F3</kbd> | **Toggle Sniffer** | Start/stop live Scapy packet sniffer on Wi-Fi interface |
| <kbd>Ctrl</kbd> + <kbd>,</kbd> | **Settings Dialog** | Configure shared secret, SSID filter, scrcpy CLI flags, and auto-connect |
| <kbd>Ctrl</kbd> + <kbd>P</kbd> | **Pairing Dialog** | Guided dialog to pair dynamic TLS ports with a 6-digit PIN |

### Scrcpy Performance Presets

| Preset | CLI Arguments | Best Used For |
|---|---|---|
| **⚡ Low-Latency** | `--no-audio --max-size 1024 -b 4M --max-fps 60` | High-speed touch feedback and low network jitter |
| **💎 High Quality** | `--max-size 1920 -b 16M --max-fps 60` | Full 1080p presentation, reading fine text and documents |
| **🎵 Audio Only** | `--no-video --audio-codec=opus` | Headless audio streaming without display render overhead |

---

## 📂 Project Repository Tree

```
ArcXscrcpy/
├── assets/
│   └── banner.jpg                 # Cyber-HUD panoramic banner artwork
├── docs/
│   ├── ARCHITECTURE.md            # Detailed architecture diagrams & sequences
│   ├── SETUP_CHECKLIST.md         # 8-step one-time deployment checklist
│   ├── TEST_PLAN.md               # 4-step state machine test plan & unit tests
│   ├── TROUBLESHOOTING.md         # Matrix for unauthorized, offline, FBE, etc.
│   ├── LIMITATIONS.md             # Honest limitations & USB fallback
│   └── SCREENSHOTS_IN_WORDS.md    # Cyber-HUD visual layout specifications
├── desktop/                       # Arch Linux PyQt6 Desktop Application
│   ├── PKGBUILD                   # Arch Linux makepkg installer script
│   ├── setup.py                   # Python package setup script
│   ├── arc_link/
│   │   ├── __init__.py
│   │   ├── __main__.py            # CLI launcher (python -m arc_link)
│   │   ├── main.py                # Single-instance lock, CLI args, QSS loader
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── adb_manager.py     # ADB wrapper (connect, disconnect, get-state)
│   │   │   ├── config.py          # ~/.config/arc-link/config.toml manager
│   │   │   ├── discovery.py       # UDP knock, mDNS, and fallback resolution
│   │   │   ├── hotspot_watcher.py # Dynamic interface & default route watcher
│   │   │   ├── knock.py           # UDP knock client & protocol parser
│   │   │   ├── scrcpy_runner.py   # Subprocess tracking & clean termination
│   │   │   ├── sniffer.py         # Scapy QThread manager wrapping pkexec
│   │   │   ├── sniffer_helper.py  # Standalone privileged Scapy sniffer script
│   │   │   └── state.py           # Connection state machine & telemetry models
│   │   └── ui/
│   │       ├── __init__.py
│   │       ├── main_window.py     # Cyber-HUD central window
│   │       ├── pairing_dialog.py  # Guided one-time wireless pairing dialog
│   │       ├── settings_dialog.py # Configuration dialog
│   │       ├── theme.qss          # Neon Glass / Cyber-HUD stylesheet
│   │       ├── tokens.py          # Color, geometry & typography tokens
│   │       ├── tray.py            # System tray icon with status menu
│   │       └── widgets/
│   │           ├── __init__.py
│   │           ├── action_card.py # Glowing action buttons (scrcpy, sniffer)
│   │           ├── device_card.py # Live telemetry card with shimmer loader
│   │           ├── glow_pill.py   # Animated status indicator pill
│   │           ├── log_console.py # Searchable colored terminal console
│   │           ├── packet_table.py# Real-time packet sniffer table
│   │           ├── preset_selector.py # Low-latency / High-quality presets
│   │           ├── progress_ring.py # Neon circular indeterminate spinner
│   │           └── shimmer.py     # Laser-sweep skeleton loading widget
│   ├── resources/
│   │   ├── arc-link.desktop       # XDG desktop shortcut
│   │   ├── arc-link.service       # systemd user unit for autostart
│   │   ├── org.arclink.sniffer.policy # Polkit rule for privileged helper
│   │   └── icons/
│   │       └── arc-link.svg       # Custom neon vector logo
│   └── tests/
│       ├── __init__.py
│       ├── test_config.py         # TOML configuration unit tests
│       ├── test_discovery.py      # mDNS regex & port check unit tests
│       ├── test_knock.py          # UDP knock protocol unit tests
│       └── test_state.py          # State machine transition unit tests
└── android/                       # Kotlin Jetpack Compose Companion App
    ├── build.gradle.kts           # Root gradle build configuration
    ├── settings.gradle.kts        # Repository & module settings
    ├── gradle.properties          # JVM & AndroidX optimization flags
    ├── gradlew                    # Gradle build wrapper script
    ├── gradle/wrapper/
    │   └── gradle-wrapper.properties
    └── app/
        ├── build.gradle.kts       # App module build script (API 30..34)
        ├── proguard-rules.pro
        └── src/
            ├── main/
            │   ├── AndroidManifest.xml # Permissions, Receiver & Service declaration
            │   └── java/com/arcx/arclink/
            │       ├── ArcLinkApp.kt   # Application class with auto daemon init
            │       ├── model/
            │       │   └── Models.kt   # HotspotState & KnockPayload data models
            │       ├── service/
            │       │   ├── AdbController.kt # WRITE_SECURE_SETTINGS & NsdManager
            │       │   ├── ArcLinkService.kt# Foreground daemon with WakeLock
            │       │   ├── BootReceiver.kt  # DirectBootAware autostart receiver
            │       │   ├── HotspotMonitor.kt# Broadcast + Reflection + Polling
            │       │   └── KnockListener.kt # UDP server on :9099
            │       └── ui/
            │           ├── MainActivity.kt  # Compose Cyber-HUD dashboard
            │           └── theme/
            │               ├── Color.kt     # Shared Neon Glass color constants
            │               ├── Theme.kt     # Material 3 dark cyber scheme
            │               └── Type.kt      # Monospace and sans typography
            └── test/java/com/arcx/arclink/
                ├── HotspotDetectorTest.kt   # AP state model unit tests
                └── KnockPayloadTest.kt      # Knock JSON serialization tests
```

---

## 🔒 Security Architecture

1. **Non-Root Elevated Settings:**
   - Instead of risky device rooting, ArcXscrcpy relies on standard Android `WRITE_SECURE_SETTINGS` permission granted once via ADB cable.
2. **Subnet-Isolated Knock Protocol:**
   - The Android UDP server on `:9099` strictly accepts requests originating from private hotspot subnets (`192.168.43.x`, `192.168.49.x`, `10.x.x.x`). Requests from foreign or WAN interfaces are immediately dropped.
3. **Cryptographic Shared Secret:**
   - All knocks must match the configured token (`ARCX-KNOCK:<secret>`). Any mismatched token triggers immediate silent socket discard.
4. **Immediate Teardown:**
   - When the hotspot shuts off, `adb_wifi_enabled` is set back to `0` immediately, ensuring the device never leaves debugging ports open on external networks.
5. **Polkit Least-Privilege:**
   - On Linux, only the isolated sniffer helper (`/usr/lib/arc-link/arc-link-sniffer`) is granted elevated packet capture permissions via PolicyKit. The GUI runs strictly as an unprivileged user.

---

## 📖 In-Depth Documentation

- [Detailed Architecture & Flowcharts](docs/ARCHITECTURE.md)
- [Step-by-Step Provisioning Checklist](docs/SETUP_CHECKLIST.md)
- [State Machine & Integration Test Plan](docs/TEST_PLAN.md)
- [Troubleshooting & Diagnostics Matrix](docs/TROUBLESHOOTING.md)
- [Honest Technical Limitations & USB Fallback](docs/LIMITATIONS.md)
- [Visual Design & Screenshots-in-Words](docs/SCREENSHOTS_IN_WORDS.md)

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).
