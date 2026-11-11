package com.arcx.arclink.service

import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.os.SystemClock
import android.util.Log
import androidx.core.app.NotificationCompat
import com.arcx.arclink.model.AppUiState
import com.arcx.arclink.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Foreground Service maintaining ARC-LINK system state.
 * Uses START_STICKY, a partial wake lock, and an AlarmManager watchdog.
 */
class ArcLinkService : Service() {

    companion object {
        private const val TAG = "ARC_LinkService"
        const val CHANNEL_ID = "arclink_daemon_channel"
        const val NOTIFICATION_ID = 42001

        private val _uiState = MutableStateFlow(AppUiState())
        val uiState: StateFlow<AppUiState> = _uiState.asStateFlow()

        fun startService(context: Context) {
            val intent = Intent(context, ArcLinkService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }
    }

    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var wakeLock: PowerManager.WakeLock? = null

    private lateinit var hotspotMonitor: HotspotMonitor
    private lateinit var adbController: AdbController
    private lateinit var knockListener: KnockListener

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "ArcLinkService onCreate()")

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("ARC-LINK Daemon Active", "Monitoring Hotspot & ADB..."))

        acquireWakeLock()
        setupAlarmManagerRestart()

        // Initialize core subsystems
        hotspotMonitor = HotspotMonitor(this, serviceScope)
        adbController = AdbController(this, serviceScope)
        knockListener = KnockListener(this, serviceScope) { laptopIp, timestamp ->
            appendLog("Authenticated knock accepted from $laptopIp")
            _uiState.value = _uiState.value.copy(
                connectedLaptopIp = laptopIp,
                lastKnockTimestamp = timestamp
            )
            updateNotification("Hotspot Connected", "Client $laptopIp paired via ADB")
        }

        // Observe Hotspot state changes
        serviceScope.launch {
            hotspotMonitor.hotspotState.collect { hs ->
                _uiState.value = _uiState.value.copy(hotspotState = hs)
                if (hs.isEnabled) {
                    appendLog("Hotspot turned ON (${hs.interfaceName} - ${hs.ipAddress})")
                    adbController.resetSessionGuard()
                    knockListener.start({ hotspotMonitor.hotspotState.value }, adbController)
                    updateNotification("Hotspot Active", "Listening on :9099. Waiting for laptop knock...")
                } else {
                    appendLog("Hotspot turned OFF. Disabling wireless debugging.")
                    adbController.disableForSession("Hotspot OFF")
                    updateNotification("Hotspot Inactive", "Awaiting Wi-Fi hotspot activation")
                }
            }
        }

        // Observe ADB state changes
        serviceScope.launch {
            adbController.isAdbWifiActive.collect { active ->
                _uiState.value = _uiState.value.copy(isAdbWifiEnabled = active)
            }
        }
        serviceScope.launch {
            adbController.currentPort.collect { port ->
                _uiState.value = _uiState.value.copy(adbPort = port)
            }
        }

        hotspotMonitor.start()
        knockListener.start({ hotspotMonitor.hotspotState.value }, adbController)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "ArcLinkService onStartCommand()")
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        Log.w(TAG, "ArcLinkService onDestroy() - cleaning up")
        hotspotMonitor.stop()
        knockListener.stop()
        adbController.stopNsdDiscovery()
        releaseWakeLock()
        serviceScope.cancel()

        // Restart self via AlarmManager fallback if killed unexpectedly
        scheduleServiceRestart()
        super.onDestroy()
    }

    private fun acquireWakeLock() {
        val pm = getSystemService(Context.POWER_SERVICE) as? PowerManager
        wakeLock = pm?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ArcLink::ServiceWakeLock")
        wakeLock?.acquire(12 * 60 * 60 * 1000L) // 12 hours max safety
    }

    private fun releaseWakeLock() {
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            // ignore
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "ARC-LINK Autonomous Recovery",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent background monitor for screen recovery via wireless ADB"
                setShowBadge(false)
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(title: String, content: String): Notification {
        val tapIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            tapIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(content)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification(title: String, content: String) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
        nm?.notify(NOTIFICATION_ID, buildNotification(title, content))
    }

    private fun setupAlarmManagerRestart() {
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val restartIntent = Intent(this, BootReceiver::class.java).apply {
            action = "com.arcx.arclink.ACTION_WATCHDOG_CHECK"
        }
        val pending = PendingIntent.getBroadcast(
            this,
            9001,
            restartIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Ping watchdog every 15 minutes
        alarmManager.setInexactRepeating(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            SystemClock.elapsedRealtime() + 15 * 60 * 1000L,
            15 * 60 * 1000L,
            pending
        )
    }

    private fun scheduleServiceRestart() {
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val restartIntent = Intent(this, BootReceiver::class.java).apply {
            action = "com.arcx.arclink.ACTION_SERVICE_RESTART"
        }
        val pending = PendingIntent.getBroadcast(
            this,
            9002,
            restartIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager.setExactAndAllowWhileIdle(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            SystemClock.elapsedRealtime() + 3000L,
            pending
        )
    }

    private fun appendLog(msg: String) {
        val timeStr = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date())
        val logEntry = "[$timeStr] $msg"
        val currentLogs = _uiState.value.logs.takeLast(100).toMutableList()
        currentLogs.add(logEntry)
        _uiState.value = _uiState.value.copy(logs = currentLogs)
    }
}
