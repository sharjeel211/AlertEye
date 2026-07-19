"""
AlertEye — Firebase Realtime Database notifier

On a confirmed detection, writes the alert to the Firebase Realtime Database
at /alerts/{uid} so the per-account Android app can read it.

Firebase is OPTIONAL. If the service account JSON file is not present, this
notifier logs a single warning and every method becomes a silent no-op — the
desktop app runs exactly as it would without Firebase, and never crashes.

The service account path is read from the FIREBASE_SERVICE_ACCOUNT_PATH
environment variable (loaded from desktop_app/.env by main.py via
python-dotenv, mirroring utils/auth_manager.py), defaulting to
"firebase_service_account.json" in the desktop_app root.
"""

import os
import logging

logger = logging.getLogger('alerteye')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL = (
    "https://alerteye-247b2-default-rtdb.asia-southeast1.firebasedatabase.app"
)

class FirebaseNotifier:
    """
    Writes detection alerts to Firebase Realtime Database at /alerts/{uid}.

    Initializes firebase-admin only if the service account file exists. When it
    doesn't, the notifier disables itself gracefully and all calls are no-ops.
    All Firebase calls are wrapped so failures are logged but never raised to
    the caller.
    """

    def __init__(self):
        self._ready = False
        self._db = None

        sa_path = os.environ.get(
            'FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase_service_account.json'
        )

        if not os.path.isabs(sa_path):
            sa_path = os.path.join(PROJECT_ROOT, sa_path)

        if not os.path.exists(sa_path):
            logger.warning(
                "Firebase service account not found at '%s' — Firebase alerts "
                "disabled. Set FIREBASE_SERVICE_ACCOUNT_PATH in desktop_app/.env "
                "to enable per-account alerts for the Android app.", sa_path
            )
            return

        try:
            import firebase_admin
            from firebase_admin import credentials, db

            if not firebase_admin._apps:
                cred = credentials.Certificate(sa_path)
                firebase_admin.initialize_app(
                    cred, {'databaseURL': DATABASE_URL}
                )
            self._db = db
            self._ready = True
            logger.info("✓ Firebase notifier ready — RTDB at %s", DATABASE_URL)
        except Exception as e:
            logger.warning("Firebase initialization failed: %s", e)
            self._ready = False
            self._db = None

    @property
    def is_ready(self) -> bool:
        return self._ready

    def send_alert(self, uid: str, alert_type: str, confidence: float,
                   camera_name: str):
        """
        Write an alert to /alerts/{uid}. No-op if Firebase isn't configured.
        Never raises — failures are logged.
        """
        if not self._ready or not self._db:
            return
        try:
            ref = self._db.reference(f"/alerts/{uid}")
            ref.set({
                'alert_type': alert_type,
                'confidence': confidence,
                'camera_name': camera_name,
                'timestamp': {'.sv': 'timestamp'},
            })
            logger.info("✅ Firebase alert written to /alerts/%s", uid)
        except Exception as e:
            logger.error("Firebase send_alert failed: %s", e)
