from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os, uuid, json, threading, secrets, io, random

import requests
import stripe

app = Flask(__name__)
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    import warnings
    warnings.warn(
        "SECRET_KEY env var not set — using a temporary key. "
        "All sessions will be lost on every restart. Set SECRET_KEY in .env for production.",
        stacklevel=1
    )
    _secret_key = secrets.token_hex(32)
app.config['SECRET_KEY'] = _secret_key

_database_url = os.environ.get('DATABASE_URL')
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to your .env (local) or cPanel app "
        "environment (Namecheap), e.g.\n"
        "  DATABASE_URL=mysql+pymysql://user:password@localhost/alerteye"
    )
app.config['SQLALCHEMY_DATABASE_URI'] = _database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
}

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'noreply@alerteye.com')

app.config['APP_DOWNLOAD_URL'] = os.environ.get('APP_DOWNLOAD_URL', 'http://localhost:5000/download/app')
app.config['DESKTOP_DOWNLOAD_URL'] = os.environ.get('DESKTOP_DOWNLOAD_URL', '')
app.config['ANDROID_DOWNLOAD_URL'] = os.environ.get('ANDROID_DOWNLOAD_URL', '')

app.config['STRIPE_PUBLISHABLE_KEY'] = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY', '')
app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
stripe.api_key = app.config['STRIPE_SECRET_KEY']

app.config['PAYMENT_CURRENCY'] = os.environ.get('PAYMENT_CURRENCY', 'usd').lower()
app.config['PUBLIC_BASE_URL'] = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:5000').rstrip('/')

PLANS = {
    'monthly':   {'label': 'Monthly Plan',   'days': 30,  'price': float(os.environ.get('PRICE_MONTHLY', 49))},
    'quarterly': {'label': 'Quarterly Plan', 'days': 90,  'price': float(os.environ.get('PRICE_QUARTERLY', 129))},
    'yearly':    {'label': 'Yearly Plan',    'days': 365, 'price': float(os.environ.get('PRICE_YEARLY', 449))},
}

app.config['COMPANY_NAME'] = os.environ.get('COMPANY_NAME', 'AlertEye')
app.config['COMPANY_ADDRESS'] = os.environ.get('COMPANY_ADDRESS', 'AlertEye Surveillance Systems')
app.config['COMPANY_EMAIL'] = os.environ.get('COMPANY_EMAIL', 'noreply@alerteye.com')

app.config['OPENROUTER_API_KEY'] = os.environ.get('OPENROUTER_API_KEY', '')
app.config['OPENROUTER_MODEL'] = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-oss-120b:free')
app.config['OPENROUTER_FALLBACK_MODEL'] = os.environ.get('OPENROUTER_FALLBACK_MODEL', 'openai/gpt-oss-20b:free')

INVOICE_DIR = os.path.join(os.path.dirname(__file__), 'instance', 'invoices')
os.makedirs(INVOICE_DIR, exist_ok=True)

OTP_TTL_MINUTES = 10

db = SQLAlchemy(app)
mail = Mail(app)

from flask import got_request_exception

def _log_request_exception(sender, exception, **extra):
    import traceback
    tb = traceback.format_exc()
    try:
        with open(os.path.join(os.path.dirname(__file__), 'instance', 'last_error.txt'),
                  'a', encoding='utf-8') as f:
            f.write('\n' + '=' * 60 + '\n' + datetime.utcnow().isoformat() + '\n' + tb)
    except Exception:
        pass
    print(tb)

got_request_exception.connect(_log_request_exception, app)

@app.context_processor
def inject_globals():
    from datetime import datetime
    def pending_applications_count():
        return User.query.filter_by(role='client', status='pending').count()
    return dict(
        pending_applications_count=pending_applications_count,
        now=datetime.utcnow(),
        session=session,
        PLANS=PLANS,
        currency=app.config['PAYMENT_CURRENCY'].upper(),
        stripe_pk=app.config['STRIPE_PUBLISHABLE_KEY']
    )

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    company = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    role = db.Column(db.String(20), default='client')

    status = db.Column(db.String(20), default='pending')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    email_verified = db.Column(db.Boolean, default=False)

    subscription_status = db.Column(db.String(20), default='inactive')
    subscription_start = db.Column(db.DateTime)
    subscription_end = db.Column(db.DateTime)
    subscription_plan = db.Column(db.String(50), default='monthly')

    payment_status = db.Column(db.String(20), default='unpaid')
    paid_at = db.Column(db.DateTime)
    amount_paid = db.Column(db.Float)
    payment_currency = db.Column(db.String(10))
    stripe_session_id = db.Column(db.String(200))
    stripe_payment_intent = db.Column(db.String(200))
    invoice_number = db.Column(db.String(40))

    modules_enabled = db.Column(db.Text, default='["fire_smoke","weapon","accident"]')

    emergency_phone = db.Column(db.String(30))
    police_number = db.Column(db.String(30), default='911')
    fire_number = db.Column(db.String(30), default='911')
    ambulance_number = db.Column(db.String(30), default='911')

    admin_notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_subscription_active(self):
        if self.subscription_status != 'active':
            return False
        if self.subscription_end and datetime.utcnow() > self.subscription_end:
            self.subscription_status = 'expired'
            db.session.commit()
            return False
        return True

    def get_modules(self):
        try:
            return json.loads(self.modules_enabled)
        except:
            return []

    def days_until_expiry(self):
        if not self.subscription_end:
            return 0
        delta = self.subscription_end - datetime.utcnow()
        return max(0, delta.days)

    @property
    def subscription_badge(self):
        if self.subscription_status == 'active':
            d = self.days_until_expiry()
            if d <= 7:
                return ('warning', f'Expires in {d}d')
            return ('success', 'Active')
        elif self.subscription_status == 'expired':
            return ('danger', 'Expired')
        return ('secondary', 'Inactive')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id])

class DetectionAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    alert_type = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    camera_name = db.Column(db.String(100))
    screenshot_path = db.Column(db.String(300))
    emergency_called = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id])

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('client_dashboard'))
        return f(*args, **kwargs)
    return decorated

def send_approval_email(user):
    """Send approval email with credentials and download link."""
    try:
        msg = Message(
            subject='🛡️ AlertEye — Your Account Has Been Approved!',
            recipients=[user.email]
        )
        msg.html = render_template('emails/approval.html',
                                   user=user,
                                   download_url=app.config['APP_DOWNLOAD_URL'])
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_rejection_email(user):
    try:
        msg = Message(
            subject='AlertEye — Application Update',
            recipients=[user.email]
        )
        msg.html = render_template('emails/rejection.html', user=user)
        mail.send(msg)
    except Exception as e:
        print(f"Email error: {e}")

def send_subscription_expiry_warning(user):
    try:
        msg = Message(
            subject='⚠️ AlertEye — Subscription Expiring Soon',
            recipients=[user.email]
        )
        msg.html = render_template('emails/expiry_warning.html', user=user)
        mail.send(msg)
    except Exception as e:
        print(f"Email error: {e}")

def send_subscription_expired_email(user):
    try:
        msg = Message(
            subject='🔒 AlertEye — Subscription Expired',
            recipients=[user.email]
        )
        msg.html = render_template('emails/expired.html', user=user)
        mail.send(msg)
    except Exception as e:
        print(f"Email error: {e}")

def send_alert_email(user, alert_type, confidence, camera_name, screenshot_path=None):
    try:
        msg = Message(
            subject=f'🚨 AlertEye Alert — {alert_type.upper()} Detected',
            recipients=[user.email]
        )
        msg.html = render_template('emails/alert.html',
                                   user=user,
                                   alert_type=alert_type,
                                   confidence=confidence,
                                   camera_name=camera_name,
                                   timestamp=datetime.utcnow())
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, 'rb') as f:
                msg.attach('alert_screenshot.jpg', 'image/jpeg', f.read())
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Alert email error: {e}")
        return False

def send_otp_email(email, name, otp):
    """Email a one-time verification code to the applicant."""
    try:
        msg = Message(
            subject=f'🔐 AlertEye — Your verification code is {otp}',
            recipients=[email]
        )
        msg.html = render_template('emails/otp.html', name=name, otp=otp,
                                   ttl=OTP_TTL_MINUTES)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"OTP email error: {e}")
        return False

