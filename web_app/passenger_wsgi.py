import os
import sys

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from app import app as application, create_admin

try:
    create_admin()
except Exception as e:
    print(f"[passenger_wsgi] create_admin failed: {e}", file=sys.stderr)
