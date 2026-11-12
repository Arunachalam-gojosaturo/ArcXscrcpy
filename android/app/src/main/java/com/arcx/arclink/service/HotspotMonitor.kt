package com.arcx.arclink.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.wifi.WifiManager
import android.util.Log
import com.arcx.arclink.model.HotspotState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.net.Inet4Address
import java.net.NetworkInterface

/**
 * Triple-strategy Wi-Fi Hotspot detector.
 * Combines:
 *  1. WIFI_AP_STATE_CHANGED broadcast (11 off, 13 on)
 *  2. Reflection on WifiManager.isWifiApEnabled
 *  3. NetworkInterface polling every 3s for AP interfaces (ap0, wlan1, swlan0, softap0).
 */
class HotspotMonitor(
    private val context: Context,
    private val scope: CoroutineScope
) {
    companion object {
        private const val TAG = "ARC_HotspotMonitor"
        private const val ACTION_WIFI_AP_STATE_CHANGED = "android.net.wifi.WIFI_AP_STATE_CHANGED"
        private const val EXTRA_WIFI_AP_STATE = "wifi_state"
        private const val WIFI_AP_STATE_ENABLED = 13
        private const val WIFI_AP_STATE_DISABLED = 11

        private val PRIMARY_AP_PREFIXES = listOf("ap", "softap", "swlan", "wlan2", "wlan1", "wigig", "tether")
        private val SECONDARY_AP_PREFIXES = listOf("wlan", "rndis", "ncm")
        private val EXCLUDED_IFACE_PREFIXES = listOf("lo", "dummy", "rmnet", "r_rmnet", "ccmni", "p2p", "wifi-aware", "tun", "sit", "ip6", "gre")
    }

    private val _hotspotState = MutableStateFlow(HotspotState())
    val hotspotState: StateFlow<HotspotState> = _hotspotState.asStateFlow()

    private var pollingJob: Job? = null
    private val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager

    private val apReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == ACTION_WIFI_AP_STATE_CHANGED) {
                val state = intent.getIntExtra(EXTRA_WIFI_AP_STATE, -1)
                Log.d(TAG, "WIFI_AP_STATE_CHANGED broadcast received: state=$state")
                evaluateState(broadcastState = state)
            }
        }
    }

    fun start() {
        // 1. Register broadcast receiver
        val filter = IntentFilter(ACTION_WIFI_AP_STATE_CHANGED)
        try {
            context.registerReceiver(apReceiver, filter)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to register AP broadcast receiver: ${e.message}")
        }

        // 2. Start periodic 3s background polling coroutine
        pollingJob = scope.launch(Dispatchers.IO) {
            while (isActive) {
                evaluateState()
                delay(3000L)
            }
        }
    }

    fun stop() {
        try {
            context.unregisterReceiver(apReceiver)
        } catch (e: Exception) {
            Log.w(TAG, "Unregister receiver failed: ${e.message}")
        }
        pollingJob?.cancel()
    }

    private fun evaluateState(broadcastState: Int = -1) {
        val (ifaceName, ip) = findActiveApInterface()

        // Strategy A: Broadcast state 13 (ON)
        val fromBroadcast = broadcastState == WIFI_AP_STATE_ENABLED

        // Strategy B: Hidden reflection method isWifiApEnabled()
        val fromReflection = checkReflectionApEnabled()

        // Strategy C: Physical network interface presence with IPv4
        val fromInterface = ifaceName.isNotEmpty() && ip.isNotEmpty()

        val isEnabled = fromBroadcast || fromReflection || fromInterface

        val source = when {
            fromInterface -> "INTERFACE ($ifaceName)"
            fromBroadcast -> "BROADCAST"
            fromReflection -> "REFLECTION"
            else -> "IDLE"
        }

        val resolvedIface = ifaceName.ifEmpty { if (isEnabled) "ap0" else "" }
        val resolvedIp = ip.ifEmpty { if (isEnabled) "192.168.43.1" else "" }

        val newState = HotspotState(
            isEnabled = isEnabled,
            interfaceName = resolvedIface,
            ipAddress = resolvedIp,
            detectionSource = source
        )

        if (_hotspotState.value != newState) {
            Log.i(TAG, "Hotspot state updated: enabled=$isEnabled, iface=$resolvedIface, ip=$resolvedIp (Source: $source)")
            _hotspotState.value = newState
        }
    }

    private fun checkReflectionApEnabled(): Boolean {
        if (wifiManager == null) return false
        return try {
            val method = wifiManager.javaClass.getDeclaredMethod("isWifiApEnabled")
            method.isAccessible = true
            (method.invoke(wifiManager) as? Boolean) ?: false
        } catch (e: Exception) {
            false
        }
    }

    private fun findActiveApInterface(): Pair<String, String> {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()?.toList() ?: return Pair("", "")

            // Pass 1: Look for primary hotspot/AP interfaces (ap, softap, swlan, wlan2, wlan1, etc.)
            for (prefix in PRIMARY_AP_PREFIXES) {
                for (iface in interfaces) {
                    if (!iface.isUp || iface.isLoopback) continue
                    if (iface.name.lowercase().startsWith(prefix)) {
                        val ipv4 = getFirstIpv4(iface)
                        if (ipv4.isNotEmpty()) {
                            return Pair(iface.name, ipv4)
                        }
                    }
                }
            }

            // Pass 2: Look for secondary interfaces (wlan, rndis, ncm)
            for (prefix in SECONDARY_AP_PREFIXES) {
                for (iface in interfaces) {
                    if (!iface.isUp || iface.isLoopback) continue
                    if (iface.name.lowercase().startsWith(prefix)) {
                        val ipv4 = getFirstIpv4(iface)
                        if (ipv4.isNotEmpty()) {
                            return Pair(iface.name, ipv4)
                        }
                    }
                }
            }

            // Pass 3: Any non-cellular, non-loopback interface that is UP and has an IPv4
            for (iface in interfaces) {
                if (!iface.isUp || iface.isLoopback) continue
                val name = iface.name.lowercase()
                if (EXCLUDED_IFACE_PREFIXES.any { name.startsWith(it) }) continue
                val ipv4 = getFirstIpv4(iface)
                if (ipv4.isNotEmpty()) {
                    return Pair(iface.name, ipv4)
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "NetworkInterface query error: ${e.message}")
        }
        return Pair("", "")
    }

    private fun getFirstIpv4(iface: NetworkInterface): String {
        for (addr in iface.inetAddresses) {
            if (addr is Inet4Address && !addr.isLoopbackAddress) {
                val host = addr.hostAddress ?: ""
                if (host.isNotEmpty() && !host.startsWith("127.")) {
                    return host
                }
            }
        }
        return ""
    }
}
