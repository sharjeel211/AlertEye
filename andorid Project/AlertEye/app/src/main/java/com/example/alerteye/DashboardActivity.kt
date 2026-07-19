package com.example.alerteye

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.firebase.database.*

class DashboardActivity : AppCompatActivity() {

    private lateinit var firebaseRef: DatabaseReference

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        startAlertService()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dashboard)

        val prefs = getSharedPreferences("alerteye", MODE_PRIVATE)

        val welcomeText = findViewById<TextView>(R.id.welcomeText)
        val statusText  = findViewById<TextView>(R.id.statusText)
        val daysText    = findViewById<TextView>(R.id.daysText)
        val renewBtn    = findViewById<Button>(R.id.renewBtn)
        val logoutBtn   = findViewById<Button>(R.id.logoutBtn)
        val alertStatus = findViewById<TextView>(R.id.alertStatus)

        val username = prefs.getString("username", "User") ?: "User"
        val status   = prefs.getString("subscription_status", "unknown") ?: "unknown"
        val days     = prefs.getInt("days_left", 0)

        welcomeText.text = "Welcome, $username"
        statusText.text  = "Subscription: ${status.uppercase()}"
        daysText.text    = "Days left: $days"

        if (days <= 7) {
            daysText.setTextColor(getColor(android.R.color.holo_red_light))
        }

        requestBatteryExemption(prefs)

        renewBtn.setOnClickListener {
            val url = "https://alerteye.online/dashboard"
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }

        logoutBtn.setOnClickListener {
            stopService(Intent(this, AlertService::class.java))
            prefs.edit().clear().apply()
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this, Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    startAlertService()
                }
                else -> {
                    requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        } else {
            startAlertService()
        }

        val uid = prefs.getString("uid", null)
        if (!uid.isNullOrEmpty()) {
            firebaseRef = FirebaseDatabase.getInstance().getReference("alerts").child(uid)
            firebaseRef.addValueEventListener(object : ValueEventListener {
                override fun onDataChange(snapshot: DataSnapshot) {
                    if (!snapshot.exists()) {
                        alertStatus.text = "✅ All Clear"
                        alertStatus.setTextColor(getColor(android.R.color.holo_green_light))
                        return
                    }
                    val alertType = snapshot.child("alert_type").getValue(String::class.java)
                    val cameraName = snapshot.child("camera_name").getValue(String::class.java) ?: ""
                    val timestamp = snapshot.child("timestamp").getValue(Long::class.java) ?: 0L
                    val ageMs = System.currentTimeMillis() - timestamp

                    if (alertType == null || ageMs > 5 * 60 * 1000) {

                        alertStatus.text = "✅ All Clear"
                        alertStatus.setTextColor(getColor(android.R.color.holo_green_light))
                    } else {
                        alertStatus.text = "⚠️ ${alertType.uppercase()} on $cameraName"
                        alertStatus.setTextColor(getColor(android.R.color.holo_red_light))
                    }
                }
                override fun onCancelled(error: DatabaseError) {}
            })
        } else {
            alertStatus.text = "⚠️ Account ID missing — please log out and log back in"
            alertStatus.setTextColor(getColor(android.R.color.holo_red_light))
        }
    }

    private fun requestBatteryExemption(prefs: android.content.SharedPreferences) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return
        try {
            val pm = getSystemService(POWER_SERVICE) as PowerManager
            if (pm.isIgnoringBatteryOptimizations(packageName)) return
            if (prefs.getBoolean("battery_exemption_asked", false)) return
            prefs.edit().putBoolean("battery_exemption_asked", true).apply()
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun startAlertService() {
        try {
            val serviceIntent = Intent(this, AlertService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
