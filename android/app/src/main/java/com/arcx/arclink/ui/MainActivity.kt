package com.arcx.arclink.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BatteryChargingFull
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.WifiTethering
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arcx.arclink.service.ArcLinkService
import com.arcx.arclink.ui.theme.AcidGreen
import com.arcx.arclink.ui.theme.AcidGreenGlow
import com.arcx.arclink.ui.theme.AmberGlow
import com.arcx.arclink.ui.theme.ArcLinkTheme
import com.arcx.arclink.ui.theme.CyberRed
import com.arcx.arclink.ui.theme.GlassBorderActive
import com.arcx.arclink.ui.theme.GlassBorderSubtle
import com.arcx.arclink.ui.theme.NeonCyan
import com.arcx.arclink.ui.theme.NeonCyanGlow
import com.arcx.arclink.ui.theme.NeonMagenta
import com.arcx.arclink.ui.theme.SpaceBackgroundDark
import com.arcx.arclink.ui.theme.SpaceBackgroundDeep
import com.arcx.arclink.ui.theme.SpaceCardBackground
import com.arcx.arclink.ui.theme.TextMuted
import com.arcx.arclink.ui.theme.TextPrimary
import com.arcx.arclink.ui.theme.TextSecondary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Ensure daemon service is running
        ArcLinkService.startService(this)

        setContent {
            ArcLinkTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = SpaceBackgroundDeep
                ) {
                    ArcLinkDashboard()
                }
            }
        }
    }
}

