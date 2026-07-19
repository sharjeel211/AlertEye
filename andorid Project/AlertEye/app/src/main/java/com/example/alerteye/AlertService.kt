package com.example.alerteye

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import com.google.firebase.database.*

class AlertService : Service() {

    private var firebaseRef: DatabaseReference? = null
    private var alertListener: ValueEventListener? = null
    private var mediaPlayer: MediaPlayer? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private val CHANNEL_ID = "alerteye_channel"
    private val NOTIF_ID = 1001

    private var lastAlertedTimestamp: Long = -1L

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        acquireWakeLock()
        val notification = buildPersistentNotification("Monitoring active...")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIF_ID, notification)
        }
        listenForAlerts()
    }

    private fun acquireWakeLock() {
        try {
            wakeLock = (getSystemService(POWER_SERVICE) as PowerManager).newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK, "AlertEye::AlertListener"
            ).apply {
                setReferenceCounted(false)
                acquire()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun listenForAlerts() {
        val prefs = getSharedPreferences("alerteye", MODE_PRIVATE)
        val uid = prefs.getString("uid", null)

        if (uid.isNullOrEmpty()) {

            android.util.Log.e("AlertService", "No uid in prefs — Firebase alert listener not attached")
            return
        }

        lastAlertedTimestamp = prefs.getLong("last_alerted_ts", -1L)

        firebaseRef = FirebaseDatabase.getInstance().getReference("alerts").child(uid)
        firebaseRef?.keepSynced(true)
        val listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                if (!snapshot.exists()) return

                val alertType = snapshot.child("alert_type").getValue(String::class.java) ?: return
                val cameraName = snapshot.child("camera_name").getValue(String::class.java) ?: ""
                val confidence = snapshot.child("confidence").getValue(Double::class.java) ?: 0.0

                val timestamp = snapshot.child("timestamp").getValue(Long::class.java) ?: 0L

                if (timestamp > lastAlertedTimestamp) {
                    lastAlertedTimestamp = timestamp
                    prefs.edit().putLong("last_alerted_ts", timestamp).apply()
                    val message = "${alertType.uppercase()} detected on $cameraName " +
                            "(${(confidence * 100).toInt()}%)"
                    triggerAlarm(message)
                }
            }
            override fun onCancelled(error: DatabaseError) {
                android.util.Log.e("AlertService", "Firebase listener cancelled: ${error.message}")
            }
        }
        alertListener = listener
        firebaseRef?.addValueEventListener(listener)
    }

    private fun triggerAlarm(message: String) {
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                val afd = assets.openFd("alarm.mp3")
                setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                isLooping = true
                prepare()
                start()
            }
        } catch (e: Exception) { e.printStackTrace() }

        val stopIntent = Intent(this, AlertService::class.java).apply { action = "STOP_ALARM" }
        val stopPending = PendingIntent.getService(this, 0, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

        val openIntent = Intent(this, AlarmActivity::class.java).apply {
            putExtra("alert_message", message)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        val openPending = PendingIntent.getActivity(this, 1, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("⚠️ ALERTEYE — ALERT!")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(false).setOngoing(true)
            .setFullScreenIntent(openPending, true)
            .setContentIntent(openPending)
            .addAction(android.R.drawable.ic_delete, "STOP ALARM", stopPending)
            .build()

        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).notify(NOTIF_ID, notification)
    }

    private fun stopAlarm() {

        mediaPlayer?.stop(); mediaPlayer?.release(); mediaPlayer = null
    }

    private fun updateNotification(text: String) {
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
            .notify(NOTIF_ID, buildPersistentNotification(text))
    }

    private fun buildPersistentNotification(text: String): Notification {
        val openPending = PendingIntent.getActivity(this, 2,
            Intent(this, DashboardActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val stopIntent = Intent(this, AlertService::class.java).apply { action = "STOP_SERVICE" }
        val stopPending = PendingIntent.getService(this, 3, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AlertEye").setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(openPending)
            .addAction(android.R.drawable.ic_delete, "Stop Service", stopPending)
            .setOngoing(true).build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "STOP_ALARM" -> { stopAlarm(); updateNotification("Monitoring active...") }
            "STOP_SERVICE" -> { stopAlarm(); stopSelf() }
        }
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        val restartIntent = Intent(applicationContext, AlertService::class.java)
        val pendingIntent = PendingIntent.getService(
            applicationContext, 1, restartIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        val alarmManager = getSystemService(ALARM_SERVICE) as AlarmManager
        alarmManager.set(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            SystemClock.elapsedRealtime() + 1000,
            pendingIntent
        )
        super.onTaskRemoved(rootIntent)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "AlertEye Alerts",
                NotificationManager.IMPORTANCE_HIGH).apply {
                description = "AlertEye surveillance alerts"
                enableVibration(true); setShowBadge(true)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAlarm()
        alertListener?.let { firebaseRef?.removeEventListener(it) }
        if (wakeLock?.isHeld == true) wakeLock?.release()
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
