"""
AlertEye Desktop — Auth Manager
Handles login, subscription validation, and periodic heartbeat checks.
"""

import json
import os
import threading
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any

DEFAULT_SERVER = "https://alerteye.online"

class AuthManager:
    """
    Manages authentication and subscription state for the desktop app.
    Communicates with the AlertEye web portal API.
    """

    def __init__(self, server_url: str = DEFAULT_SERVER):
        self.server_url = server_url.rstrip('/')
        self._user_data: Optional[Dict[str, Any]] = None
        self._session_active = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        self._on_subscription_change = None
        self._on_modules_change = None

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate with the web portal.
        Returns: {'success': bool, 'error': str (if failed), user data if success}
        """
        try:
            resp = requests.post(
                f"{self.server_url}/api/auth",
                json={'email': email, 'password': password},
                timeout=10
            )
            data = resp.json()

            if data.get('success'):
                self._user_data = data['user']
                self._session_active = True
                self._save_session()
                self._start_heartbeat()
                return {'success': True, **data['user']}
            else:
                return {'success': False, 'error': data.get('error', 'Login failed')}

        except requests.ConnectionError:
            return {'success': False, 'error': 'Cannot connect to server. Check your internet connection.'}
        except requests.Timeout:
            return {'success': False, 'error': 'Server timeout. Try again.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def logout(self):
        self._session_active = False
        self._user_data = None
        self._running = False
        self._clear_session()

    def _save_session(self):
        """Save session to disk so user stays logged in after restart."""
        try:
            import os
            session_path = os.path.join(os.path.expanduser('~'), '.alerteye_session.json')
            with open(session_path, 'w') as f:
                json.dump({
                    'server_url': self.server_url,
                    'uid': self._user_data.get('uid'),
                    'email': self._user_data.get('email'),
                    'name': self._user_data.get('name'),
                }, f)
        except Exception:
            pass

    def _clear_session(self):
        try:
            import os
            session_path = os.path.join(os.path.expanduser('~'), '.alerteye_session.json')
            if os.path.exists(session_path):
                os.remove(session_path)
        except Exception:
            pass

    def load_saved_session(self) -> bool:
        """Try to resume a saved session. Returns True if credentials exist."""
        try:
            import os
            session_path = os.path.join(os.path.expanduser('~'), '.alerteye_session.json')
            if not os.path.exists(session_path):
                return False
            with open(session_path) as f:
                data = json.load(f)
            self.server_url = data.get('server_url', self.server_url)
            return bool(data.get('uid') and data.get('email'))
        except Exception:
            return False

    def get_saved_email(self) -> str:
        try:
            import os
            session_path = os.path.join(os.path.expanduser('~'), '.alerteye_session.json')
            with open(session_path) as f:
                return json.load(f).get('email', '')
        except Exception:
            return ''

    @property
    def is_logged_in(self) -> bool:
        return self._session_active and self._user_data is not None

    @property
    def is_subscription_active(self) -> bool:
        if not self._user_data:
            return False
        return self._user_data.get('subscription_active', False)

    @property
    def enabled_modules(self) -> list:
        if not self._user_data or not self.is_subscription_active:
            return []
        return self._user_data.get('modules', [])

    @property
    def user_name(self) -> str:
        return self._user_data.get('name', 'User') if self._user_data else ''

    @property
    def user_email(self) -> str:
        return self._user_data.get('email', '') if self._user_data else ''

    @property
    def user_phone(self) -> str:
        """Account holder's phone, entered during registration (contact info)."""
        return self._user_data.get('phone', '') if self._user_data else ''

    @property
    def uid(self) -> str:
        return self._user_data.get('uid', '') if self._user_data else ''

    @property
    def days_remaining(self) -> int:
        return self._user_data.get('days_remaining', 0) if self._user_data else 0

    @property
    def subscription_end(self) -> Optional[str]:
        if not self._user_data:
            return None
        return self._user_data.get('subscription_end')

    def get_emergency_numbers(self) -> Dict[str, str]:
        if not self._user_data:
            return {'police': '911', 'fire': '911', 'ambulance': '911'}
        return {
            'account_phone': self._user_data.get('phone', ''),
            'police': self._user_data.get('police_number', '911'),
            'fire': self._user_data.get('fire_number', '911'),
            'ambulance': self._user_data.get('ambulance_number', '911'),
            'emergency': self._user_data.get('emergency_phone', ''),
        }

    def is_module_enabled(self, module_name: str) -> bool:
        return module_name in self.enabled_modules

    def _start_heartbeat(self):
        """Ping server every 30 minutes to check subscription status."""
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        while self._running and self._session_active:
            time.sleep(1800)
            if not self._running:
                break
            self._check_subscription()

    def _check_subscription(self):
        try:
            resp = requests.post(
                f"{self.server_url}/api/heartbeat",
                json={'uid': self.uid},
                timeout=10
            )
            data = resp.json()
            old_active = self.is_subscription_active
            old_modules = set(self.enabled_modules)

            self._user_data['subscription_active'] = data.get('active', False)
            self._user_data['modules'] = data.get('modules', [])
            self._user_data['days_remaining'] = data.get('days_remaining', 0)

            if old_active != self.is_subscription_active and self._on_subscription_change:
                self._on_subscription_change(self.is_subscription_active)

            if old_modules != set(self.enabled_modules) and self._on_modules_change:
                self._on_modules_change(self.enabled_modules)

        except Exception:
            pass

    def force_check(self):
        """Manually trigger a subscription check."""
        threading.Thread(target=self._check_subscription, daemon=True).start()

    def set_subscription_change_callback(self, callback):
        self._on_subscription_change = callback

    def set_modules_change_callback(self, callback):
        self._on_modules_change = callback

    def report_alert(self, alert_type: str, confidence: float,
                     camera_name: str, screenshot_path: str = '') -> bool:
        """Post a detection alert to the web portal (for logging + email)."""
        if not self.is_logged_in:
            return False
        try:
            resp = requests.post(
                f"{self.server_url}/api/alert",
                json={
                    'uid': self.uid,
                    'api_secret': os.environ.get('DESKTOP_API_SECRET', ''),
                    'alert_type': alert_type,
                    'confidence': confidence,
                    'camera_name': camera_name,
                    'screenshot_path': screenshot_path,
                },
                timeout=8
            )
            return resp.ok
        except Exception:
            return False
