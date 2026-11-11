# ARC-LINK One-Time Setup Checklist

Follow this procedure in exact sequence while your phone screen is still partially functional, or via USB cable before deploying ARC-LINK for broken-display emergency recovery.

---

### Step 1: Build & Install the Android Companion APK
1. Ensure Java 17 and Android SDK build-tools are available:
   ```bash
   cd /home/arunachalam/ArcXscrcpy/android
   ./gradlew assembleDebug
   ```
2. Connect your phone via USB cable with Developer Options enabled and install the APK:
   ```bash
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```

---

### Step 2: Perform One-Time ADB Pairing (While Screen is Accessible)
On Android 11+ (API 30+), wireless debugging requires an initial TLS pairing handshake to trust the laptop's RSA key:
1. On the phone, navigate to:
   `Settings` -> `System` -> `Developer options` -> `Wireless debugging`
2. Toggle Wireless Debugging ON and tap **"Pair device with pairing code"**.
3. Note the IP, Pairing Port (different from the connection port), and 6-digit code shown on the screen.
4. On your Arch Linux laptop, run:
   ```bash
   adb pair <IP>:<PAIRING_PORT> <6-DIGIT_CODE>
   ```
   *Example: `adb pair 192.168.43.1:41235 941024`*
5. Confirm output shows: `Successfully paired to 192.168.43.1:41235`.
   *This saves your laptop's public key in `/data/misc/adb/adb_keys` on the phone permanently.*

---

### Step 3: Grant WRITE_SECURE_SETTINGS Permission
Because the app runs without root, it requires elevated permission to write system settings:
```bash
adb shell pm grant com.arcx.arclink android.permission.WRITE_SECURE_SETTINGS
```
Verify the permission was granted:
```bash
adb shell dumpsys package com.arcx.arclink | grep WRITE_SECURE_SETTINGS
```

---

### Step 4: Disable Battery Optimization & OEM Killers
To ensure the background daemon survives deep sleep and is not killed by aggressive Android power managers:
1. Whitelist from battery optimization:
   ```bash
   adb shell dumpsys deviceidle whitelist +com.arcx.arclink
   ```
2. Disable app standby restrictions:
   ```bash
   adb shell am set-standby-bucket com.arcx.arclink active
   ```
3. Open the ARC-LINK app once on the phone and tap **"Battery"** to accept the exemption prompt.

---

### Step 5: Install Desktop App via PKGBUILD on Arch Linux
1. Change directory to the desktop package:
   ```bash
   cd /home/arunachalam/ArcXscrcpy/desktop
   ```
2. Build and install the Arch package with all dependencies:
   ```bash
   makepkg -si
   ```
   *This installs:*
   - `/usr/bin/arc-link`
   - `/usr/lib/arc-link/arc-link-sniffer`
   - `/usr/share/polkit-1/actions/org.arclink.sniffer.policy`
   - `/usr/share/applications/arc-link.desktop`
   - `/usr/lib/systemd/user/arc-link.service`
   - `/usr/share/icons/hicolor/scalable/apps/arc-link.svg`

3. Enable the user systemd service (starts automatically on login):
   ```bash
   systemctl --user enable --now arc-link.service
   ```

---

### Step 6: Configure Matching Shared Secret on Both Sides
1. On your laptop, open `~/.config/arc-link/config.toml` (or click **Settings** in the desktop GUI):
   ```toml
   [auth]
   shared_secret = "your_secure_custom_passphrase"
   ```
2. In the Android app, tap **"Secret"** and enter the exact same passphrase.

---

### Step 7: Reboot Verification Test
1. Unplug the USB cable from the phone completely.
2. Reboot the phone:
   ```bash
   adb reboot
   ```
3. Wait 45 seconds for the phone to boot up.
4. Turn ON the phone's Wi-Fi hotspot (via power button menu, quick settings, or hardware button).
5. On the laptop, join the phone's Wi-Fi hotspot.
6. Observe the `arc-link` desktop UI:
   - Status changes from `DISCONNECTED` -> `SEARCHING` -> `KNOCKING` -> `CONNECTING` -> `CONNECTED`.
   - Device telemetry populates (Battery %, Model, Storage, Uptime).
   - Scrcpy mirror window launches automatically with zero touches on the phone!

---

### Step 8: Hotspot Disconnection Test
1. Turn OFF the phone's hotspot.
2. Observe desktop behavior:
   - Scrcpy window closes immediately.
   - ADB session disconnects cleanly.
   - Desktop status transitions to `DISCONNECTED`.
   - System tray sends desktop notification.
