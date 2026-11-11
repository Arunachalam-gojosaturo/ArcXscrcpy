package com.arcx.arclink.model

/**
 * Hotspot operating state.
 */
data class HotspotState(
    val isEnabled: Boolean = false,
    val interfaceName: String = "",
    val ipAddress: String = "",
    val detectionSource: String = "IDLE"
)

/**
 * Payload returned to the desktop client via UDP knock response.
 */
data class KnockReplyPayload(
    val device_name: String,
    val model: String,
    val ip: String,
    val adb_port: Int,
    val adb_wifi_enabled: Boolean,
    val hotspot: Boolean,
    val battery: Int
)

/**
 * Live system state exposed to the Compose UI.
 */
data class AppUiState(
    val isArmed: Boolean = true,
    val hotspotState: HotspotState = HotspotState(),
    val isAdbWifiEnabled: Boolean = false,
    val adbPort: Int = 0,
    val connectedLaptopIp: String = "",
    val lastKnockTimestamp: Long = 0L,
    val batteryPct: Int = -1,
    val isCharging: Boolean = false,
    val sharedSecret: String = "arcx_secure_token_broken_screen",
    val logs: List<String> = emptyList()
)
