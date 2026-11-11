# Honest Technical Limitations & Fallback Strategies

While ARC-LINK delivers zero-touch broken screen recovery without root, several fundamental hardware and Android security architecture boundaries exist.

---

## 1. What Cannot Work Without Root or a Working Screen

### A. The "Initial Bootstrap Catch-22"
- **Requirement:** ARC-LINK cannot be installed or authorized on a device that is *already completely dead and locked* without prior setup.
- **Reason:** Android security forbids non-root apps from writing to `Settings.Global` without explicit permission `WRITE_SECURE_SETTINGS`. This permission can ONLY be granted once via ADB cable (`adb shell pm grant ...`).
- **Implication:** You must perform the One-Time Setup Checklist (pairing the laptop RSA key and granting the permission) **before** the screen breaks completely or while you still have partial visibility/touch.

### B. File-Based Encryption (FBE) & Direct Boot
- On modern Android devices with a lockscreen PIN/password, credentials are encrypted under CE (Credential Encrypted) storage.
- Before the first unlock after a cold reboot, only DE (Device Encrypted) storage is accessible.
- ARC-LINK's `BootReceiver` is flagged `android:directBootAware="true"` to run before first unlock. However, on certain heavily modified vendor skins (Samsung Knox, MIUI), Wireless Debugging daemon initialization is deferred by the framework until the user provides the lockscreen credential.
- **Workaround:** Connect a standard USB keyboard via USB-OTG adapter, press Space, type your PIN, and hit Enter blindly.

### C. Forced Wi-Fi Hotspot Activation
- If the phone has completely rebooted and Wi-Fi hotspot was turned OFF before reboot, non-root user applications on Android 11+ cannot programmatically toggle `WifiManager.startTethering()` due to `android.permission.TETHER_PRIVILEGED` restriction (system apps only).
- **Workaround:**
  1. Configure your phone's power menu or double-tap shortcut to toggle hotspot.
  2. Or keep Hotspot set to remain active across reboots.

---

## 2. USB-Cable Fallback (`adb tcpip 5555`) & The Reboot Reset

If wireless ADB handshake fails entirely, the standard legacy fallback is:

### Procedure:
1. Plug the phone into your Arch Linux laptop with a USB-C cable.
2. Verify connection:
   ```bash
   adb devices
   ```
3. Switch ADB daemon to persistent TCP/IP mode on port 5555:
   ```bash
   adb tcpip 5555
   ```
4. Unplug the USB cable.
5. In the `arc-link` desktop UI, click **CONNECT PHONE** (or run `adb connect 192.168.43.1:5555`).
6. Launch Scrcpy.

### The Limitation:
- **Reboot Reset:** Whenever the phone reboots, the `adbd` daemon on Android automatically resets back to USB mode only. The TCP port 5555 listener is destroyed and will not restart without either:
  1. Re-plugging the USB cable to run `adb tcpip 5555` again, OR
  2. ARC-LINK's autonomous `WRITE_SECURE_SETTINGS` trigger (`adb_wifi_enabled=1`).
- This makes ARC-LINK's automation essential for long-term cable-free recovery.
