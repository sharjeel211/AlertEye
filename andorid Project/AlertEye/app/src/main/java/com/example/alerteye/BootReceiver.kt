package com.example.alerteye

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val prefs = context.getSharedPreferences("alerteye", Context.MODE_PRIVATE)
            if (prefs.getString("email", null) != null) {

                val serviceIntent = Intent(context, AlertService::class.java)
                ContextCompat.startForegroundService(context, serviceIntent)
            }
        }
    }
}