def generate_invoice_pdf(user):
    """Render a PDF invoice for a paid user and return the file path."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas

    path = os.path.join(INVOICE_DIR, f'{user.invoice_number}.pdf')
    plan = PLANS.get(user.subscription_plan, {})
    plan_label = plan.get('label', user.subscription_plan.title())
    currency = (user.payment_currency or app.config['PAYMENT_CURRENCY']).upper()
    amount = user.amount_paid or 0.0

    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    accent = colors.HexColor('#2563eb')
    dark = colors.HexColor('#1a1f36')

    c.setFillColor(dark)
    c.rect(0, h - 40 * mm, w, 40 * mm, fill=1, stroke=0)
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.png')
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 20 * mm, h - 33 * mm, width=22 * mm, height=22 * mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 22)
    c.drawString(46 * mm, h - 22 * mm, app.config['COMPANY_NAME'])
    c.setFont('Helvetica', 10)
    c.drawString(46 * mm, h - 28 * mm, 'Surveillance System Subscription')
    c.setFont('Helvetica-Bold', 24)
    c.drawRightString(w - 20 * mm, h - 20 * mm, 'INVOICE')
    c.setFont('Helvetica', 9)
    c.drawRightString(w - 20 * mm, h - 26 * mm, f'No. {user.invoice_number}')

    y = h - 56 * mm
    c.setFillColor(dark)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(20 * mm, y, 'BILLED TO')
    c.drawRightString(w - 20 * mm, y, 'INVOICE DETAILS')
    c.setFont('Helvetica', 10)
    c.setFillColor(colors.HexColor('#374151'))
    c.drawString(20 * mm, y - 6 * mm, user.name or '')
    if user.company:
        c.drawString(20 * mm, y - 11 * mm, user.company)
    c.drawString(20 * mm, y - 16 * mm, user.email or '')

    paid_at = (user.paid_at or datetime.utcnow()).strftime('%b %d, %Y')
    c.drawRightString(w - 20 * mm, y - 6 * mm, f'Date: {paid_at}')
    c.drawRightString(w - 20 * mm, y - 11 * mm, 'Status: PAID')

    ty = y - 32 * mm
    c.setFillColor(accent)
    c.rect(20 * mm, ty, w - 40 * mm, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(24 * mm, ty + 2.7 * mm, 'Description')
    c.drawRightString(w - 24 * mm, ty + 2.7 * mm, 'Amount')

    ly = ty - 12 * mm
    c.setFillColor(colors.HexColor('#374151'))
    c.setFont('Helvetica', 10)
    c.drawString(24 * mm, ly + 3 * mm, f'AlertEye Surveillance System — {plan_label}')
    c.drawRightString(w - 24 * mm, ly + 3 * mm, f'{currency} {amount:,.2f}')
    c.setStrokeColor(colors.HexColor('#e2e8f0'))
    c.line(20 * mm, ly, w - 20 * mm, ly)

    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(dark)
    c.drawRightString(w - 60 * mm, ly - 10 * mm, 'Total Paid')
    c.drawRightString(w - 24 * mm, ly - 10 * mm, f'{currency} {amount:,.2f}')

    c.setFont('Helvetica', 9)
    c.setFillColor(colors.HexColor('#9ca3af'))
    c.drawString(20 * mm, 22 * mm, app.config['COMPANY_ADDRESS'])
    c.drawString(20 * mm, 17 * mm, app.config['COMPANY_EMAIL'])
    c.drawCentredString(w / 2, 10 * mm,
                        'Thank you for choosing AlertEye. This is a computer-generated invoice.')
    if user.stripe_payment_intent:
        c.drawRightString(w - 20 * mm, 17 * mm, f'Ref: {user.stripe_payment_intent}')

    c.showPage()
    c.save()
    return path

def send_invoice_email(user, pdf_path):
    """Email the PDF invoice to the customer."""
    try:
        msg = Message(
            subject=f'🧾 AlertEye — Payment Receipt (Invoice {user.invoice_number})',
            recipients=[user.email]
        )
        msg.html = render_template('emails/invoice.html', user=user,
                                   plan=PLANS.get(user.subscription_plan, {}))
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                msg.attach(f'{user.invoice_number}.pdf', 'application/pdf', f.read())
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Invoice email error: {e}")
        return False

def notify_admins_new_application(user):
    """Email all admins that a (paid) applicant is awaiting approval."""
    try:
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            msg = Message('📋 New AlertEye Application (Paid)',
                          recipients=[admin.email])
            msg.html = render_template('emails/new_application.html',
                                       applicant=user, admin=admin)
            mail.send(msg)
    except Exception as e:
        print(f"Admin notify error: {e}")

def log_activity(user_id, action, details='', request_obj=None):
    ip = request_obj.remote_addr if request_obj else 'system'
    log = ActivityLog(user_id=user_id, action=action, details=details, ip_address=ip)
    db.session.add(log)
    db.session.commit()

APP_BUILD = 'downloads-v4'

@app.route('/__version__')
def _version():
    return jsonify({'build': APP_BUILD, 'stripe_configured': bool(stripe.api_key)})

@app.route('/')
def index():
    return render_template('public/home.html')

@app.route('/about')
def about():
    return render_template('public/about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not email or not message:
            flash('Please fill in your name, email and message.', 'danger')
            return redirect(url_for('contact'))
        try:
            msg = Message(
                subject=f'Website enquiry from {name}',
                recipients=[app.config['COMPANY_EMAIL']],
                body=f'Name: {name}\nEmail: {email}\n\n{message}',
                reply_to=email
            )
            mail.send(msg)
            flash('Thanks for reaching out. We will get back to you shortly.', 'success')
        except Exception:
            flash('We could not send your message right now. Please email us directly.', 'danger')
        return redirect(url_for('contact'))
    return render_template('public/contact.html')

def build_assistant_prompt():
    currency = app.config['PAYMENT_CURRENCY'].upper()
    plan_lines = []
    for key, p in PLANS.items():
        plan_lines.append(
            f"- {p['label']} ({key}): {currency} {p['price']:.2f} for {p['days']} days"
        )
    plans_text = "\n".join(plan_lines)
    return (
        "You are the official AlertEye website assistant. Only use the facts "
        "below. Never invent prices, plans, features, or policies. If a "
        "question is not covered here, say you are not sure and point the user "
        "to the contact page. Keep answers short, friendly and professional.\n\n"
        "WHAT ALERTEYE IS:\n"
        "AlertEye is an AI video-surveillance product. It watches the user's "
        "existing camera feeds in real time and detects three types of threats: "
        "(1) fire and smoke, (2) weapons, (3) road accidents. When a threat is "
        "confirmed (held for ~5 seconds), it instantly alerts the owner by phone "
        "call/ring, push notification and email, including the live location.\n\n"
        "PARTS OF THE PRODUCT:\n"
        "- A web portal (this site) to apply, pay, and manage the subscription.\n"
        "- A desktop application that connects to the cameras and runs the AI.\n"
        "- A companion Android app that receives the alerts and rings.\n\n"
        "PLANS AND PRICING (these are the only plans):\n"
        f"{plans_text}\n\n"
        "IMPORTANT PRICING POLICY:\n"
        "- A plan is a time-based subscription (monthly, quarterly or yearly).\n"
        "- ALL THREE detection modules (fire/smoke, weapon, accident) are "
        "INCLUDED in every plan. They are NOT sold separately and there is no "
        "per-module or per-camera price. The user picks a duration, not "
        "individual features.\n"
        "- The longer plans are cheaper per day; the yearly plan is the best "
        "value.\n\n"
        "HOW TO GET STARTED (buying flow):\n"
        "1. Click 'Get started' / 'Apply for access' and fill the form.\n"
        "2. Verify the email with the 6-digit code.\n"
        "3. Pay securely for the chosen plan.\n"
        "4. The team reviews/approves the application.\n"
        "5. Login credentials and the invoice are emailed to the user.\n"
        "6. Download the desktop app, sign in, and the modules unlock.\n\n"
        "OTHER FACTS:\n"
        "- Works with the user's existing cameras; no special hardware needed.\n"
        "- The emergency contact number is set by the customer in their own "
        "dashboard, and is called when a threat is confirmed.\n"
        "- When a subscription expires the modules lock until it is renewed.\n"
        "- For anything not listed here, direct the user to the Contact page."
    )

@app.route('/api/chat', methods=['POST'])
def api_chat():
    api_key = app.config['OPENROUTER_API_KEY']
    if not api_key:
        return jsonify({'reply': 'The assistant is not configured yet. Please use the contact page.'}), 200

    data = request.get_json(silent=True) or {}
    history = data.get('messages', [])
    if not isinstance(history, list):
        history = []

    trimmed = [m for m in history if isinstance(m, dict) and m.get('role') in ('user', 'assistant')][-10:]
    messages = [{'role': 'system', 'content': build_assistant_prompt()}] + trimmed

    models = [app.config['OPENROUTER_MODEL'], app.config['OPENROUTER_FALLBACK_MODEL']]
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': app.config['PUBLIC_BASE_URL'],
        'X-Title': 'AlertEye'
    }
    for model in models:
        if not model:
            continue
        try:
            resp = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={'model': model, 'messages': messages},
                timeout=30
            )
            if resp.status_code == 200:
                reply = resp.json()['choices'][0]['message']['content'].strip()
                if reply:
                    return jsonify({'reply': reply})
        except Exception:
            continue
    return jsonify({'reply': 'The assistant is busy right now. Please try again in a moment or use the contact page.'}), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.status == 'pending':
                flash('Your application is still under review. We\'ll email you once approved.', 'warning')
                return redirect(url_for('login'))
            if user.status == 'rejected':
                flash('Your application was not approved. Contact support for details.', 'danger')
                return redirect(url_for('login'))

            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.name
            log_activity(user.id, 'Login', f'Login from {request.remote_addr}', request)

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('client_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').lower().strip()
        company = request.form.get('company', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        plan = request.form.get('plan', 'monthly')

        if not name or not email or not password:
            flash('Name, email and password are required.', 'danger')
            return redirect(url_for('apply'))
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('apply'))
        if plan not in PLANS:
            plan = 'monthly'

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists. Please sign in.', 'danger')
            return redirect(url_for('login'))

        otp = f'{random.randint(0, 999999):06d}'
        session['reg'] = {
            'name': name,
            'email': email,
            'company': company,
            'phone': phone,
            'password_hash': generate_password_hash(password),
            'plan': plan,
            'otp': otp,
            'otp_expires': (datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
            'attempts': 0,
            'verified': False,
        }
        session.modified = True

        send_otp_email(email, name, otp)
        flash(f'We sent a 6-digit verification code to {email}.', 'success')
        return redirect(url_for('verify_otp'))

    return render_template('auth/apply.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    reg = session.get('reg')
    if not reg:
        flash('Please start your registration first.', 'warning')
        return redirect(url_for('apply'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        expires = datetime.fromisoformat(reg['otp_expires'])

        if datetime.utcnow() > expires:
            flash('That code has expired. We can send you a new one.', 'danger')
            return redirect(url_for('verify_otp'))

        reg['attempts'] = reg.get('attempts', 0) + 1
        if reg['attempts'] > 5:
            session.pop('reg', None)
            flash('Too many incorrect attempts. Please start again.', 'danger')
            return redirect(url_for('apply'))

        if entered == reg['otp']:
            reg['verified'] = True
            session['reg'] = reg
            session.modified = True
            return redirect(url_for('checkout'))

        session['reg'] = reg
        session.modified = True
        flash('Incorrect code. Please try again.', 'danger')

    return render_template('auth/verify_otp.html', email=reg['email'])

@app.route('/resend-otp')
def resend_otp():
    reg = session.get('reg')
    if not reg:
        return redirect(url_for('apply'))
    otp = f'{random.randint(0, 999999):06d}'
    reg['otp'] = otp
    reg['otp_expires'] = (datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()
    reg['attempts'] = 0
    session['reg'] = reg
    session.modified = True
    send_otp_email(reg['email'], reg['name'], otp)
    flash('A new verification code is on its way.', 'success')
    return redirect(url_for('verify_otp'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('forgot_password'))

        user = User.query.filter_by(email=email).first()
        if user:
            otp = f'{random.randint(0, 999999):06d}'
            session['pwreset'] = {
                'email': email,
                'otp': otp,
                'otp_expires': (datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
                'attempts': 0,
            }
            session.modified = True
            send_otp_email(email, user.name, otp)
            log_activity(user.id, 'Password reset requested', request_obj=request)

        flash('If an account exists for that email, a reset code is on its way.', 'success')
        return redirect(url_for('reset_password'))

    return render_template('auth/forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    pwreset = session.get('pwreset')
    if not pwreset:
        flash('Please request a password reset first.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        expires = datetime.fromisoformat(pwreset['otp_expires'])

        if datetime.utcnow() > expires:
            session.pop('pwreset', None)
            flash('That code has expired. Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))

        pwreset['attempts'] = pwreset.get('attempts', 0) + 1
        if pwreset['attempts'] > 5:
            session.pop('pwreset', None)
            flash('Too many incorrect attempts. Please start again.', 'danger')
            return redirect(url_for('forgot_password'))
        session['pwreset'] = pwreset
        session.modified = True

        if entered != pwreset['otp']:
            flash('Incorrect code. Please try again.', 'danger')
            return redirect(url_for('reset_password'))
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('reset_password'))
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('reset_password'))

        user = User.query.filter_by(email=pwreset['email']).first()
        if not user:
            session.pop('pwreset', None)
            flash('Account not found.', 'danger')
            return redirect(url_for('forgot_password'))

        user.set_password(password)
        db.session.commit()
        session.pop('pwreset', None)
        log_activity(user.id, 'Password reset completed', request_obj=request)
        flash('Your password has been reset. Please sign in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/reset_password.html', email=pwreset['email'])

@app.route('/resend-reset-otp')
def resend_reset_otp():
    pwreset = session.get('pwreset')
    if not pwreset:
        return redirect(url_for('forgot_password'))
    user = User.query.filter_by(email=pwreset['email']).first()
    if user:
        otp = f'{random.randint(0, 999999):06d}'
        pwreset['otp'] = otp
        pwreset['otp_expires'] = (datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()
        pwreset['attempts'] = 0
        session['pwreset'] = pwreset
        session.modified = True
        send_otp_email(pwreset['email'], user.name, otp)
    flash('A new reset code is on its way.', 'success')
    return redirect(url_for('reset_password'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    reg = session.get('reg')
    if not reg:
        flash('Please start your registration first.', 'warning')
        return redirect(url_for('apply'))
    if not reg.get('verified'):
        flash('Please verify your email first.', 'warning')
        return redirect(url_for('verify_otp'))

    plan = PLANS.get(reg['plan'], PLANS['monthly'])
    currency = app.config['PAYMENT_CURRENCY']

    if request.method == 'GET':
        return render_template('auth/checkout.html', reg=reg, plan=plan)

    if not stripe.api_key:
        flash('Payments are not configured. Please contact support.', 'danger')
        return redirect(url_for('checkout'))

    base = app.config['PUBLIC_BASE_URL']
    try:
        checkout_session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            customer_email=reg['email'],
            line_items=[{
                'quantity': 1,
                'price_data': {
                    'currency': currency,
                    'unit_amount': int(round(plan['price'] * 100)),
                    'product_data': {
                        'name': f"AlertEye Surveillance System — {plan['label']}",
                        'description': f"{plan['days']}-day subscription access",
                    },
                },
            }],
            metadata={'email': reg['email'], 'plan': reg['plan']},
            success_url=base + url_for('payment_success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base + url_for('payment_cancel'),
        )
    except Exception as e:
        print(f"Stripe error: {e}")
        flash('Could not start the payment. Please try again.', 'danger')
        return redirect(url_for('checkout'))

    session['stripe_session_id'] = checkout_session.id
    session.modified = True
    return redirect(checkout_session.url, code=303)

@app.route('/payment/cancel')
def payment_cancel():
    flash('Payment was cancelled. You can complete it whenever you are ready.', 'warning')
    return redirect(url_for('checkout'))

def _stripe_val(obj, key, default=None):
    """Safely read a key from a Stripe object (its .get() is not dict-like)."""
    try:
        v = obj[key]
    except Exception:
        return default
    return default if v is None else v

@app.route('/payment/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Missing payment reference.', 'danger')
        return redirect(url_for('apply'))

    existing = User.query.filter_by(stripe_session_id=session_id).first()
    if existing:
        session['paid_user_id'] = existing.id
        return render_template('auth/payment_success.html', user=existing)

    reg = session.get('reg')
    try:
        cs = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        print(f"Stripe retrieve error: {e}")
        flash('Could not verify the payment. Please contact support.', 'danger')
        return redirect(url_for('apply'))

    if cs.payment_status != 'paid':
        flash('Payment not completed yet.', 'warning')
        return redirect(url_for('checkout'))

    meta = _stripe_val(cs, 'metadata', {}) or {}
    email = (reg or {}).get('email') or _stripe_val(cs, 'customer_email') or _stripe_val(meta, 'email')
    if not email:
        flash('Could not match this payment to a registration.', 'danger')
        return redirect(url_for('apply'))

    plan_key = (reg or {}).get('plan') or _stripe_val(meta, 'plan', 'monthly')
    plan = PLANS.get(plan_key, PLANS['monthly'])

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=(reg or {}).get('name', email.split('@')[0]),
                    email=email,
                    company=(reg or {}).get('company', ''),
                    phone=(reg or {}).get('phone', ''),
                    status='pending')
        if reg and reg.get('password_hash'):
            user.password_hash = reg['password_hash']
        else:
            user.set_password(secrets.token_urlsafe(10))
        db.session.add(user)

    user.email_verified = True
    user.subscription_plan = plan_key
    user.payment_status = 'paid'
    user.paid_at = datetime.utcnow()
    user.amount_paid = (_stripe_val(cs, 'amount_total') or int(plan['price'] * 100)) / 100.0
    user.payment_currency = (_stripe_val(cs, 'currency') or app.config['PAYMENT_CURRENCY']).upper()
    user.stripe_session_id = session_id
    user.stripe_payment_intent = _stripe_val(cs, 'payment_intent')
    if not user.invoice_number:
        user.invoice_number = 'INV-' + datetime.utcnow().strftime('%Y%m%d') + '-' + str(uuid.uuid4())[:6].upper()
    db.session.commit()

    pdf_path = None
    try:
        pdf_path = generate_invoice_pdf(user)
    except Exception as e:
        print(f"Invoice PDF error: {e}")

    uid_bg = user.id
    def _post_payment_bg(pdf):
        with app.app_context():
            bg = User.query.get(uid_bg)
            if not bg:
                return
            if pdf:
                send_invoice_email(bg, pdf)
            notify_admins_new_application(bg)

    threading.Thread(target=_post_payment_bg, args=(pdf_path,), daemon=True).start()

    log_activity(user.id, 'Paid & registered',
                 f'Plan: {plan_key}, Amount: {user.amount_paid} {user.payment_currency}', request)

    session.pop('reg', None)
    session.pop('stripe_session_id', None)
    session['paid_user_id'] = user.id
    session.modified = True

    return render_template('auth/payment_success.html', user=user)

@app.route('/invoice/<int:user_id>')
def download_invoice(user_id):
    user = User.query.get_or_404(user_id)

    allowed = (session.get('paid_user_id') == user.id)
    if not allowed and 'user_id' in session:
        viewer = User.query.get(session['user_id'])
        allowed = viewer and (viewer.id == user.id or viewer.role == 'admin')
    if not allowed:
        flash('Please log in to access your invoice.', 'warning')
        return redirect(url_for('login'))

    if user.payment_status != 'paid' or not user.invoice_number:
        flash('No invoice is available for this account yet.', 'warning')
        return redirect(url_for('client_dashboard'))

    path = os.path.join(INVOICE_DIR, f'{user.invoice_number}.pdf')
    if not os.path.exists(path):
        path = generate_invoice_pdf(user)
    return send_file(path, as_attachment=True,
                     download_name=f'{user.invoice_number}.pdf',
                     mimetype='application/pdf')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], 'Logout')
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def client_dashboard():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

    recent_alerts = DetectionAlert.query.filter_by(user_id=user.id)\
        .order_by(DetectionAlert.timestamp.desc()).limit(10).all()

    return render_template('client/dashboard.html', user=user, alerts=recent_alerts)

@app.route('/dashboard/emergency', methods=['POST'])
@login_required
def update_emergency_contacts():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

    fields = ('emergency_phone', 'police_number', 'fire_number', 'ambulance_number')
    for field in fields:
        value = request.form.get(field, '').strip()
        if value:
            setattr(user, field, value)
    db.session.commit()
    log_activity(user.id, 'Updated emergency contacts', request_obj=request)
    flash('Emergency contacts updated.', 'success')
    return redirect(url_for('client_dashboard'))

def _find_dist_file(filename):
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, 'dist', filename),
        os.path.join(here, '..', 'dist', filename),
        os.path.join(os.path.dirname(here), 'dist', filename),
        os.path.join(os.path.expanduser('~'), 'dist', filename),
        os.path.join(app.static_folder, 'downloads', filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

@app.route('/download/app')
@login_required
def download_app():
    user = User.query.get(session['user_id'])
    if not user.is_subscription_active() and user.role != 'admin':
        flash('Active subscription required to download the app.', 'danger')
        return redirect(url_for('client_dashboard'))

    app_path = _find_dist_file('AlertEye.exe') or _find_dist_file('AlertEye.zip')
    if app_path:
        return send_file(app_path, as_attachment=True)
    if app.config['DESKTOP_DOWNLOAD_URL']:
        return redirect(app.config['DESKTOP_DOWNLOAD_URL'])
    flash('Desktop app bundle not yet available. Contact admin.', 'warning')
    return redirect(url_for('client_dashboard'))

@app.route('/download/android')
@login_required
def download_android():
    user = User.query.get(session['user_id'])
    if not user.is_subscription_active() and user.role != 'admin':
        flash('Active subscription required to download the app.', 'danger')
        return redirect(url_for('client_dashboard'))

    apk_path = _find_dist_file('AlertEye.apk')
    if apk_path:
        return send_file(apk_path, as_attachment=True, download_name='AlertEye.apk')
    if app.config['ANDROID_DOWNLOAD_URL']:
        return redirect(app.config['ANDROID_DOWNLOAD_URL'])
    flash('Android app (APK) not yet available. Contact admin.', 'warning')
    return redirect(url_for('client_dashboard'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_users = User.query.filter_by(role='client').count()
    pending = User.query.filter_by(status='pending').count()
    active_subs = User.query.filter_by(subscription_status='active').count()
    recent_alerts = DetectionAlert.query.order_by(DetectionAlert.timestamp.desc()).limit(20).all()
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(15).all()

    expiring = User.query.filter(
        User.subscription_status == 'active',
        User.subscription_end <= datetime.utcnow() + timedelta(days=7),
        User.subscription_end >= datetime.utcnow()
    ).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users, pending=pending,
                           active_subs=active_subs, recent_alerts=recent_alerts,
                           recent_logs=recent_logs, expiring=expiring)

@app.route('/admin/applications')
@admin_required
def admin_applications():
    status = request.args.get('status', 'pending')
    users = User.query.filter_by(role='client', status=status)\
        .order_by(User.applied_at.desc()).all()
    return render_template('admin/applications.html', users=users, current_status=status)

@app.route('/admin/approve/<int:user_id>', methods=['POST'])
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    plan = request.form.get('plan', 'monthly')
    modules = request.form.getlist('modules')
    if not modules:
        modules = ['fire_smoke', 'weapon', 'accident']

    user.status = 'approved'
    user.approved_at = datetime.utcnow()
    user.approved_by = session['user_id']
    user.subscription_plan = plan
    user.modules_enabled = json.dumps(modules)

    if not user.password_hash:

        user.set_password(secrets.token_urlsafe(10))

    now = datetime.utcnow()
    user.subscription_start = now
    if plan == 'monthly':
        user.subscription_end = now + timedelta(days=30)
    elif plan == 'quarterly':
        user.subscription_end = now + timedelta(days=90)
    elif plan == 'yearly':
        user.subscription_end = now + timedelta(days=365)
    user.subscription_status = 'active'

    db.session.commit()

    send_approval_email(user)
    log_activity(session['user_id'], f'Approved user {user.email}',
                 f'Plan: {plan}, Modules: {modules}', request)

    flash(f'✅ {user.name} approved! Credentials sent to {user.email}.', 'success')
    return redirect(url_for('admin_applications'))

@app.route('/admin/reject/<int:user_id>', methods=['POST'])
@admin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', 'Application did not meet requirements.')
    user.status = 'rejected'
    user.rejection_reason = reason
    db.session.commit()
    send_rejection_email(user)
    log_activity(session['user_id'], f'Rejected user {user.email}', reason, request)
    flash(f'❌ {user.name}\'s application rejected.', 'info')
    return redirect(url_for('admin_applications'))

@app.route('/admin/users')
@admin_required
def admin_users():
    search = request.args.get('q', '')
    query = User.query.filter_by(role='client', status='approved')
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )
    users = query.order_by(User.approved_at.desc()).all()
    return render_template('admin/users.html', users=users, search=search)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'renew_subscription':
            plan = request.form.get('plan', 'monthly')
            now = datetime.utcnow()

            base = user.subscription_end if user.is_subscription_active() else now
            if plan == 'monthly':
                user.subscription_end = base + timedelta(days=30)
            elif plan == 'quarterly':
                user.subscription_end = base + timedelta(days=90)
            elif plan == 'yearly':
                user.subscription_end = base + timedelta(days=365)
            user.subscription_status = 'active'
            user.subscription_start = now
            user.subscription_plan = plan
            db.session.commit()
            log_activity(session['user_id'], f'Renewed subscription for {user.email}',
                         f'Plan: {plan}', request)
            flash('✅ Subscription renewed.', 'success')

        elif action == 'suspend':
            user.subscription_status = 'inactive'
            db.session.commit()
            flash('🔒 Subscription suspended.', 'warning')

        elif action == 'update_modules':
            modules = request.form.getlist('modules')
            user.modules_enabled = json.dumps(modules)
            db.session.commit()
            flash('✅ Modules updated.', 'success')

        elif action == 'update_notes':
            user.admin_notes = request.form.get('admin_notes')
            db.session.commit()
            flash('✅ Notes saved.', 'success')

        return redirect(url_for('admin_user_detail', user_id=user_id))

    alerts = DetectionAlert.query.filter_by(user_id=user_id)\
        .order_by(DetectionAlert.timestamp.desc()).limit(30).all()
    activity = ActivityLog.query.filter_by(user_id=user_id)\
        .order_by(ActivityLog.timestamp.desc()).limit(20).all()

    return render_template('admin/user_detail.html',
                           user=user, alerts=alerts, activity=activity,
                           all_modules=['fire_smoke', 'weapon', 'accident'])

@app.route('/admin/alerts')
@admin_required
def admin_alerts():
    alerts = DetectionAlert.query.order_by(DetectionAlert.timestamp.desc()).limit(100).all()
    return render_template('admin/alerts.html', alerts=alerts)

@app.route('/api/auth', methods=['POST'])
def api_auth():
    """Desktop app calls this to verify credentials + subscription."""
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    if user.status != 'approved':
        return jsonify({'success': False, 'error': 'Account not approved'}), 403

    active = user.is_subscription_active()
    modules = user.get_modules() if active else []

    log_activity(user.id, 'Desktop App Login', request.remote_addr)

    return jsonify({
        'success': True,
        'user': {
            'uid': user.uid,
            'name': user.name,
            'email': user.email,
            'phone': user.phone or '',
            'subscription_active': active,
            'subscription_end': user.subscription_end.isoformat() if user.subscription_end else None,
            'days_remaining': user.days_until_expiry(),
            'modules': modules,
            'emergency_phone': user.emergency_phone,
            'police_number': user.police_number or '911',
            'fire_number': user.fire_number or '911',
            'ambulance_number': user.ambulance_number or '911',
        }
    })

@app.route('/api/alert', methods=['POST'])
def api_alert():
    """Desktop app posts detection alerts here."""
    data = request.get_json()
    uid = data.get('uid')
    api_secret = data.get('api_secret', '')
    expected = os.environ.get('DESKTOP_API_SECRET', '')
    if expected and api_secret != expected:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    user = User.query.filter_by(uid=uid).first()
    if not user:
        return jsonify({'success': False, 'error': 'Unknown user'}), 404

    alert = DetectionAlert(
        user_id=user.id,
        alert_type=data.get('alert_type'),
        confidence=data.get('confidence', 0.0),
        camera_name=data.get('camera_name', 'CAM-01'),
        screenshot_path=data.get('screenshot_path', '')
    )
    db.session.add(alert)
    db.session.commit()

    alert_id = alert.id
    user_id_bg = user.id
    alert_type_bg = data.get('alert_type')
    confidence_bg = data.get('confidence', 0.0)
    camera_bg = data.get('camera_name', 'CAM-01')
    screenshot_bg = data.get('screenshot_path')

    def send_in_bg():
        with app.app_context():
            bg_user = User.query.get(user_id_bg)
            if bg_user:
                sent = send_alert_email(
                    bg_user, alert_type_bg, confidence_bg,
                    camera_bg, screenshot_bg
                )
                bg_alert = DetectionAlert.query.get(alert_id)
                if bg_alert:
                    bg_alert.email_sent = sent
                    db.session.commit()

    threading.Thread(target=send_in_bg, daemon=True).start()

    return jsonify({'success': True, 'alert_id': alert.id})

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """Desktop app pings every 30min to check subscription status."""
    data = request.get_json()
    uid = data.get('uid')
    user = User.query.filter_by(uid=uid).first()
    if not user:
        return jsonify({'active': False})

    active = user.is_subscription_active()
    modules = user.get_modules() if active else []

    return jsonify({
        'active': active,
        'modules': modules,
        'days_remaining': user.days_until_expiry()
    })

def run_scheduled_tasks():
    """Check subscriptions daily — send reminder emails."""
    import time
    while True:
        with app.app_context():
            try:

                expired = User.query.filter(
                    User.subscription_status == 'active',
                    User.subscription_end < datetime.utcnow()
                ).all()
                for user in expired:
                    user.subscription_status = 'expired'
                    db.session.commit()
                    send_subscription_expired_email(user)

                expiring_soon = User.query.filter(
                    User.subscription_status == 'active',
                    User.subscription_end <= datetime.utcnow() + timedelta(days=7),
                    User.subscription_end >= datetime.utcnow()
                ).all()
                for user in expiring_soon:
                    send_subscription_expiry_warning(user)

            except Exception as e:
                print(f"Scheduler error: {e}")
        time.sleep(86400)

def migrate_schema():
    """Add any User columns missing from an existing MySQL DB (lightweight migration)."""
    from sqlalchemy import inspect, text
    with app.app_context():
        inspector = inspect(db.engine)
        if 'user' not in inspector.get_table_names():
            return
        existing = {c['name'] for c in inspector.get_columns('user')}
        additions = {
            'email_verified': 'BOOLEAN DEFAULT 0',
            'payment_status': "VARCHAR(20) DEFAULT 'unpaid'",
            'paid_at': 'DATETIME',
            'amount_paid': 'FLOAT',
            'payment_currency': 'VARCHAR(10)',
            'stripe_session_id': 'VARCHAR(200)',
            'stripe_payment_intent': 'VARCHAR(200)',
            'invoice_number': 'VARCHAR(40)',
        }
        with db.engine.begin() as conn:
            for col, ddl in additions.items():
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE `user` ADD COLUMN {col} {ddl}'))
                    print(f"[migrate] Added column user.{col}")

def create_admin():
    """Create default admin if none exists."""
    with app.app_context():
        db.create_all()
        migrate_schema()
        if not User.query.filter_by(role='admin').first():
            admin = User(
                name='Admin',
                email='admin@alerteye.com',
                role='admin',
                status='approved',
                subscription_status='active',
                subscription_end=datetime.utcnow() + timedelta(days=3650)
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin@alerteye.com / Admin@123")

if __name__ == '__main__':
    create_admin()

    scheduler = threading.Thread(target=run_scheduled_tasks, daemon=True)
    scheduler.start()
    app.run(debug=True, port=5000, host='0.0.0.0')
