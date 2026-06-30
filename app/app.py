from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import string
import hashlib

# Add src to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import *
from src.data_loader import DataLoader
from src.recommender import FashionRecommender
from app.models import db, User, OTPRecord, CartItem, Order, OrderItem, SearchHistory, OrderTracking, RecommendationFeedback, SECURITY_QUESTIONS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize data loader and recommender
data_loader = DataLoader()
recommender = FashionRecommender()

# Load data and model
with app.app_context():
    db.create_all()
    try:
        data_loader.load_raw_data()
        recommender.load_model()
        # Share the articles DataFrame with recommender for gender detection
        if data_loader.articles_df is not None:
            recommender.set_articles_df(data_loader.articles_df)
    except Exception as e:
        print(f"Warning: {e}")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== OTP HELPERS ====================

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    """
    Send OTP via email using SMTP.
    ---------------------------------------------------------------------------
    SETUP REQUIRED: Replace the SMTP credentials below with your own.
    For Gmail: enable 2FA → create an App Password → use it as SMTP_PASSWORD.
    ---------------------------------------------------------------------------
    In development / demo mode this just prints the OTP to the console.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # ── SMTP Configuration (update these) ────────────────────────────────
    SMTP_HOST     = 'smtp.gmail.com'
    SMTP_PORT     = 587
    SMTP_USER     = 'your_email@gmail.com'   # ← replace
    SMTP_PASSWORD = 'your_app_password'      # ← replace (Gmail App Password)
    # ─────────────────────────────────────────────────────────────────────

    msg = MIMEMultipart()
    msg['From']    = SMTP_USER
    msg['To']      = email
    msg['Subject'] = 'H&M Fashion – Password Reset OTP'

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; border-radius: 10px; color: white;">
            <h2>H&M Fashion</h2>
            <p>Your password reset OTP</p>
        </div>
        <div style="padding: 30px; border: 1px solid #eee; border-radius: 0 0 10px 10px;">
            <p style="color: #333;">Hi, you requested to reset your password.</p>
            <p style="text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #667eea; margin: 20px 0;">
                {otp}
            </p>
            <p style="color: #666; font-size: 13px;">This OTP is valid for <strong>10 minutes</strong>. Do not share it with anyone.</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        # In dev/demo mode, just print the OTP
        print(f"[DEV] OTP for {email}: {otp} (SMTP error: {e})")
        return True  # Return True so the flow continues in dev mode


def send_otp_sms(phone, otp):
    """
    Send OTP via SMS using Twilio.
    ---------------------------------------------------------------------------
    SETUP REQUIRED: Sign up at twilio.com, get Account SID + Auth Token +
    a Twilio phone number, then fill in below.
    ---------------------------------------------------------------------------
    In development / demo mode this just prints the OTP to the console.
    """
    # ── Twilio Configuration (update these) ──────────────────────────────
    TWILIO_SID     = 'AC128a06b1c05484b706c532a6d9cf51d8'    # ← replace
    TWILIO_TOKEN   = 'ab66df9291bf265e7df42e37bf3ecc6e'        # ← replace
    TWILIO_PHONE   = '+15755705569'            # ← replace with your Twilio number
    # ─────────────────────────────────────────────────────────────────────

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            body=f'Your H&M Fashion password reset OTP is: {otp}. Valid for 10 minutes.',
            from_=TWILIO_PHONE,
            to=phone
        )
        return True
    except Exception as e:
        # Dev mode fallback
        print(f"[DEV] OTP for {phone}: {otp} (Twilio error: {e})")
        return True


def store_otp(user_id, otp, method):
    """Hash and store OTP; invalidate any previous OTP for this user."""
    # Invalidate old OTPs
    OTPRecord.query.filter_by(user_id=user_id, is_used=False).delete()

    otp_hash = generate_password_hash(otp)
    record = OTPRecord(
        user_id=user_id,
        otp_hash=otp_hash,
        delivery_method=method,
        is_used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(record)
    db.session.commit()
    return record


def verify_otp(user_id, otp):
    """Check OTP against stored hash. Returns True if valid & not expired."""
    record = OTPRecord.query.filter_by(
        user_id=user_id, is_used=False
    ).order_by(OTPRecord.created_at.desc()).first()

    if not record:
        return False

    if datetime.utcnow() > record.expires_at:
        record.is_used = True
        db.session.commit()
        return False

    if check_password_hash(record.otp_hash, otp):
        record.is_used = True
        db.session.commit()
        return True

    return False

# ==================== SERVE IMAGES ====================

@app.route('/data/raw/images/<path:filename>')
def serve_image(filename):
    images_dir = Path(__file__).resolve().parent.parent / 'data' / 'raw' / 'images'
    return send_from_directory(images_dir, filename)

# ==================== HOME & BROWSE ====================

@app.route('/')
def index():
    """Homepage – browse without login"""
    # If user is logged in, use their gender for personalized popular items
    gender = None
    if current_user.is_authenticated and current_user.gender in ('Men', 'Women'):
        gender = current_user.gender

    popular_articles = data_loader.get_popular_articles(20, gender=gender)
    for article in popular_articles:
        article['image_url'] = data_loader.get_article_image_url(article['article_id'])

    return render_template('index.html', articles=popular_articles, active_gender=gender)


@app.route('/search')
def search():
    """Search products – gender-aware, no login required"""
    query = request.args.get('q', '').strip()

    if not query:
        flash('Please enter a search term', 'warning')
        return redirect(url_for('index'))

    # Pass logged-in user's gender (if set) for filtering
    user_gender = None
    if current_user.is_authenticated and current_user.gender in ('Men', 'Women'):
        user_gender = current_user.gender

    articles, detected_gender = data_loader.search_articles(query, n=50, gender=user_gender)

    for article in articles:
        article['image_url'] = data_loader.get_article_image_url(article['article_id'])

    # Save search history if logged in
    if current_user.is_authenticated:
        search_record = SearchHistory(
            user_id=current_user.id,
            search_query=query,
            gender_filter=detected_gender
        )
        db.session.add(search_record)
        db.session.commit()

    return render_template('search_results.html',
                           articles=articles,
                           query=query,
                           detected_gender=detected_gender)


@app.route('/product/<int:article_id>')
def product_detail(article_id):
    """Product detail – gender-aware recommendations"""
    article = data_loader.get_article_by_id(article_id)
    if not article:
        flash('Product not found', 'danger')
        return redirect(url_for('index'))

    article['image_url'] = data_loader.get_article_image_url(article_id)

    # Get hybrid recommendations (gender is auto-detected inside recommender)
    recommended_ids = recommender.get_hybrid_recommendations(article_id, 6)
    recommendations = []
    for rec_id in recommended_ids:
        rec_article = data_loader.get_article_by_id(rec_id)
        if rec_article:
            rec_article['image_url'] = data_loader.get_article_image_url(rec_id)
            recommendations.append(rec_article)

    # Also get complementary items separately for a "Complete the Look" section
    complementary = data_loader.get_complementary_articles(article_id, n=4)
    for comp in complementary:
        comp['image_url'] = data_loader.get_article_image_url(comp['article_id'])
    # Remove any that are already in recommendations
    rec_ids_set = {r['article_id'] for r in recommendations}
    complementary = [c for c in complementary if c['article_id'] not in rec_ids_set]

    # NEW: Get complete outfit recommendations
    outfits = data_loader.get_complete_outfits(article_id, n=3)
    # Add image URLs to all outfit items
    for outfit in outfits:
        for item in outfit['items']:
            item['image_url'] = data_loader.get_article_image_url(item['article_id'])

    return render_template('product_detail.html',
                           article=article,
                           recommendations=recommendations,
                           complementary=complementary,
                           outfits=outfits)

# ==================== AUTHENTICATION ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username       = request.form.get('username', '').strip()
        email          = request.form.get('email', '').strip()
        password       = request.form.get('password', '')
        gender         = request.form.get('gender', 'Unspecified')
        age            = request.form.get('age', '25')
        country_code   = request.form.get('country_code', '')
        mobile_number  = request.form.get('mobile_number', '').strip()
        sq1            = request.form.get('security_question_1', '')
        sa1            = request.form.get('security_answer_1', '').strip()
        sq2            = request.form.get('security_question_2', '')
        sa2            = request.form.get('security_answer_2', '').strip()

        # ── Validation ────────────────────────────────────────────────────
        if not all([username, email, password]):
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('register'))

        if not sq1 or not sa1 or not sq2 or not sa2:
            flash('Security questions and answers are mandatory', 'danger')
            return redirect(url_for('register'))

        if sq1 == sq2:
            flash('Please choose two different security questions', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('register'))

        # Mobile validation (if provided)
        if mobile_number and not mobile_number.isdigit():
            flash('Mobile number must contain only digits', 'danger')
            return redirect(url_for('register'))

        # Age validation
        try:
            age = int(age)
            if age < 13 or age > 120:
                flash('Age must be between 13 and 120', 'danger')
                return redirect(url_for('register'))
        except (ValueError, TypeError):
            age = 25

        # Uniqueness checks
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        # ── Create user ───────────────────────────────────────────────────
        user = User(
            username=username,
            email=email,
            gender=gender,
            age=age,
            country_code=country_code if country_code else None,
            mobile_number=mobile_number if mobile_number else None,
            security_question_1=sq1,
            security_question_2=sq2
        )
        user.set_password(password)
        user.set_security_answers(sa1, sa2)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', security_questions=SECURITY_QUESTIONS)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# ==================== FORGOT PASSWORD FLOW ====================
# Step 1 → /forgot_password        : Enter username → show security questions
# Step 2 → /forgot_password/verify : Answer security questions → choose OTP method
# Step 3 → /forgot_password/otp    : Enter OTP → reset password
# ================================================================

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Step 1: Enter username to look up account"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Username not found', 'danger')
            return redirect(url_for('forgot_password'))

        # Store user_id in session for the multi-step flow
        session['fp_user_id'] = user.id
        # Move to security question step
        return redirect(url_for('forgot_password_verify'))

    # Clear any stale session data on fresh visit
    session.pop('fp_user_id', None)
    session.pop('fp_sq_verified', None)
    return render_template('forgot_password.html', step='username')


@app.route('/forgot_password/verify', methods=['GET', 'POST'])
def forgot_password_verify():
    """Step 2: Answer security questions OR skip to OTP, then choose OTP delivery method"""
    user_id = session.get('fp_user_id')
    if not user_id:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('forgot_password'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please start again.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        # Check if user wants to skip security questions
        skip_sq = request.form.get('skip_security_questions')
        
        if skip_sq == 'yes':
            # Skip directly to OTP
            session['fp_sq_verified'] = True
            session['fp_sq_skipped'] = True
            flash('Security questions skipped. Please verify via OTP.', 'info')
            return redirect(url_for('forgot_password_verify'))
        
        # If security questions haven't been verified yet
        if not session.get('fp_sq_verified'):
            answer1 = request.form.get('security_answer_1', '').strip()
            answer2 = request.form.get('security_answer_2', '').strip()

            if not user.check_security_answer_1(answer1) or not user.check_security_answer_2(answer2):
                flash('One or both security answers are incorrect. Please try again.', 'danger')
                return redirect(url_for('forgot_password_verify'))

            # Mark security questions as verified
            session['fp_sq_verified'] = True
            session['fp_sq_skipped'] = False
            # Re-render the page to show OTP method selection
            return redirect(url_for('forgot_password_verify'))

        # Security questions verified/skipped → send OTP
        else:
            method = request.form.get('otp_method', '')

            if method == 'email':
                otp = generate_otp()
                store_otp(user.id, otp, 'email')
                send_otp_email(user.email, otp)
                session['fp_otp_sent'] = True
                flash(f'OTP sent to {user.get_masked_email()}', 'success')
                return redirect(url_for('forgot_password_otp'))

            elif method == 'mobile':
                if not user.mobile_number:
                    flash('No mobile number registered on this account.', 'danger')
                    return redirect(url_for('forgot_password_verify'))
                otp = generate_otp()
                store_otp(user.id, otp, 'mobile')
                full_phone = f"{user.country_code or ''}{user.mobile_number}"
                send_otp_sms(full_phone, otp)
                session['fp_otp_sent'] = True
                flash(f'OTP sent to {user.get_masked_mobile()}', 'success')
                return redirect(url_for('forgot_password_otp'))
            else:
                flash('Please select a delivery method', 'warning')

    # GET – show appropriate step
    sq_verified = session.get('fp_sq_verified', False)
    return render_template('forgot_password.html',
                           step='security_questions' if not sq_verified else 'otp_method',
                           user=user,
                           sq_verified=sq_verified)


@app.route('/forgot_password/otp', methods=['GET', 'POST'])
def forgot_password_otp():
    """Step 3: Verify OTP and reset password"""
    user_id = session.get('fp_user_id')
    if not user_id or not session.get('fp_sq_verified'):
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('forgot_password'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'verify_otp':
            otp = request.form.get('otp', '').strip()
            if verify_otp(user.id, otp):
                session['fp_otp_verified'] = True
                return redirect(url_for('forgot_password_otp'))
            else:
                flash('Invalid or expired OTP. Please try again.', 'danger')
                return redirect(url_for('forgot_password_otp'))

        elif action == 'reset_password':
            if not session.get('fp_otp_verified'):
                flash('Please verify OTP first.', 'warning')
                return redirect(url_for('forgot_password_otp'))

            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not new_password or len(new_password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return redirect(url_for('forgot_password_otp'))

            if new_password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('forgot_password_otp'))

            # Reset password
            user.set_password(new_password)
            db.session.commit()

            # Clear all session data for this flow
            session.pop('fp_user_id', None)
            session.pop('fp_sq_verified', None)
            session.pop('fp_otp_sent', None)
            session.pop('fp_otp_verified', None)

            flash('Password reset successfully! You can now login.', 'success')
            return redirect(url_for('login'))

    # GET
    otp_verified = session.get('fp_otp_verified', False)
    return render_template('forgot_password.html',
                           step='otp_enter' if not otp_verified else 'new_password',
                           user=user,
                           otp_verified=otp_verified)


# Resend OTP helper
@app.route('/forgot_password/resend_otp', methods=['POST'])
def resend_otp():
    user_id = session.get('fp_user_id')
    if not user_id:
        flash('Session expired.', 'warning')
        return redirect(url_for('forgot_password'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('forgot_password'))

    # Check last OTP record to determine method
    last_otp = OTPRecord.query.filter_by(user_id=user.id).order_by(OTPRecord.created_at.desc()).first()
    method = last_otp.delivery_method if last_otp else 'email'

    otp = generate_otp()
    store_otp(user.id, otp, method)

    if method == 'email':
        send_otp_email(user.email, otp)
        flash(f'OTP resent to {user.get_masked_email()}', 'success')
    else:
        full_phone = f"{user.country_code or ''}{user.mobile_number}"
        send_otp_sms(full_phone, otp)
        flash(f'OTP resent to {user.get_masked_mobile()}', 'success')

    return redirect(url_for('forgot_password_otp'))


# ==================== SHOPPING CART ====================

# ==================== CART API ====================

@app.route('/api/cart/count')
@login_required
def cart_count_api():
    """API endpoint to get current cart item count"""
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total_count = sum(item.quantity for item in cart_items)
        return jsonify({'count': total_count, 'success': True})
    except Exception as e:
        return jsonify({'count': 0, 'success': False, 'error': str(e)})


# ==================== CART ====================

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    items_with_details = []
    subtotal = 0

    for item in cart_items:
        article = data_loader.get_article_by_id(item.article_id)
        if article:
            article['image_url'] = data_loader.get_article_image_url(item.article_id)
            article['cart_id'] = item.id
            article['quantity'] = item.quantity
            items_with_details.append(article)
            subtotal += article.get('price', 0) * item.quantity

    shipping = 0 if subtotal > 999 else 50
    tax = subtotal * 0.18
    total = subtotal + shipping + tax

    return render_template('cart.html',
                           items=items_with_details,
                           subtotal=subtotal, shipping=shipping, tax=tax, total=total)


@app.route('/add_to_cart/<int:article_id>', methods=['POST'])
@login_required
def add_to_cart(article_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, article_id=article_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, article_id=article_id)
        db.session.add(cart_item)
    db.session.commit()
    
    # Get updated cart count
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_count = sum(item.quantity for item in cart_items)
    
    # Support both JSON (AJAX) and HTML responses
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            'success': True,
            'message': 'Item added to cart!',
            'cart_count': total_count
        })
    else:
        flash('Item added to cart!', 'success')
        return redirect(request.referrer or url_for('index'))


@app.route('/buy_now/<int:article_id>', methods=['POST'])
@login_required
def buy_now(article_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, article_id=article_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, article_id=article_id)
        db.session.add(cart_item)
    db.session.commit()
    return redirect(url_for('checkout'))


@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    cart_item = CartItem.query.get_or_404(cart_id)
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('cart'))
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart', 'info')
    return redirect(url_for('cart'))


@app.route('/update_cart/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    cart_item = CartItem.query.get_or_404(cart_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data = request.get_json()
    quantity = data.get('quantity', 1)
    if quantity < 1:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    db.session.commit()
    return jsonify({'success': True})


# ==================== CHECKOUT & PAYMENT ====================

@app.route('/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))

    subtotal = 0
    items = []
    for item in cart_items:
        article = data_loader.get_article_by_id(item.article_id)
        if article:
            article['quantity'] = item.quantity
            article['image_url'] = data_loader.get_article_image_url(item.article_id)
            items.append(article)
            subtotal += article.get('price', 0) * item.quantity

    shipping = 0 if subtotal > 999 else 50
    tax = subtotal * 0.18
    total = subtotal + shipping + tax
    
    # Get saved addresses (if you have a model for this)
    # For now, we'll pass an empty list
    saved_addresses = []

    return render_template('checkout.html',
                           cart_items=items, subtotal=subtotal,
                           shipping=shipping, tax=tax, total=total,
                           saved_addresses=saved_addresses)

@app.route("/place-order", methods=["POST"])
def place_order():
    # handle shipping + payment logic
    return redirect(url_for("process_payment"))

@app.route('/process_payment', methods=['GET','POST'])
@login_required
def process_payment():
    payment_method = request.form.get('payment_method')
    full_name      = request.form.get('full_name')
    email          = request.form.get('email')
    phone          = request.form.get('phone')
    address_line1  = request.form.get('address_line1')
    address_line2  = request.form.get('address_line2', '')
    city           = request.form.get('city')
    state          = request.form.get('state')
    pincode        = request.form.get('pincode')

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))

    subtotal = 0
    order_items_data = []
    for item in cart_items:
        article = data_loader.get_article_by_id(item.article_id)
        if article:
            price = article.get('price', 0)
            subtotal += price * item.quantity
            order_items_data.append({
                'article_id': item.article_id,
                'quantity': item.quantity,
                'price': price
            })

    shipping = 0 if subtotal > 999 else 50
    tax = subtotal * 0.18
    total = subtotal + shipping + tax

    tracking_number = 'TRK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    shipping_address = address_line1
    if address_line2:
        shipping_address += f", {address_line2}"
    
    # Realistic delivery: Same day to 3 days max
    delivery_hours = random.randint(6, 72)  # 6 hours to 72 hours (3 days)
    estimated_delivery = datetime.utcnow() + timedelta(hours=delivery_hours)

    order = Order(
        user_id=current_user.id,
        total_amount=total,
        status='pending',  # Start with pending instead of placed
        payment_method=payment_method,
        payment_status='completed' if payment_method != 'cod' else 'pending',
        tracking_number=tracking_number,
        estimated_delivery=estimated_delivery,
        shipping_name=full_name, shipping_email=email, shipping_phone=phone,
        shipping_address=shipping_address, shipping_city=city,
        shipping_state=state, shipping_pincode=pincode
    )
    db.session.add(order)
    db.session.flush()

    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            article_id=item_data['article_id'],
            quantity=item_data['quantity'],
            price=item_data['price']
        )
        db.session.add(order_item)

    # Create initial tracking entry - Order Confirmed
    tracking1 = OrderTracking(
        order_id=order.id,
        status='confirmed',
        message='Order confirmed and payment received',
        location='Mumbai Processing Center',
        created_at=datetime.utcnow()
    )
    db.session.add(tracking1)
    
    # Simulate realistic tracking progression
    if delivery_hours <= 24:  # Same day delivery
        # Packed (2 hours later)
        tracking2 = OrderTracking(
            order_id=order.id,
            status='packed',
            message='Your order has been packed',
            location='Mumbai Warehouse',
            created_at=datetime.utcnow() + timedelta(hours=2)
        )
        db.session.add(tracking2)
        
        # Out for delivery (4 hours later)
        tracking3 = OrderTracking(
            order_id=order.id,
            status='shipping',
            message='Out for delivery',
            location='Local Delivery Hub',
            created_at=datetime.utcnow() + timedelta(hours=4)
        )
        db.session.add(tracking3)
        
    elif delivery_hours <= 48:  # Next day delivery
        # Packed (6 hours later)
        tracking2 = OrderTracking(
            order_id=order.id,
            status='packed',
            message='Your order has been packed',
            location='Mumbai Warehouse',
            created_at=datetime.utcnow() + timedelta(hours=6)
        )
        db.session.add(tracking2)
        
        # Out for delivery (24 hours later)
        tracking3 = OrderTracking(
            order_id=order.id,
            status='shipping',
            message='Out for delivery',
            location='Local Delivery Hub',
            created_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(tracking3)
        
    else:  # 2-3 days delivery
        # Packed (12 hours later)
        tracking2 = OrderTracking(
            order_id=order.id,
            status='packed',
            message='Your order has been packed',
            location='Mumbai Warehouse',
            created_at=datetime.utcnow() + timedelta(hours=12)
        )
        db.session.add(tracking2)
        
        # In transit (36 hours later)
        tracking3 = OrderTracking(
            order_id=order.id,
            status='shipping',
            message='Package in transit',
            location='Regional Hub',
            created_at=datetime.utcnow() + timedelta(hours=36)
        )
        db.session.add(tracking3)
        
        # Out for delivery (60 hours later)
        tracking4 = OrderTracking(
            order_id=order.id,
            status='shipping',
            message='Out for delivery',
            location='Local Delivery Hub',
            created_at=datetime.utcnow() + timedelta(hours=60)
        )
        db.session.add(tracking4)

    # Clear cart
    for item in cart_items:
        db.session.delete(item)

    db.session.commit()

    flash(f'Order placed successfully! Tracking: {tracking_number}', 'success')
    return redirect(url_for('order_confirmation', order_id=order.id))


# ==================== ORDERS ====================

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    orders_with_details = []
    for order in user_orders:
        order_data = {
            'id': order.id, 'total': order.total_amount, 'status': order.status,
            'payment_method': order.payment_method, 'tracking_number': order.tracking_number,
            'created_at': order.created_at, 'estimated_delivery': order.estimated_delivery,
            'items': []
        }
        for item in order.order_items:
            article = data_loader.get_article_by_id(item.article_id)
            if article:
                article['image_url'] = data_loader.get_article_image_url(item.article_id)
                article['quantity'] = item.quantity
                article['price'] = item.price
                order_data['items'].append(article)
        orders_with_details.append(order_data)

    return render_template('orders.html', orders=orders_with_details)


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('orders'))

    items = []
    for item in order.order_items:
        article = data_loader.get_article_by_id(item.article_id)
        if article:
            article['image_url'] = data_loader.get_article_image_url(item.article_id)
            article['quantity'] = item.quantity
            article['price'] = item.price
            items.append(article)

    tracking_history = OrderTracking.query.filter_by(order_id=order_id).order_by(OrderTracking.created_at.asc()).all()
    return render_template('order_tracking.html', order=order, items=items, tracking_history=tracking_history)


@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('orders'))

    items = []
    for item in order.order_items:
        article = data_loader.get_article_by_id(item.article_id)
        if article:
            article['image_url'] = data_loader.get_article_image_url(item.article_id)
            article['quantity'] = item.quantity
            article['price'] = item.price
            items.append(article)

    return render_template('order_confirmation.html', order=order, items=items)


@app.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('orders'))

    if order.status in ['delivered', 'cancelled']:
        flash(f'Cannot cancel order – status is {order.status}', 'warning')
    else:
        order.status = 'cancelled'
        db.session.add(OrderTracking(
            order_id=order.id, status='cancelled',
            message='Order cancelled by customer', location='System'
        ))
        db.session.commit()
        flash('Order cancelled successfully', 'info')

    return redirect(url_for('orders'))


# ==================== FEEDBACK SYSTEM ====================

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback on recommendations"""
    data = request.get_json()
    
    article_id = data.get('article_id')
    feedback_type = data.get('feedback_type')  # 'recommendations', 'complementary', 'outfits'
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not all([article_id, feedback_type, rating]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Rating must be 1-5'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid rating'}), 400
    
    feedback = RecommendationFeedback(
        user_id=current_user.id if current_user.is_authenticated else None,
        article_id=article_id,
        feedback_type=feedback_type,
        rating=rating,
        comment=comment
    )
    db.session.add(feedback)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Thank you for your feedback!'})


