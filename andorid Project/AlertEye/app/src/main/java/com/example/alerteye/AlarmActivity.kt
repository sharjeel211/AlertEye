package com.example.alerteye

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class AlarmActivity : AppCompatActivity() {

    private val handler = Handler(Looper.getMainLooper())
    private val autoDismiss = Runnable { dismiss() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_alarm)

        val message = intent.getStringExtra("alert_message") ?: "ALERT DETECTED"
        findViewById<TextView>(R.id.alarmText).text = message

        findViewById<Button>(R.id.dismissBtn).setOnClickListener { dismiss() }

        handler.postDelayed(autoDismiss, 60000)
    }

    private fun dismiss() {
        handler.removeCallbacks(autoDismiss)
        val stopIntent = Intent(this, AlertService::class.java).apply { action = "STOP_ALARM" }
        startService(stopIntent)
        finish()
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(autoDismiss)
    }
}
