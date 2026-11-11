package com.arcx.arclink

import com.arcx.arclink.model.KnockReplyPayload
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class KnockPayloadTest {

    @Test
    fun testKnockJsonSerialization() {
        val payload = KnockReplyPayload(
            device_name = "Pixel 7 Pro",
            model = "GE2AE",
            ip = "192.168.43.1",
            adb_port = 39821,
            adb_wifi_enabled = true,
            hotspot = true,
            battery = 85
        )

        val json = JSONObject().apply {
            put("device_name", payload.device_name)
            put("model", payload.model)
            put("ip", payload.ip)
            put("adb_port", payload.adb_port)
            put("adb_wifi_enabled", payload.adb_wifi_enabled)
            put("hotspot", payload.hotspot)
            put("battery", payload.battery)
        }

        assertEquals("Pixel 7 Pro", json.getString("device_name"))
        assertEquals(39821, json.getInt("adb_port"))
        assertTrue(json.getBoolean("adb_wifi_enabled"))
        assertEquals(85, json.getInt("battery"))
    }

    @Test
    fun testKnockPrefixValidation() {
        val validKnock = "ARCX-KNOCK:arcx_secure_token_broken_screen"
        assertTrue(validKnock.startsWith("ARCX-KNOCK:"))

        val secret = validKnock.removePrefix("ARCX-KNOCK:")
        assertEquals("arcx_secure_token_broken_screen", secret)
    }
}
