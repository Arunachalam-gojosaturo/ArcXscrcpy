package com.arcx.arclink.service

import android.content.Context
import android.content.pm.PackageManager
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.provider.Settings
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Controller for toggling Android Wireless Debugging via WRITE_SECURE_SETTINGS
 * and discovering dynamic wireless ADB ports via NsdManager.
 */
class AdbController(
    private val context: Context,
    private val scope: CoroutineScope
) {
    companion object {
        private const val TAG = "ARC_AdbController"
        private const val SERVICE_TYPE_TLS = "_adb-tls-connect._tcp"
        private const val SERVICE_TYPE_PLAIN = "_adb._tcp"
    }

    private val _isAdbWifiActive = MutableStateFlow(false)
    val isAdbWifiActive: StateFlow<Boolean> = _isAdbWifiActive.asStateFlow()

    private val _currentPort = MutableStateFlow(0)
    val currentPort: StateFlow<Int> = _currentPort.asStateFlow()

    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as? NsdManager
    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private var isNsdDiscovering = false

    // One-time per hotspot session guard
    private var hasEnabledForCurrentSession = false
    private var watchdogJob: Job? = null

    init {
        checkCurrentSettingsState()
        startNsdDiscovery()
    }

    fun hasSecureSettingsPermission(): Boolean {
        return context.checkSelfPermission(android.Manifest.permission.WRITE_SECURE_SETTINGS) == PackageManager.PERMISSION_GRANTED
    }

    fun checkCurrentSettingsState(): Boolean {
        return try {
            val wifiAdb = Settings.Global.getInt(context.contentResolver, "adb_wifi_enabled", 0)
            val active = wifiAdb == 1
            _isAdbWifiActive.value = active
            active
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Enables Wireless ADB when hotspot is active and an authenticated knock arrives.
     * Guarded to run only once per hotspot session.
     */
    fun enableForSession(reason: String): Boolean {
        if (!hasSecureSettingsPermission()) {
            Log.e(TAG, "Cannot enable wireless ADB: WRITE_SECURE_SETTINGS permission missing!")
            return false
        }

        if (hasEnabledForCurrentSession && _isAdbWifiActive.value && _currentPort.value > 0) {
            Log.d(TAG, "Wireless ADB already enabled for this session (Port: ${_currentPort.value})")
            return true
        }

        try {
            Log.i(TAG, "Enabling wireless debugging ($reason)...")
            // 1. Ensure basic ADB is enabled
            Settings.Global.putInt(context.contentResolver, Settings.Global.ADB_ENABLED, 1)

            // 2. Enable Wireless Debugging
            Settings.Global.putInt(context.contentResolver, "adb_wifi_enabled", 1)

            hasEnabledForCurrentSession = true
            _isAdbWifiActive.value = true

            // Trigger fresh NSD discovery to capture port immediately
            restartNsdDiscovery()
            startWatchdog()
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to write secure settings: ${e.message}")
            return false
        }
    }

    /**
     * Disables Wireless ADB immediately when hotspot is disabled or session terminates.
     */
    fun disableForSession(reason: String) {
        hasEnabledForCurrentSession = false
        watchdogJob?.cancel()

        if (!hasSecureSettingsPermission()) {
            return
        }

        try {
            Log.i(TAG, "Disabling wireless debugging ($reason)...")
            Settings.Global.putInt(context.contentResolver, "adb_wifi_enabled", 0)
            _isAdbWifiActive.value = false
            _currentPort.value = 0
        } catch (e: Exception) {
            Log.w(TAG, "Failed to disable adb_wifi_enabled: ${e.message}")
        }
    }

    /**
     * Resets the session guard when a new hotspot session begins.
     */
    fun resetSessionGuard() {
        hasEnabledForCurrentSession = false
    }

    private fun startWatchdog() {
        watchdogJob?.cancel()
        watchdogJob = scope.launch(Dispatchers.IO) {
            var elapsedSec = 0
            while (isActive && elapsedSec < 20) {
                delay(2000L)
                elapsedSec += 2
                checkCurrentSettingsState()

                if (_currentPort.value > 0) {
                    Log.d(TAG, "Watchdog confirmed active wireless ADB port: ${_currentPort.value}")
                    break
                }
            }
        }
    }

    private fun startNsdDiscovery() {
        if (nsdManager == null || isNsdDiscovering) return

        discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(regType: String) {
                isNsdDiscovering = true
                Log.d(TAG, "NSD discovery started for $regType")
            }

            override fun onServiceFound(service: NsdServiceInfo) {
                Log.d(TAG, "NSD service candidate found: ${service.serviceName} (${service.serviceType})")
                if (service.serviceType.contains("adb")) {
                    resolveService(service)
                }
            }

            override fun onServiceLost(service: NsdServiceInfo) {
                Log.d(TAG, "NSD service lost: ${service.serviceName}")
            }

            override fun onDiscoveryStopped(serviceType: String) {
                isNsdDiscovering = false
                Log.d(TAG, "NSD discovery stopped")
            }

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                isNsdDiscovering = false
                Log.w(TAG, "Start discovery failed: code $errorCode")
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                isNsdDiscovering = false
            }
        }

        try {
            nsdManager.discoverServices(SERVICE_TYPE_TLS, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
        } catch (e: Exception) {
            Log.w(TAG, "NSD discoverServices failed: ${e.message}")
        }
    }

    private fun resolveService(serviceInfo: NsdServiceInfo) {
        nsdManager?.resolveService(serviceInfo, object : NsdManager.ResolveListener {
            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.w(TAG, "Resolve failed for ${serviceInfo.serviceName}: code $errorCode")
            }

            override fun onServiceResolved(resolved: NsdServiceInfo) {
                val port = resolved.port
                Log.i(TAG, "Resolved Wireless ADB port: $port")
                if (port > 0) {
                    _currentPort.value = port
                    _isAdbWifiActive.value = true
                }
            }
        })
    }

    private fun restartNsdDiscovery() {
        stopNsdDiscovery()
        startNsdDiscovery()
    }

    fun stopNsdDiscovery() {
        if (nsdManager != null && isNsdDiscovering && discoveryListener != null) {
            try {
                nsdManager.stopServiceDiscovery(discoveryListener)
            } catch (e: Exception) {
                Log.w(TAG, "Failed to stop NSD: ${e.message}")
            }
            isNsdDiscovering = false
        }
    }
}
