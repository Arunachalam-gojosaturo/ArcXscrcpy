# ARC-LINK Visual Design: Screenshots-in-Words

This document details the exact visual layout, color palette, typography, animations, and micro-interactions of both the Arch Linux Desktop GUI and the Android Jetpack Compose Companion App.

---

## 1. Arch Linux Desktop Application (`arc-link`)

### Window Geometry & Background
- **Resolution:** 1020 x 820 px (scalable, minimum size 900 x 700 px).
- **Background:** Deep space cyberpunk backdrop (`#070A12` grading into `#0D1224`).
- **Surface Polish:** Translucent glassmorphism panels with 1px hairline border at 12% white opacity (`rgba(255, 255, 255, 0.12)`) and rounded 14-20px corners.

### Zone 1: Header Row
- **Left:** The bold glowing electric cyan logo `"ARC-LINK"` in Orbitron ExtraBold typography, accompanied by the subtitle `"Autonomous Wireless ADB / scrcpy Bridge"` in muted slate.
- **Center-Right:** Pill badge indicating Wi-Fi hotspot status. When connected, lights up with a 1px acid green border displaying `SSID: Pixel_AP [wlan0]`.
- **Far Right:** The animated **GlowPill** status widget.
  - In `DISCONNECTED`: Dark translucent capsule with a gray indicator dot.
  - In `SEARCHING` / `KNOCKING` / `CONNECTING`: Amber capsule with a pulsating outer neon glow and dynamic dot halo expanding/contracting at 25 FPS.
  - In `CONNECTED`: Brilliant acid green `#39FF88` glowing capsule displaying `"CONNECTED"`.

### Zone 2: Device Telemetry Card (Glass Panel)
- **Top:** Displays the target hardware name in electric cyan Orbitron (e.g., `GOOGLE PIXEL 7 PRO • Google Pixel 7 Pro`).
- **Grid Layout (2 Rows x 4 Columns):**
  - Row 1: `ENDPOINT` (`192.168.43.1:39451` in acid green), `ANDROID VER` (`Android 14 (API 34)`), `BATTERY` (`88%` with dynamic green/red color coding), `POWER` (`AC / USB Charging`).
  - Row 2: `STORAGE` (`142 GB free (256 GB total)`), `UPTIME` (`up 3 days, 14:22`), `SERIAL / ID` (`192.168.43.1`), `AUTH MODE` (`TCP/IP 9099`).
- **Loading State:** When connecting, switches seamlessly to the `SkeletonShimmer` loader, where a 45-degree cyan laser sweep animates smoothly across the dark glass surface.

### Zone 3: Primary Control Row
- **Big Connect Button:** Vibrant gradient fill (`#00E5FF` to `#0099B8`) with dark bold typography `"CONNECT PHONE"`.
- **Disconnect Button:** Outlined danger button in crimson red (`#FF3B5C`) with 60% translucent border.
- **Progress Spinner & Step Label:** Circular progress ring with spinning cyan comet tail and live step text: `"Knocking on gateway 192.168.43.1:9099..."` -> `"Handshaking dynamic port..."`.
- **Action Links:** Subtle glass buttons for `Pairing... (Ctrl+P)` and `⚙ Settings (Ctrl+,)`.

### Zone 4: Three Large Glowing Action Cards
- **Card 1 (SCRCPY):** Electric cyan border with icon, hotkey tag `[F1]`, and subtitle `"Mirror Screen & Audio"`. When active, displays a green `"RUNNING"` badge and inline red `"STOP"` button.
- **Card 2 (SCREEN OFF):** Magenta accent (`#FF2BD6`) with hotkey tag `[F2]`, providing one-click mirror while keeping the physical AMOLED display unpowered.
- **Card 3 (SNIFFER):** Amber accent (`#FFB020`) with hotkey tag `[F3]`, activating live Scapy packet capture on the Wi-Fi hotspot interface.

### Zone 5: Live Tab Panels
- **Tab 1 (LOG CONSOLE):** Dark terminal console with real-time search filter, "Copy All" and "Export" buttons. Color-coded log lines: Cyan for `[INFO]`, Acid Green for `[SUCCESS]`, Amber for `[WARN]`, and Red for `[ERROR]`.
- **Tab 2 (PACKET SNIFFER):** Live Scapy frame table showing `TIME`, `SOURCE`, `DESTINATION`, `PROTO` (colored chips: Cyan TCP, Magenta UDP, Amber ICMP), `LENGTH`, and decoded packet summaries. Includes auto-scroll toggle and live packet counter.
- **Tab 3 (SCRCPY PRESETS):** One-click toggle profiles for `⚡ Low Latency` (1024px, 4M, 60fps, no audio), `💎 High Quality` (1080p, 16M), and `🎵 Audio Only` (headless streaming).

### Zone 6: Footer
- Bottom status bar showing daemon uptime (`Uptime: 01:24:10`), detected ADB and scrcpy binary paths, and system signature `"ARC-LINK v1.0.0 [Arch Linux]"`.

---

## 2. Android Jetpack Compose Companion App (`com.arcx.arclink`)

### Single Dashboard Screen Layout
- **Theme:** Dynamic deep space gradient (`#070A12` -> `#0D1224`) with edge-to-edge system bar integration.
- **Top Bar:** Large electric cyan branding `"ARC-LINK"` with subtitle `"AUTONOMOUS SCREEN RECOVERY"`. On the right, an "ARMED" pill switch glowing acid green.
- **Hero Status Ring:**
  - A prominent 170dp circular neon gauge in the center of the viewport.
  - When the Wi-Fi hotspot is active, a pulsating outer halo expands and contracts rhythmically at 1.2s intervals in acid green glow (`#39FF88`).
  - Inside the ring: Wi-Fi tethering glyph, status label `"HOTSPOT ACTIVE"`, and current interface address (`ap0 (192.168.43.1)`).
- **Telemetry Glass Card:**
  - Glass card with 1px translucent border (`rgba(255, 255, 255, 0.12)`).
  - Displays `WIRELESS ADB: ACTIVE`, dynamic `ADB PORT: 39451`, `CLIENT IP: 192.168.43.15`, and `LAST AUTH KNOCK: 20:45:12`.
- **Quick Action Buttons:**
  - **"Grant Cmd":** Outlined cyan button that copies the `adb shell pm grant` command to the clipboard with haptic feedback.
  - **"Battery":** Outlined amber button that launches the Android battery optimization exemption intent.
  - **"Secret":** Outlined magenta button that opens the secret token configuration modal dialog.
- **Live Event Timeline:**
  - Monospace scrolling event log at the bottom of the screen displaying real-time daemon milestones (e.g., `[20:45:10] Hotspot turned ON`, `[20:45:12] Authenticated knock accepted from 192.168.43.15`, `[20:45:13] Wireless ADB enabled on port 39451`).
