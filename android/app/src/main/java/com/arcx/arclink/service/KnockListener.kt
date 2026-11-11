package com.arcx.arclink.service

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.provider.Settings
import android.util.Log
import com.arcx.arclink.model.HotspotState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketException

/**
 * UDP Server on port 9099.
 * Accepts "ARCX-KNOCK:<secret>", validates authentication, enables wireless ADB,
 * and replies with JSON metadata.
 */
class KnockListener(
    private val context: Context,
    private val scope: CoroutineScope,
    private val port: Int = 9099,
    private val onKnockAccepted: (laptopIp: String, timestamp: Long) -> Unit
) {
    companion object {
        private const val TAG = "ARC_KnockListener"
        private const val KNOCK_PREFIX = "ARCX-KNOCK:"
    }

    private var serverSocket: DatagramSocket? = null
    private var listeningJob: Job? = null
    private var sharedSecret: String = "arcx_secure_token_broken_screen"

    fun setSharedSecret(secret: String) {
        sharedSecret = secret.trim()
    }

    fun start(hotspotProvider: () -> HotspotState, adbController: AdbController) {
        if (listeningJob != null && listeningJob?.isActive == true) return

        listeningJob = scope.launch(Dispatchers.IO) {
            try {
                serverSocket = DatagramSocket(port)
                serverSocket?.reuseAddress = true
                Log.i(TAG, "KnockListener bound to UDP 0.0.0.0:$port")

                val buffer = ByteArray(2048)
                val packet = DatagramPacket(buffer, buffer.size)

                while (isActive) {
                    try {
                        serverSocket?.receive(packet)
                    } catch (e: SocketException) {
                        break
                    }

                    val rawText = String(packet.data, packet.offset, packet.length, Charsets.UTF_8).trim()
                    val senderIp = packet.address.hostAddress ?: "unknown"
                    val hotspot = hotspotProvider()

                    Log.d(TAG, "Received UDP datagram from $senderIp: $rawText")

                    // 1. Verify Knock Payload
                    if (!rawText.startsWith(KNOCK_PREFIX)) {
                        Log.w(TAG, "Rejected datagram: missing ARCX-KNOCK header")
                        continue
                    }

                    val incomingSecret = rawText.removePrefix(KNOCK_PREFIX)
                    if (incomingSecret != sharedSecret) {
                        Log.e(TAG, "Security rejection: invalid knock secret from $senderIp")
                        continue
                    }

                    // 2. Reject if hotspot is not active or sender is not on local subnet
                    if (!isSenderAuthorized(senderIp, hotspot)) {
                        Log.w(TAG, "Sender $senderIp rejected: not on local hotspot subnet")
                        continue
                    }

                    Log.i(TAG, "Authenticated knock accepted from $senderIp!")
                    onKnockAccepted(senderIp, System.currentTimeMillis())

                    // 3. Trigger ADB activation via AdbController
                    adbController.enableForSession("Knock from $senderIp")

                    // Wait momentarily to ensure port resolution if freshly enabled
                    var targetPort = adbController.currentPort.value
                    if (targetPort == 0) {
                        kotlinx.coroutines.delay(400L)
                        targetPort = adbController.currentPort.value
                    }

                    // 4. Build JSON Response
                    val responseJson = buildResponsePayload(hotspot, targetPort, adbController.isAdbWifiActive.value)
                    val responseBytes = responseJson.toString().toByteArray(Charsets.UTF_8)
                    val replyPacket = DatagramPacket(
                        responseBytes,
                        responseBytes.size,
                        packet.address,
                        packet.port
                    )

                    try {
                        serverSocket?.send(replyPacket)
                        Log.i(TAG, "Replied to $senderIp with port $targetPort")
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to send knock reply: ${e.message}")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Knock server socket exception: ${e.message}")
            } finally {
                stop()
            }
        }
    }

    fun stop() {
        try {
            serverSocket?.close()
        } catch (e: Exception) {
            // ignore
        }
        serverSocket = null
        listeningJob?.cancel()
        listeningJob = null
    }

    private fun isSenderAuthorized(senderIp: String, hotspot: HotspotState): Boolean {
        // Local hotspot addresses are typically 192.168.43.x, 192.168.49.x, 10.x.x.x, or 127.0.0.1
        if (senderIp == "127.0.0.1" || senderIp == "localhost") return true

        if (hotspot.ipAddress.isNotEmpty()) {
            val prefix = hotspot.ipAddress.substringBeforeLast(".")
            if (senderIp.startsWith(prefix)) return true
        }

        return senderIp.startsWith("192.168.") || senderIp.startsWith("10.") || senderIp.startsWith("172.")
    }

    private fun buildResponsePayload(hotspot: HotspotState, adbPort: Int, isAdbWifi: Boolean): JSONObject {
        val json = JSONObject()

        // Query device name from settings or build properties
        val devName = try {
            Settings.Global.getString(context.contentResolver, "device_name")
        } catch (e: Exception) {
            null
        } ?: Build.MODEL

        json.put("device_name", devName)
        json.put("model", Build.MODEL)
        json.put("ip", hotspot.ipAddress.ifEmpty { "192.168.43.1" })
        json.put("adb_port", if (adbPort > 0) adbPort else 5555)
        json.put("adb_wifi_enabled", isAdbWifi)
        json.put("hotspot", hotspot.isEnabled)
        json.put("battery", queryBatteryLevel())

        return json
    }

    private fun queryBatteryLevel(): Int {
        return try {
            val filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            val intent = context.registerReceiver(null, filter)
            intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        } catch (e: Exception) {
            -1
        }
    }
}
