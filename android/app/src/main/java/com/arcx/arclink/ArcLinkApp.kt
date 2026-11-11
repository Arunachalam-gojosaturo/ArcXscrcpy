package com.arcx.arclink

import android.app.Application
import android.util.Log
import com.arcx.arclink.service.ArcLinkService

/**
 * ARC-LINK Application class.
 * Autostarts the background recovery service upon process initialization.
 */
class ArcLinkApp : Application() {

    companion object {
        private const val TAG = "ARC_App"
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "ArcLinkApp initializing...")

        try {
            ArcLinkService.startService(this)
        } catch (e: Exception) {
            Log.e(TAG, "Could not start ArcLinkService from App onCreate: ${e.message}")
        }
    }
}
