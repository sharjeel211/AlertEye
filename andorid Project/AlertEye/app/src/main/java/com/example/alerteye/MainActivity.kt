package com.example.alerteye

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class MainActivity : AppCompatActivity() {

    private val client = OkHttpClient()
    private val SERVER_URL = "https://alerteye.online"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("alerteye", MODE_PRIVATE)
        if (prefs.getString("email", null) != null) {
            startActivity(Intent(this, DashboardActivity::class.java))
            finish()
            return
        }

        setContentView(R.layout.activity_main)

        val emailField = findViewById<EditText>(R.id.emailField)
        val passField  = findViewById<EditText>(R.id.passField)
        val loginBtn   = findViewById<Button>(R.id.loginBtn)
        val errorText  = findViewById<TextView>(R.id.errorText)

        loginBtn.setOnClickListener {
            val email = emailField.text.toString().trim()
            val pass  = passField.text.toString().trim()

            if (email.isEmpty() || pass.isEmpty()) {
                errorText.text = "Enter email and password"
                return@setOnClickListener
            }

            loginBtn.isEnabled = false
            loginBtn.text = "Logging in..."
            errorText.text = ""

            val json = JSONObject()
            json.put("email", email)
            json.put("password", pass)

            val body = json.toString().toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url("$SERVER_URL/api/auth")
                .post(body)
                .build()

            client.newCall(request).enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    runOnUiThread {
                        errorText.text = "Cannot connect to server"
                        loginBtn.isEnabled = true
                        loginBtn.text = "Login"
                    }
                }

                override fun onResponse(call: Call, response: Response) {
                    val responseBody = response.body?.string()
                    runOnUiThread {
                        loginBtn.isEnabled = true
                        loginBtn.text = "Login"
                        try {
                            val res = JSONObject(responseBody ?: "{}")
                            if (response.isSuccessful && res.optBoolean("success", false)) {
                                val user = res.getJSONObject("user")
                                prefs.edit()
                                    .putString("email", email)
                                    .putString("password", pass)
                                    .putString("uid", user.optString("uid", ""))
                                    .putString("username", user.optString("name", email))
                                    .putString("subscription_status",
                                        if (user.optBoolean("subscription_active", false))
                                            "active" else "inactive")
                                    .putInt("days_left", user.optInt("days_remaining", 0))
                                    .apply()
                                startActivity(Intent(this@MainActivity, DashboardActivity::class.java))
                                finish()
                            } else {
                                errorText.text = res.optString("error", "Login failed")
                            }
                        } catch (e: Exception) {
                            errorText.text = "Error: ${e.message}"
                        }
                    }
                }
            })
        }
    }
}
