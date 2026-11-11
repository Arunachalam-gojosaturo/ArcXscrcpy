package com.arcx.arclink

import com.arcx.arclink.model.HotspotState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HotspotDetectorTest {

    @Test
    fun testHotspotStateDefault() {
        val state = HotspotState()
        assertFalse(state.isEnabled)
        assertEquals("", state.interfaceName)
        assertEquals("", state.ipAddress)
        assertEquals("IDLE", state.detectionSource)
    }

    @Test
    fun testHotspotActiveState() {
        val state = HotspotState(
            isEnabled = true,
            interfaceName = "ap0",
            ipAddress = "192.168.43.1",
            detectionSource = "INTERFACE (ap0)"
        )
        assertTrue(state.isEnabled)
        assertEquals("ap0", state.interfaceName)
        assertEquals("192.168.43.1", state.ipAddress)
        assertTrue(state.detectionSource.contains("ap0"))
    }
}
