from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Article, Cart, CartItem, Order, OrderItem
from datetime import datetime

# Home page
def index():
    articles = Article.query.limit(20).all()
    return render_template('index.html', articles=articles)

# Add to cart
@login_required
def add_to_cart(article_id):
    article = Article.query.get_or_404(article_id)

    # Get or create cart for user
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    # Check if item already in cart
    cart_item = CartItem.query.filter_by(cart_id=cart.id, article_id=article_id).first()

    if cart_item:
        cart_item.quantity += 1
        flash('Item quantity updated in cart!', 'success')
    else:
        cart_item = CartItem(cart_id=cart.id, article_id=article_id, quantity=1)
        db.session.add(cart_item)
        flash('Item added to cart!', 'success')

    db.session.commit()

    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Item added to cart'})

    return redirect(request.referrer or url_for('index'))

# Buy Now - Adds to cart and redirects to checkout
@login_required
def buy_now(article_id):
    article = Article.query.get_or_404(article_id)

    # Get or create cart for user
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    # Check if item already in cart
    cart_item = CartItem.query.filter_by(cart_id=cart.id, article_id=article_id).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, article_id=article_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()

    # Redirect directly to checkout
    return redirect(url_for('checkout'))

# View cart
@login_required
def cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart:
        cart_items = []
        subtotal = 0
    else:
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        subtotal = sum(item.article.price * item.quantity for item in cart_items)

    # Calculate shipping and tax
    shipping = 0 if subtotal > 999 else 50
    tax = subtotal * 0.18  # 18% GST
    total = subtotal + shipping + tax

    return render_template('cart.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

# Update cart item quantity
@login_required
def update_cart_item(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    # Verify cart belongs to current user
    if cart_item.cart.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    quantity = data.get('quantity', 1)

    if quantity < 1:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity

    db.session.commit()
    return jsonify({'success': True})

# Remove from cart
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    # Verify cart belongs to current user
    if cart_item.cart.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    db.session.delete(cart_item)
    db.session.commit()

    return jsonify({'success': True})

# Checkout page
@login_required
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart or not cart.items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('cart'))

    cart_items = cart.items
    subtotal = sum(item.article.price * item.quantity for item in cart_items)
    shipping = 0 if subtotal > 999 else 50
    tax = subtotal * 0.18
    total = subtotal + shipping + tax

    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

# Place order
@login_required
def place_order():
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart or not cart.items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('cart'))

    # Get form data
    shipping_name = request.form.get('full_name')
    shipping_email = request.form.get('email')
    shipping_phone = request.form.get('phone')
    address_line1 = request.form.get('address_line1')
    address_line2 = request.form.get('address_line2', '')
    city = request.form.get('city')
    state = request.form.get('state')
    pincode = request.form.get('pincode')
    payment_method = request.form.get('payment_method')

    # Calculate totals
    subtotal = sum(item.article.price  * item.quantity for item in cart.items)
    shipping_cost = 0 if subtotal > 999 else 50
    tax = subtotal * 0.18
    total = subtotal + shipping_cost + tax

    # Create shipping address
    shipping_address = f"{address_line1}"
    if address_line2:
        shipping_address += f", {address_line2}"

    # Create order
    order = Order(
        user_id=current_user.id,
        total_amount=total,
        status='pending',
        payment_method=payment_method,
        payment_status='pending' if payment_method != 'cod' else 'cod',
        shipping_name=shipping_name,
        shipping_email=shipping_email,
        shipping_phone=shipping_phone,
        shipping_address=shipping_address,
        shipping_city=city,
        shipping_state=state,
        shipping_pincode=pincode
    )

    db.session.add(order)
    db.session.flush()  # Get order ID

    # Create order items
    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            article_id=cart_item.article_id,
            quantity=cart_item.quantity,
            price=cart_item.article.price
        )
        db.session.add(order_item)

    # Clear cart
    CartItem.query.filter_by(cart_id=cart.id).delete()

    db.session.commit()

    flash(f'Order placed successfully! Order ID: #{order.id}', 'success')
    return redirect(url_for('order_confirmation', order_id=order.id))

# Order confirmation page
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash('Order not found!', 'danger')
        return redirect(url_for('orders'))

    return render_template('order_confirmation.html', order=order)

# View all orders
@login_required
def orders():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(user_id=current_user.id)\
                        .order_by(Order.created_at.desc())\
                        .paginate(page=page, per_page=10)

    return render_template('orders.html', orders=orders)

# Cancel order
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash('Order not found!', 'danger')
        return redirect(url_for('orders'))

    if order.status != 'pending':
        flash('This order cannot be cancelled!', 'warning')
        return redirect(url_for('orders'))

    order.status = 'cancelled'
    db.session.commit()

    flash('Order cancelled successfully!', 'success')
    return redirect(url_for('orders'))

# Get cart count (API endpoint)
@login_required
def cart_count():
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart:
        count = 0
    else:
        count = sum(item.quantity for item in cart.items)

    return jsonify({'count': count})

# Product detail page
def product_detail(article_id):
    article = Article.query.get_or_404(article_id)

    # Get similar products
    similar_products = Article.query.filter(
        Article.product_type_name == article.product_type_name,
        Article.article_id != article_id
    ).limit(4).all()

    return render_template('product_detail.html',
                         article=article,
                         similar_products=similar_products)