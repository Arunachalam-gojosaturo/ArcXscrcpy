# ARC-LINK Comprehensive Test Plan

This document details the test strategy for verifying the 4-step state machine, fault tolerance, and automated unit tests.

---

## 1. Automated Unit Test Matrix

### Desktop Test Suite (`desktop/tests/`)
| Test File | Target Functionality | Verification Criteria | Status |
|---|---|---|---|
| `test_state.py` | `ConnectionStateMachine` lifecycle | DISCONNECTED -> SEARCHING -> KNOCKING -> CONNECTING -> CONNECTED transitions; state change signals; device telemetry updates. | PASS |
| `test_knock.py` | `KnockClient` & `KnockResult` protocol | Dataclass parsing; socket timeout handling; binary serialization; ARCX-KNOCK message validation. | PASS |
| `test_discovery.py` | `DiscoveryEngine` & mDNS parser | mDNS string regex extraction (`_adb-tls-connect._tcp`); fallback TCP port scanner check. | PASS |
| `test_config.py` | `ArcConfig` TOML manager | Save/Load roundtrip; section serialization; fallback default parameters. | PASS |

### Android Test Suite (`android/app/src/test/`)
| Test File | Target Functionality | Verification Criteria |
|---|---|---|
| `KnockPayloadTest.kt` | JSON metadata generation | Ensures all required keys (`device_name`, `model`, `ip`, `adb_port`, `adb_wifi_enabled`, `hotspot`, `battery`) are present and valid types. |
| `HotspotDetectorTest.kt` | `HotspotState` model & flags | State mutation, interface identification, fallback detection tags. |

---

## 2. 4-Step State Machine Integration Test Plan

### Phase 1: Cold Reboot & Autonomous Daemon Autostart
- **Objective:** Verify `ArcLinkService` starts in the background without user interaction or display unlock.
- **Procedure:**
  1. Ensure USB cable is disconnected.
  2. Perform cold device reboot (`adb reboot` or battery pull).
  3. Wait 30 seconds for direct-boot initialization.
- **Pass Criteria:**
  - Running `adb shell dumpsys activity services com.arcx.arclink` shows `ArcLinkService` in foreground mode (`specialUse`).
  - System logs (`logcat`) show `KnockListener bound to UDP 0.0.0.0:9099`.

---

### Phase 2: Hotspot Activation & Auto-Connect Handshake
- **Objective:** Verify zero-touch connection establishment upon laptop joining hotspot.
- **Procedure:**
  1. Enable phone Wi-Fi hotspot.
  2. Laptop joins phone SSID.
- **Pass Criteria:**
  - Desktop `HotspotWatcher` emits `hotspot_connected` within 2 seconds.
  - UDP packet `ARCX-KNOCK:<secret>` is transmitted to `192.168.43.1:9099`.
  - Android `KnockListener` validates secret and calls `AdbController.enableForSession()`.
  - Android responds with dynamic port JSON payload.
  - Desktop runs `adb connect <gateway>:<dynamic_port>` and verifies with `get-state`.
  - Desktop UI turns acid green (`CONNECTED`) and `scrcpy` window displays on laptop screen.

---

### Phase 3: Hotspot Deactivation & Security Teardown
- **Objective:** Ensure wireless debugging is promptly disabled to prevent port exposure.
- **Procedure:**
  1. Turn off phone hotspot.
- **Pass Criteria:**
  - Android `HotspotMonitor` triggers state change to `isEnabled = false`.
  - `AdbController.disableForSession()` sets `adb_wifi_enabled = 0`.
  - `adb shell settings get global adb_wifi_enabled` confirms value is `0`.

---

### Phase 4: Laptop Loss & Graceful Scrcpy Cleanup
- **Objective:** Ensure desktop app cleanly terminates subprocesses when hotspot signal drops.
- **Procedure:**
  1. Disconnect laptop Wi-Fi or move out of range while scrcpy is mirroring.
- **Pass Criteria:**
  - Desktop `HotspotWatcher` detects default route removal.
  - `ScrcpyRunner` terminates scrcpy PID with SIGTERM / SIGKILL.
  - `AdbManager` executes `adb disconnect`.
  - Desktop UI reflects `DISCONNECTED` state and shows notification.
