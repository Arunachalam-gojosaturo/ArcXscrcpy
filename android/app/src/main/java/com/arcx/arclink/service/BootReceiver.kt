package com.arcx.arclink.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * Autostart Receiver invoked on device boot, package update, and alarm pings.
 * DirectBootAware ensures execution even before first user unlock if storage is unencrypted.
 */
class BootReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "ARC_BootReceiver"
    }

    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: "null"
        Log.i(TAG, "BootReceiver triggered with action: $action")

        when (action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_LOCKED_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED,
            "android.intent.action.QUICKBOOT_POWERON",
            "com.htc.intent.action.QUICKBOOT_POWERON",
            "com.arcx.arclink.ACTION_SERVICE_RESTART",
            "com.arcx.arclink.ACTION_WATCHDOG_CHECK" -> {
                Log.i(TAG, "Starting ArcLinkService daemon from BootReceiver...")
                try {
                    ArcLinkService.startService(context)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to start ArcLinkService from broadcast: ${e.message}")
                }
            }
            else -> {
                Log.d(TAG, "Unhandled action: $action")
            }
        }
    }
}
