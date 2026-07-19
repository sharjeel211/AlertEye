package com.example.alerteye

import android.app.Application
import com.google.firebase.database.FirebaseDatabase

class AlertEyeApp : Application() {
    override fun onCreate() {
        super.onCreate()
        try {
            FirebaseDatabase.getInstance().setPersistenceEnabled(true)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
