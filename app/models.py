from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Predefined security questions pool
SECURITY_QUESTIONS = [
    "What is the name of your first pet?",
    "What is your mother's maiden name?",
    "What was the name of your first school?",
    "What is the name of the city where you were born?",
    "What is the name of your oldest sibling?",
    "What was your childhood nickname?",
    "What is the make of your first car?",
    "What is your favourite childhood book?",
]

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personalization
    gender = db.Column(db.String(20), nullable=True, default='Unspecified')
    age = db.Column(db.Integer, nullable=True, default=25)
    favorite_color = db.Column(db.String(50), nullable=True)
    
    # Mobile with country code
    country_code = db.Column(db.String(10), nullable=True)   # e.g. "+91"
    mobile_number = db.Column(db.String(20), nullable=True)  # digits only
    
    # Security questions (mandatory)
    security_question_1 = db.Column(db.String(255), nullable=True)
    security_answer_1_hash = db.Column(db.String(255), nullable=True)
    security_question_2 = db.Column(db.String(255), nullable=True)
    security_answer_2_hash = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_security_answers(self, answer1, answer2):
        self.security_answer_1_hash = generate_password_hash(answer1.strip().lower())
        self.security_answer_2_hash = generate_password_hash(answer2.strip().lower())
    
    def check_security_answer_1(self, answer):
        if not self.security_answer_1_hash:
            return False
        return check_password_hash(self.security_answer_1_hash, answer.strip().lower())
    
    def check_security_answer_2(self, answer):
        if not self.security_answer_2_hash:
            return False
        return check_password_hash(self.security_answer_2_hash, answer.strip().lower())
    
    def get_masked_mobile(self):
        if self.mobile_number and len(self.mobile_number) >= 4:
            prefix = self.country_code or ""
            masked = "X" * (len(self.mobile_number) - 3) + self.mobile_number[-3:]
            return f"{prefix} {masked}"
        return "Not set"
    
    def get_masked_email(self):
        if self.email:
            parts = self.email.split('@')
            if len(parts) == 2:
                name = parts[0]
                masked_name = name[0] + '*' * max(1, len(name) - 2) + (name[-1] if len(name) > 1 else '')
                return f"{masked_name}@{parts[1]}"
        return "Not set"
    
    def __repr__(self):
        return f'<User {self.username}>'


class OTPRecord(db.Model):
    """One active OTP per user at a time for password reset."""
    __tablename__ = 'otp_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    otp_hash = db.Column(db.String(255), nullable=False)
    delivery_method = db.Column(db.String(10), nullable=False)  # 'email' or 'mobile'
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def __repr__(self):
        return f'<OTPRecord user={self.user_id} method={self.delivery_method}>'


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_query = db.Column(db.String(200), nullable=False)
    gender_filter = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SearchHistory {self.search_query}>'


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    article_id = db.Column(db.BigInteger, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CartItem user={self.user_id} article={self.article_id}>'


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    
    tracking_number = db.Column(db.String(100), nullable=True)
    estimated_delivery = db.Column(db.DateTime, nullable=True)
    
    shipping_name = db.Column(db.String(100), nullable=True)
    shipping_email = db.Column(db.String(120), nullable=True)
    shipping_phone = db.Column(db.String(20), nullable=True)
    shipping_address = db.Column(db.String(500), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=True)
    shipping_state = db.Column(db.String(100), nullable=True)
    shipping_pincode = db.Column(db.String(10), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    tracking_updates = db.relationship('OrderTracking', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id} user={self.user_id}>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    article_id = db.Column(db.BigInteger, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f'<OrderItem order={self.order_id} article={self.article_id}>'


class OrderTracking(db.Model):
    __tablename__ = 'order_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrderTracking order={self.order_id} status={self.status}>'


class RecommendationFeedback(db.Model):
    __tablename__ = 'recommendation_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL if not logged in
    article_id = db.Column(db.BigInteger, nullable=False)  # The product they were viewing
    feedback_type = db.Column(db.String(50), nullable=False)  # 'recommendations', 'complementary', 'outfits'
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Feedback article={self.article_id} rating={self.rating}>'