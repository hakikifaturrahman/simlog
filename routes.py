import uuid
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Product, Supplier, Order, Shipment, FinancialRecord, SupplierTransaction

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Landing Page Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/company-profile')
def company_profile():
    return render_template('company_profile.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/rates')
def rates():
    return render_template('rates.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Dashboard Routes
@app.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    # Get user statistics
    total_orders = Order.query.filter_by(user_id=current_user.id).count()
    pending_orders = Order.query.filter_by(user_id=current_user.id, status='pending').count()
    in_transit = Order.query.join(Shipment).filter(
        Order.user_id == current_user.id,
        Shipment.status == 'in_transit'
    ).count()
    
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).limit(5).all()
    
    return render_template('dashboard/user_dashboard.html', 
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         in_transit=in_transit,
                         recent_orders=recent_orders)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    # Get admin statistics
    total_products = Product.query.count()
    low_stock_count = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    total_suppliers = Supplier.query.count()
    
    # Recent activities
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()
    low_stock_products = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).all()
    
    return render_template('dashboard/admin_dashboard.html',
                         total_products=total_products,
                         low_stock_count=low_stock_count,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_suppliers=total_suppliers,
                         recent_orders=recent_orders,
                         low_stock_products=low_stock_products)

# User Logistics Routes
@app.route('/logistics')
@login_required
def logistics():
    products = Product.query.all()
    low_stock_products = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).all()
    return render_template('dashboard/logistics.html', products=products, low_stock_products=low_stock_products)

# User Orders Routes
@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    suppliers = Supplier.query.all()
    products = Product.query.all()
    return render_template('dashboard/orders.html', orders=user_orders, suppliers=suppliers, products=products)

@app.route('/orders/create', methods=['POST'])
@login_required
def create_order():
    supplier_id = request.form['supplier_id']
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])
    package_type = request.form['package_type']
    
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found')
        return redirect(url_for('orders'))
    
    # Calculate costs based on package type
    logistics_costs = {'basic': 50000, 'standard': 100000, 'premium': 200000}
    logistics_cost = logistics_costs.get(package_type, 50000)
    
    unit_price = product.unit_price
    total_cost = (unit_price * quantity) + logistics_cost
    
    order = Order(
        user_id=current_user.id,
        supplier_id=supplier_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        total_cost=total_cost,
        logistics_cost=logistics_cost,
        package_type=package_type
    )
    
    db.session.add(order)
    db.session.commit()
    
    flash('Order created successfully')
    return redirect(url_for('orders'))