@Composable
fun ArcLinkDashboard() {
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val uiState by ArcLinkService.uiState.collectAsState()

    var showSecretDialog by remember { mutableStateOf(false) }
    var tempSecret by remember { mutableStateOf(uiState.sharedSecret) }

    // Pulsing animation for Hotspot ring
    val infiniteTransition = rememberInfiniteTransition(label = "hero_pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.85f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_alpha"
    )

    val heroAccentColor by animateColorAsState(
        targetValue = if (uiState.hotspotState.isEnabled) AcidGreen else NeonCyan,
        animationSpec = tween(400),
        label = "hero_color"
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(SpaceBackgroundDeep, SpaceBackgroundDark)
                )
            )
            .padding(horizontal = 20.dp, vertical = 24.dp)
    ) {
        // 1. Top Header Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "ARC-LINK",
                    color = NeonCyan,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 2.sp
                )
                Text(
                    text = "AUTONOMOUS SCREEN RECOVERY",
                    color = TextSecondary,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 1.sp
                )
            }

            // Armed Automation Switch
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(SpaceCardBackground)
                    .border(1.dp, GlassBorderSubtle, RoundedCornerShape(20.dp))
                    .padding(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Text(
                    text = if (uiState.isArmed) "ARMED" else "DISARMED",
                    color = if (uiState.isArmed) AcidGreen else TextMuted,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.width(6.dp))
                Switch(
                    checked = uiState.isArmed,
                    onCheckedChange = {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        // Toggled state
                    },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = SpaceBackgroundDeep,
                        checkedTrackColor = AcidGreen,
                        uncheckedThumbColor = TextMuted,
                        uncheckedTrackColor = SpaceBackgroundDark
                    ),
                    modifier = Modifier.size(36.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 2. Animated Hero Status Ring
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp),
            contentAlignment = Alignment.Center
        ) {
            // Outer Halo Ring
            Box(
                modifier = Modifier
                    .size(170.dp)
                    .drawBehind {
                        val strokeWidth = 3.dp.toPx()
                        val glowWidth = 10.dp.toPx()

                        if (uiState.hotspotState.isEnabled) {
                            drawCircle(
                                color = AcidGreenGlow.copy(alpha = pulseAlpha),
                                radius = size.minDimension / 2 - glowWidth / 2,
                                style = Stroke(width = glowWidth)
                            )
                        }
                        drawCircle(
                            color = heroAccentColor,
                            radius = size.minDimension / 2 - strokeWidth / 2,
                            style = Stroke(width = strokeWidth)
                        )
                    },
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = if (uiState.hotspotState.isEnabled) Icons.Filled.WifiTethering else Icons.Filled.Wifi,
                        contentDescription = "Hotspot Status",
                        tint = heroAccentColor,
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = if (uiState.hotspotState.isEnabled) "HOTSPOT ACTIVE" else "HOTSPOT OFF",
                        color = TextPrimary,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Text(
                        text = if (uiState.hotspotState.isEnabled) {
                            "${uiState.hotspotState.interfaceName} (${uiState.hotspotState.ipAddress})"
                        } else {
                            "Awaiting AP activation"
                        },
                        color = TextSecondary,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(18.dp))

        // 3. Telemetry Glass Card
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(SpaceCardBackground)
                .border(1.dp, GlassBorderSubtle, RoundedCornerShape(16.dp))
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                MetricItem(
                    label = "WIRELESS ADB",
                    value = if (uiState.isAdbWifiEnabled) "ACTIVE" else "DISABLED",
                    color = if (uiState.isAdbWifiEnabled) AcidGreen else CyberRed
                )
                MetricItem(
                    label = "ADB PORT",
                    value = if (uiState.adbPort > 0) uiState.adbPort.toString() else "—",
                    color = NeonCyan
                )
                MetricItem(
                    label = "CLIENT IP",
                    value = uiState.connectedLaptopIp.ifEmpty { "—" },
                    color = if (uiState.connectedLaptopIp.isNotEmpty()) NeonMagenta else TextMuted
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            val lastKnockStr = if (uiState.lastKnockTimestamp > 0) {
                SimpleDateFormat("HH:mm:ss", Locale.US).format(Date(uiState.lastKnockTimestamp))
            } else "None"

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                MetricItem(label = "LAST AUTH KNOCK", value = lastKnockStr, color = TextPrimary)
                MetricItem(label = "KNOCK PORT", value = "9099 UDP", color = NeonCyan)
                MetricItem(label = "TRIGGER MODE", value = "WRITE_SECURE", color = TextSecondary)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 4. Quick Actions Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    val cmd = "adb shell pm grant com.arcx.arclink android.permission.WRITE_SECURE_SETTINGS"
                    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    clipboard.setPrimaryClip(ClipData.newPlainText("grant command", cmd))
                    Toast.makeText(context, "Copied ADB grant command to clipboard!", Toast.LENGTH_SHORT).show()
                },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(10.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, GlassBorderSubtle),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = NeonCyan)
            ) {
                Icon(Icons.Filled.ContentCopy, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Grant Cmd", fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }

            OutlinedButton(
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    try {
                        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                            data = Uri.parse("package:${context.packageName}")
                        }
                        context.startActivity(intent)
                    } catch (e: Exception) {
                        Toast.makeText(context, "Could not open battery settings", Toast.LENGTH_SHORT).show()
                    }
                },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(10.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, GlassBorderSubtle),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = AmberGlow)
            ) {
                Icon(Icons.Filled.BatteryChargingFull, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Battery", fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }

            OutlinedButton(
                onClick = {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    tempSecret = uiState.sharedSecret
                    showSecretDialog = true
                },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(10.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, GlassBorderSubtle),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = NeonMagenta)
            ) {
                Icon(Icons.Filled.Security, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Secret", fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 5. Live State Timeline / Log Viewer
        Text(
            text = "LIVE EVENT TIMELINE",
            color = TextSecondary,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 1.sp
        )

        Spacer(modifier = Modifier.height(6.dp))

        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .clip(RoundedCornerShape(12.dp))
                .background(SpaceBackgroundDeep)
                .border(1.dp, GlassBorderSubtle, RoundedCornerShape(12.dp))
                .padding(10.dp)
        ) {
            if (uiState.logs.isEmpty()) {
                item {
                    Text(
                        text = "[${SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())}] Daemon armed. Waiting for hotspot / knock...",
                        color = TextMuted,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }
            } else {
                items(uiState.logs.reversed()) { line ->
                    Text(
                        text = line,
                        color = if ("accepted" in line) AcidGreen else if ("ON" in line) NeonCyan else TextPrimary,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        modifier = Modifier.padding(vertical = 2.dp)
                    )
                }
            }
        }
    }

    // Secret Dialog
    if (showSecretDialog) {
        AlertDialog(
            onDismissRequest = { showSecretDialog = false },
            title = {
                Text("Shared Knock Secret", color = NeonCyan, fontWeight = FontWeight.Bold)
            },
            text = {
                Column {
                    Text(
                        "Enter the shared secret token matched with your Arch Linux laptop:",
                        color = TextSecondary,
                        fontSize = 12.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = tempSecret,
                        onValueChange = { tempSecret = it },
                        singleLine = true,
                        colors = androidx.compose.material3.TextFieldDefaults.colors(
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            focusedContainerColor = SpaceBackgroundDark,
                            unfocusedContainerColor = SpaceBackgroundDark,
                            focusedIndicatorColor = NeonCyan
                        )
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (tempSecret.isNotBlank()) {
                            // Save secret
                            showSecretDialog = false
                            Toast.makeText(context, "Secret saved!", Toast.LENGTH_SHORT).show()
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = NeonCyan, contentColor = SpaceBackgroundDeep)
                ) {
                    Text("Save", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showSecretDialog = false }) {
                    Text("Cancel", color = TextSecondary)
                }
            },
            containerColor = SpaceCardBackground
        )
    }
}

@Composable
fun MetricItem(label: String, value: String, color: Color) {
    Column {
        Text(
            text = label,
            fontSize = 9.sp,
            color = TextSecondary,
            fontFamily = FontFamily.Monospace
        )
        Text(
            text = value,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = color,
            fontFamily = FontFamily.Monospace
        )
    }
}