@app.route('/feedback_stats')
@login_required
def feedback_stats():
    """View feedback statistics (admin only - you can add role check later)"""
    stats = {
        'recommendations': db.session.query(
            db.func.avg(RecommendationFeedback.rating),
            db.func.count(RecommendationFeedback.id)
        ).filter_by(feedback_type='recommendations').first(),
        
        'complementary': db.session.query(
            db.func.avg(RecommendationFeedback.rating),
            db.func.count(RecommendationFeedback.id)
        ).filter_by(feedback_type='complementary').first(),
        
        'outfits': db.session.query(
            db.func.avg(RecommendationFeedback.rating),
            db.func.count(RecommendationFeedback.id)
        ).filter_by(feedback_type='outfits').first(),
    }
    
    recent_feedback = RecommendationFeedback.query.order_by(
        RecommendationFeedback.created_at.desc()
    ).limit(20).all()
    
    return render_template('feedback_stats.html', stats=stats, recent_feedback=recent_feedback)


# ==================== AI VIRTUAL TRY-ON ====================

@app.route('/api/generate-tryon', methods=['POST'])
@login_required
def generate_tryon():
    """Generate realistic virtual try-on using Gradio API (FREE)"""
    import base64
    from io import BytesIO
    
    try:
        from PIL import Image
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'PIL (Pillow) not installed. Run: pip install pillow'
        }), 500
    
    try:
        from gradio_client import Client
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Gradio client not installed. Run: pip install gradio-client'
        }), 500
    
    try:
        data = request.get_json()
        person_image = data.get('person_image', '')
        garment_image = data.get('garment_image', '')
        
        if not person_image or not garment_image:
            return jsonify({'success': False, 'error': 'Missing images'}), 400
        
        print(f"[TRYON] Starting virtual try-on for user {current_user.id}")
        print(f"[TRYON] Person image type: {'data URL' if person_image.startswith('data:') else 'other'}")
        print(f"[TRYON] Garment image type: {'data URL' if garment_image.startswith('data:') else 'HTTP URL' if garment_image.startswith('http') else 'other'}")
        
        # Handle garment image - might be HTTP URL instead of base64
        if garment_image.startswith('http://') or garment_image.startswith('https://'):
            print(f"[TRYON] Garment is HTTP URL, downloading: {garment_image[:100]}")
            try:
                import requests as req
                response = req.get(garment_image, timeout=10)
                if response.status_code == 200:
                    garment_bytes = response.content
                    # Convert to base64 data URL
                    garment_b64 = base64.b64encode(garment_bytes).decode('utf-8')
                    garment_image = f"data:image/jpeg;base64,{garment_b64}"
                    print(f"[TRYON] Garment downloaded and converted to base64")
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Could not download product image (HTTP {response.status_code})'
                    }), 400
            except Exception as download_error:
                print(f"[TRYON] Garment download error: {download_error}")
                return jsonify({
                    'success': False,
                    'error': f'Could not download product image: {str(download_error)}'
                }), 400
        
        # Remove data URL prefix if present and fix padding
        def clean_base64(b64_string):
            try:
                # Remove data URL prefix
                if 'base64,' in b64_string:
                    b64_string = b64_string.split('base64,')[1]
                
                # URL decode if needed (handles %20, %2B, etc.)
                try:
                    from urllib.parse import unquote
                    b64_string = unquote(b64_string)
                except:
                    pass
                
                # Remove any whitespace, newlines, etc.
                b64_string = ''.join(b64_string.split())
                
                # Replace URL-safe characters back to standard base64
                b64_string = b64_string.replace('-', '+').replace('_', '/')
                
                # Fix padding if needed
                padding = len(b64_string) % 4
                if padding:
                    b64_string += '=' * (4 - padding)
                
                return b64_string
            except Exception as e:
                print(f"[TRYON] clean_base64 error: {e}")
                raise
        
        try:
            person_image_b64 = clean_base64(person_image)
            garment_image_b64 = clean_base64(garment_image)
        except Exception as clean_error:
            print(f"[TRYON] Base64 cleaning error: {clean_error}")
            return jsonify({
                'success': False,
                'error': f'Invalid image format: {str(clean_error)}'
            }), 400
        
        print(f"[TRYON] Base64 cleaned - Person: {len(person_image_b64)} chars, Garment: {len(garment_image_b64)} chars")
        
        # Decode base64 to bytes with better error handling
        try:
            person_bytes = base64.b64decode(person_image_b64, validate=True)
        except Exception as decode_error:
            print(f"[TRYON] Person image decode error: {decode_error}")
            print(f"[TRYON] First 100 chars of person base64: {person_image_b64[:100]}")
            return jsonify({
                'success': False,
                'error': 'Person image format is invalid. Please try uploading a different photo.'
            }), 400
        
        try:
            garment_bytes = base64.b64decode(garment_image_b64, validate=True)
        except Exception as decode_error:
            print(f"[TRYON] Garment image decode error: {decode_error}")
            print(f"[TRYON] First 100 chars of garment base64: {garment_image_b64[:100]}")
            return jsonify({
                'success': False,
                'error': 'Garment image format is invalid. This is likely a system issue.'
            }), 400
        
        person_img = Image.open(BytesIO(person_bytes))
        garment_img = Image.open(BytesIO(garment_bytes))
        
        # Convert to RGB if needed (remove alpha channel)
        if person_img.mode != 'RGB':
            person_img = person_img.convert('RGB')
        if garment_img.mode != 'RGB':
            garment_img = garment_img.convert('RGB')
        
        print(f"[TRYON] Images decoded - Person: {person_img.size}, Garment: {garment_img.size}")
        
        # Save temporarily
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        person_path = os.path.join(temp_dir, f'person_{current_user.id}.jpg')
        garment_path = os.path.join(temp_dir, f'garment_{current_user.id}.jpg')
        
        person_img.save(person_path, 'JPEG', quality=95)
        garment_img.save(garment_path, 'JPEG', quality=95)
        
        print(f"[TRYON] Temp files saved: {person_path}, {garment_path}")
        
        # Use Gradio Client to call the free hosted model
        try:
            print("[TRYON] Connecting to Gradio client...")
            # Connect to the free hosted IDM-VTON on Hugging Face Spaces
            client = Client("yisol/IDM-VTON")
            
            print("[TRYON] Calling predict function...")
            # Call the predict function
            result = client.predict(
                person_path,  # Person image
                garment_path,  # Garment image
                "Dresses",  # Category (can be auto-detected)
                True,  # Use auto-crop
                True,  # Use auto-mask
                api_name="/tryon"
            )
            
            print(f"[TRYON] Result received: {result}")
            
            # Result is a filepath to the generated image
            result_img = Image.open(result[0])  # First output is the result
            
            print(f"[TRYON] Result image size: {result_img.size}")
            
            # Convert to base64
            buffered = BytesIO()
            result_img.save(buffered, format="JPEG", quality=95)
            result_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Cleanup temp files
            try:
                os.remove(person_path)
                os.remove(garment_path)
                print("[TRYON] Temp files cleaned up")
            except Exception as cleanup_err:
                print(f"[TRYON] Cleanup warning: {cleanup_err}")
            
            print("[TRYON] Success! Returning result")
            return jsonify({
                'success': True,
                'image': f'data:image/jpeg;base64,{result_base64}'
            })
            
        except Exception as gradio_error:
            # Fallback: If Gradio fails, return error with helpful message
            error_msg = str(gradio_error)
            print(f"[TRYON] Gradio error: {error_msg}")
            
            # Check if it's a model loading issue
            if 'loading' in error_msg.lower() or 'starting' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'error': 'AI model is loading. Please wait 30 seconds and try again.'
                }), 503
            elif 'queue' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'error': 'Service is busy. Please try again in a moment.'
                }), 503
            else:
                return jsonify({
                    'success': False,
                    'error': f'Virtual try-on service error: {error_msg[:200]}'
                }), 500
            
    except Exception as e:
        print(f'[TRYON] Fatal error: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)[:200]}'
        }), 500


# ==================== 3D TRY-ON ====================

@app.route('/tryon/<int:article_id>')
def tryon(article_id):
    article = data_loader.get_article_by_id(article_id)
    if not article:
        flash('Product not found', 'danger')
        return redirect(url_for('index'))
    article['image_url'] = data_loader.get_article_image_url(article_id)
    return render_template('tryon.html', article=article)


if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)