@app.route('/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role != 'admin':
        flash('Unauthorized')
        return redirect(url_for('orders'))
    
    order.status = 'confirmed'
    
    # Create shipment record
    tracking_number = f"SIMLOG{uuid.uuid4().hex[:8].upper()}"
    shipment = Shipment(
        order_id=order.id,
        tracking_number=tracking_number,
        estimated_delivery=datetime.utcnow() + timedelta(days=7)
    )
    
    # Create financial record
    financial_record = FinancialRecord(
        order_id=order.id,
        transaction_type='income',
        amount=order.total_cost,
        description=f'Order payment for {order.product.name}'
    )
    
    # Create supplier transaction
    supplier_transaction = SupplierTransaction(
        supplier_id=order.supplier_id,
        order_id=order.id,
        amount=order.total_cost - order.logistics_cost
    )
    
    db.session.add(shipment)
    db.session.add(financial_record)
    db.session.add(supplier_transaction)
    db.session.commit()
    
    flash('Order confirmed successfully')
    return redirect(url_for('orders'))

# User Distribution Routes
@app.route('/distribution')
@login_required
def distribution():
    user_shipments = db.session.query(Shipment).join(Order).filter(Order.user_id == current_user.id).all()
    return render_template('dashboard/distribution.html', shipments=user_shipments)

@app.route('/suppliers')
@login_required
def view_suppliers():
    if current_user.role == 'admin':
        return redirect(url_for('admin_suppliers'))
    
    suppliers = Supplier.query.all()
    return render_template('dashboard/suppliers.html', suppliers=suppliers)

# Admin Routes
@app.route('/admin/logistics')
@login_required
def admin_logistics():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    products = Product.query.all()
    low_stock_products = Product.query.filter(Product.stock_quantity <= Product.min_stock_level).all()
    return render_template('dashboard/admin_logistics.html', products=products, low_stock_products=low_stock_products)

@app.route('/admin/products/create', methods=['POST'])
@login_required
def create_product():
    if current_user.role != 'admin':
        flash('Unauthorized')
        return redirect(url_for('user_dashboard'))
    
    name = request.form['name']
    description = request.form['description']
    stock_quantity = int(request.form['stock_quantity'])
    min_stock_level = int(request.form['min_stock_level'])
    unit_price = float(request.form['unit_price'])
    
    product = Product(
        name=name,
        description=description,
        stock_quantity=stock_quantity,
        min_stock_level=min_stock_level,
        unit_price=unit_price
    )
    
    db.session.add(product)
    db.session.commit()
    
    flash('Product created successfully')
    return redirect(url_for('admin_logistics'))

@app.route('/admin/products/<int:product_id>/update', methods=['POST'])
@login_required
def update_product_stock(product_id):
    if current_user.role != 'admin':
        flash('Unauthorized')
        return redirect(url_for('user_dashboard'))
    
    product = Product.query.get_or_404(product_id)
    new_stock = int(request.form['stock_quantity'])
    
    product.stock_quantity = new_stock
    product.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash('Stock updated successfully')
    return redirect(url_for('admin_logistics'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('dashboard/admin_orders.html', orders=all_orders)

@app.route('/admin/distribution')
@login_required
def admin_distribution():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    all_shipments = Shipment.query.join(Order).order_by(Shipment.id.desc()).all()
    return render_template('dashboard/admin_distribution.html', shipments=all_shipments)

@app.route('/admin/shipments/<int:shipment_id>/update', methods=['POST'])
@login_required
def update_shipment_status(shipment_id):
    if current_user.role != 'admin':
        flash('Unauthorized')
        return redirect(url_for('user_dashboard'))
    
    shipment = Shipment.query.get_or_404(shipment_id)
    new_status = request.form['status']
    current_location = request.form.get('current_location', '')
    
    shipment.status = new_status
    shipment.current_location = current_location
    
    if new_status == 'in_transit' and not shipment.shipped_date:
        shipment.shipped_date = datetime.utcnow()
    elif new_status == 'delivered':
        shipment.actual_delivery = datetime.utcnow()
        # Update order status
        shipment.order.status = 'delivered'
    
    db.session.commit()
    
    flash('Shipment status updated successfully')
    return redirect(url_for('admin_distribution'))

@app.route('/admin/suppliers')
@login_required
def admin_suppliers():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    suppliers = Supplier.query.all()
    return render_template('dashboard/admin_suppliers.html', suppliers=suppliers)

@app.route('/admin/suppliers/create', methods=['POST'])
@login_required
def create_supplier():
    if current_user.role != 'admin':
        flash('Unauthorized')
        return redirect(url_for('user_dashboard'))
    
    name = request.form['name']
    contact_person = request.form['contact_person']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    
    supplier = Supplier(
        name=name,
        contact_person=contact_person,
        email=email,
        phone=phone,
        address=address
    )
    
    db.session.add(supplier)
    db.session.commit()
    
    flash('Supplier created successfully')
    return redirect(url_for('admin_suppliers'))

@app.route('/admin/financial')
@login_required
def admin_financial():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    financial_records = FinancialRecord.query.order_by(FinancialRecord.transaction_date.desc()).all()
    
    # Calculate totals
    total_income = db.session.query(db.func.sum(FinancialRecord.amount)).filter_by(transaction_type='income').scalar() or 0
    total_expenses = db.session.query(db.func.sum(FinancialRecord.amount)).filter_by(transaction_type='expense').scalar() or 0
    net_profit = total_income - total_expenses
    
    return render_template('dashboard/admin_financial.html', 
                         financial_records=financial_records,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_profit=net_profit)

# Initialize default admin user
def create_default_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@simlog.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# Create default admin when app starts
with app.app_context():
    create_default_admin()
