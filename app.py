"""Online Food Ordering & Restaurant Management System (Flask)."""
import os
import random
import uuid
from datetime import timedelta
from decimal import Decimal
from functools import wraps
from urllib.parse import urlparse

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from flask_wtf import CSRFProtect, FlaskForm
from flask_wtf.file import FileAllowed, FileField
from sqlalchemy import func
from werkzeug.utils import secure_filename
from wtforms import (BooleanField, DecimalField, PasswordField, SelectField,
                     StringField, TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, NumberRange,
                                Regexp, ValidationError)

from config import Config
from models import Category, MenuItem, Order, OrderItem, ORDER_STATUSES, User, db, utcnow
from seed_data import CATEGORIES, ITEMS

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.instance_path, exist_ok=True)
db.init_app(app)
csrf = CSRFProtect(app)

MAX_QTY = 20
# status -> statuses it can move to (cancel by admin is added in allowed_statuses)
NEXT_STATUS = {"Pending": ["Accepted", "Rejected"], "Accepted": ["Preparing"],
               "Preparing": ["Ready"], "Ready": ["Delivered"]}
ADMIN_CAN_CANCEL = ("Pending", "Accepted", "Preparing")
STATUS_COLORS = {"Pending": "#fcc419", "Accepted": "#339af0", "Preparing": "#ff922b", "Ready": "#845ef7",
                 "Delivered": "#40c057", "Rejected": "#fa5252", "Cancelled": "#868e96"}
TRACK_STEPS = ["Pending", "Accepted", "Preparing", "Ready", "Delivered"]


# --------------------------------------------------------------------------- helpers
def allowed_statuses(order, role):
    options = list(NEXT_STATUS.get(order.status, []))
    if role == "admin" and order.status in ADMIN_CAN_CANCEL:
        options.append("Cancelled")
    return options


def home_for(user):
    return url_for({"admin": "admin_dashboard", "staff": "staff_dashboard"}.get(user.role, "home"))


def login_required(view):
    @wraps(view)
    def wrapper(*a, **kw):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapper


def roles_required(*roles):
    def deco(view):
        @wraps(view)
        @login_required
        def wrapper(*a, **kw):
            if g.user.role not in roles:
                abort(403)
            return view(*a, **kw)
        return wrapper
    return deco


def back(default_endpoint):
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for(default_endpoint))


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def parse_qty(value):
    try:
        q = int(value)
    except (TypeError, ValueError):
        return None
    return q if 1 <= q <= MAX_QTY else None


def get_cart():
    return session.get("cart", {})


def cart_lines():
    """Return ([(item, qty, subtotal)], total) with prices read from the database."""
    cart = get_cart()
    ids = [int(k) for k in cart]
    items = {i.id: i for i in MenuItem.query.filter(MenuItem.id.in_(ids))} if ids else {}
    lines, total = [], Decimal("0")
    for key, qty in cart.items():
        item = items.get(int(key))
        if item:
            sub = item.price * qty
            lines.append((item, qty, sub))
            total += sub
    return lines, total


def store_image(file_storage):
    """Save an uploaded image and return its filename.
    To move to Amazon S3 later, replace the body of this function with an S3 upload
    and return the S3 URL (templates already accept full http(s) URLs)."""
    ext = secure_filename(file_storage.filename).rsplit(".", 1)[-1].lower()
    name = f"up_{uuid.uuid4().hex[:12]}.{ext}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], name))
    return name


def revenue_by_day(days):
    today = utcnow().date()
    start = today - timedelta(days=days - 1)
    rows = Order.query.filter(Order.status == "Delivered", Order.created_at >= start).all()
    buckets = {start + timedelta(days=i): [Decimal("0"), 0] for i in range(days)}
    for o in rows:
        d = o.created_at.date()
        if d in buckets:
            buckets[d][0] += o.total_amount
            buckets[d][1] += 1
    return buckets


@app.before_request
def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = db.session.get(User, uid)
        if g.user is None:
            session.clear()


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


@app.context_processor
def inject_globals():
    return {"app_name": app.config["APP_NAME"], "cart_count": sum(get_cart().values()),
            "TRACK_STEPS": TRACK_STEPS, "ORDER_STATUSES": ORDER_STATUSES}


@app.template_filter("inr")
def inr(value):
    return "₹{:,.2f}".format(Decimal(value or 0))


@app.template_filter("local_dt")
def local_dt(value, fmt="%d %b %Y, %I:%M %p"):
    if not value:
        return ""
    return (value + timedelta(minutes=app.config["DISPLAY_UTC_OFFSET_MINUTES"])).strftime(fmt)


@app.template_filter("food_img")
def food_img(item):
    img = item.image or "default.svg"
    if img.startswith(("http://", "https://")):
        return img
    return url_for("static", filename="images/foods/" + img)


@app.errorhandler(403)
def forbidden(_e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_e):
    flash("That file is too large (max 2 MB).", "danger")
    return redirect(url_for("manage_food"))


# --------------------------------------------------------------------------- forms
class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(2, 100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField("Password", validators=[DataRequired(), Length(8, 128)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", "Passwords do not match.")])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class CategoryForm(FlaskForm):
    name = StringField("Category name", validators=[DataRequired(), Length(2, 80)])
    description = StringField("Description", validators=[Length(max=255)])


class FoodForm(FlaskForm):
    name = StringField("Food name", validators=[DataRequired(), Length(2, 120)])
    category_id = SelectField("Category", coerce=int)
    description = TextAreaField("Description", validators=[Length(max=1000)])
    price = DecimalField("Price (₹)", places=2, validators=[DataRequired(), NumberRange(0.01, 99999)])
    image = FileField("Image (JPG, PNG or WEBP, max 2 MB)", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only.")])
    is_available = BooleanField("Available for ordering", default=True)


class UserForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(2, 100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    role = SelectField("Role", choices=[("staff", "Restaurant staff"), ("admin", "Administrator")])
    password = PasswordField("Temporary password", validators=[DataRequired(), Length(8, 128)])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists.")


class CheckoutForm(FlaskForm):
    address = TextAreaField("Delivery address", validators=[DataRequired(), Length(10, 255)])
    phone = StringField("Phone number", validators=[DataRequired(), Regexp(r"^[0-9+\-\s]{8,15}$", message="Enter a valid phone number.")])


# --------------------------------------------------------------------------- public pages
@app.route("/")
def home():
    featured = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.id).limit(8).all()
    hero = MenuItem.query.filter(MenuItem.is_available.is_(True),
                                 MenuItem.name.in_(["Hyderabadi Chicken Biryani", "Cheese Burger", "Gulab Jamun"])).all()
    hero = (hero + [i for i in featured if i not in hero])[:3]
    return render_template("home.html", featured=featured, hero=hero, categories=Category.query.order_by(Category.id).all())


@app.route("/menu")
def menu():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", type=int)
    query = MenuItem.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(MenuItem.name.ilike(like), MenuItem.description.ilike(like)))
    if cat:
        query = query.filter_by(category_id=cat)
    items = query.order_by(MenuItem.is_available.desc(), MenuItem.name).all()
    return render_template("menu.html", items=items, categories=Category.query.order_by(Category.id).all(), q=q, selected=cat)


@app.route("/food/<int:item_id>")
def food_detail(item_id):
    item = db.get_or_404(MenuItem, item_id)
    related = MenuItem.query.filter(MenuItem.category_id == item.category_id, MenuItem.id != item.id,
                                    MenuItem.is_available.is_(True)).limit(4).all()
    return render_template("food_detail.html", item=item, related=related)


# --------------------------------------------------------------------------- auth
@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(home_for(g.user))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(), role="customer")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(home_for(g.user))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            cart = session.get("cart")
            session.clear()  # prevents session fixation
            session["user_id"] = user.id
            session.permanent = True
            if cart and user.role == "customer":
                session["cart"] = cart
            flash(f"Welcome back, {user.name.split()[0]}!", "success")
            return redirect(safe_next(request.args.get("next")) or home_for(user))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# --------------------------------------------------------------------------- cart & checkout
@app.route("/cart")
@roles_required("customer")
def cart():
    lines, total = cart_lines()
    return render_template("cart.html", lines=lines, total=total, max_qty=MAX_QTY)


@app.route("/cart/add/<int:item_id>", methods=["POST"])
@roles_required("customer")
def cart_add(item_id):
    item = db.get_or_404(MenuItem, item_id)
    qty = parse_qty(request.form.get("quantity", 1))
    if qty is None:
        flash(f"Quantity must be between 1 and {MAX_QTY}.", "danger")
        return back("menu")
    if not item.is_available:
        flash(f"Sorry, {item.name} is currently unavailable.", "warning")
        return back("menu")
    cart_ = get_cart()
    cart_[str(item.id)] = min(cart_.get(str(item.id), 0) + qty, MAX_QTY)
    session["cart"] = cart_
    flash(f"{item.name} added to your cart.", "success")
    return back("menu")


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@roles_required("customer")
def cart_update(item_id):
    qty = parse_qty(request.form.get("quantity"))
    cart_ = get_cart()
    if str(item_id) not in cart_:
        return redirect(url_for("cart"))
    if qty is None:
        flash(f"Quantity must be between 1 and {MAX_QTY}.", "danger")
    else:
        cart_[str(item_id)] = qty
        session["cart"] = cart_
        flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@roles_required("customer")
def cart_remove(item_id):
    cart_ = get_cart()
    cart_.pop(str(item_id), None)
    session["cart"] = cart_
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@roles_required("customer")
def checkout():
    lines, total = cart_lines()
    if not lines:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("menu"))
    form = CheckoutForm()
    if form.validate_on_submit():
        unavailable = [i.name for i, _q, _s in lines if not i.is_available]
        if unavailable:
            flash("Please remove unavailable items: " + ", ".join(unavailable), "danger")
            return redirect(url_for("cart"))
        order = Order(user_id=g.user.id, total_amount=total, status="Pending", payment_method="Cash on Delivery",
                      delivery_address=form.address.data.strip(), phone=form.phone.data.strip())
        for item, qty, _s in lines:
            order.items.append(OrderItem(menu_item_id=item.id, quantity=qty, price=item.price))
        db.session.add(order)
        db.session.commit()
        session.pop("cart", None)
        return redirect(url_for("order_confirmation", order_id=order.id))
    return render_template("checkout.html", form=form, lines=lines, total=total)


# --------------------------------------------------------------------------- orders
def get_order_or_403(order_id):
    order = db.get_or_404(Order, order_id)
    if g.user.role == "customer" and order.user_id != g.user.id:
        abort(403)  # customers may only see their own orders
    return order


@app.route("/orders")
@roles_required("customer")
def my_orders():
    orders = Order.query.filter_by(user_id=g.user.id).order_by(Order.created_at.desc()).all()
    return render_template("my_orders.html", orders=orders)


@app.route("/orders/<int:order_id>")
@login_required
def order_details(order_id):
    order = get_order_or_403(order_id)
    return render_template("order_details.html", order=order, options=allowed_statuses(order, g.user.role))


@app.route("/orders/<int:order_id>/confirmation")
@roles_required("customer")
def order_confirmation(order_id):
    return render_template("order_confirmation.html", order=get_order_or_403(order_id))


@app.route("/orders/<int:order_id>/cancel", methods=["POST"])
@roles_required("customer")
def cancel_order(order_id):
    order = get_order_or_403(order_id)
    if order.status != "Pending":
        flash("Only orders that are still Pending can be cancelled.", "danger")
    else:
        order.status = "Cancelled"
        db.session.commit()
        flash("Your order has been cancelled.", "info")
    return redirect(url_for("order_details", order_id=order.id))


@app.route("/orders/<int:order_id>/status", methods=["POST"])
@roles_required("staff", "admin")
def update_status(order_id):
    order = db.get_or_404(Order, order_id)
    new = request.form.get("status", "")
    if new not in allowed_statuses(order, g.user.role):
        flash(f"Cannot change an order from {order.status} to {new or '—'}.", "danger")
    else:
        order.status = new
        db.session.commit()
        flash(f"Order #{order.id} is now {new}.", "success")
    return back("manage_orders")


# --------------------------------------------------------------------------- staff & admin: orders / food
@app.route("/staff")
@roles_required("staff")
def staff_dashboard():
    counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    today = utcnow().date()
    today_orders = Order.query.filter(Order.created_at >= today).count()
    incoming = Order.query.filter(Order.status.in_(["Pending", "Accepted", "Preparing", "Ready"])) \
        .order_by(Order.created_at).limit(8).all()
    unavailable = MenuItem.query.filter_by(is_available=False).all()
    return render_template("staff_dashboard.html", counts=counts, today_orders=today_orders,
                           incoming=incoming, unavailable=unavailable)


@app.route("/manage/orders")
@roles_required("staff", "admin")
def manage_orders():
    status = request.args.get("status", "")
    query = Order.query
    if status in ORDER_STATUSES:
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).limit(200).all()
    counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    return render_template("manage_orders.html", orders=orders, counts=counts, current=status,
                           allowed=lambda o: allowed_statuses(o, g.user.role))


@app.route("/manage/food")
@roles_required("staff", "admin")
def manage_food():
    items = MenuItem.query.order_by(MenuItem.category_id, MenuItem.name).all()
    return render_template("manage_food.html", items=items)


@app.route("/manage/food/new", methods=["GET", "POST"])
@app.route("/manage/food/<int:item_id>/edit", methods=["GET", "POST"])
@roles_required("staff", "admin")
def food_form(item_id=None):
    item = db.get_or_404(MenuItem, item_id) if item_id else None
    form = FoodForm(obj=item)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name)]
    if not form.category_id.choices:
        flash("Create a category first.", "warning")
        return redirect(url_for("manage_food"))
    if form.validate_on_submit():
        if item is None:
            item = MenuItem()
            db.session.add(item)
        item.name = form.name.data.strip()
        item.category_id = form.category_id.data
        item.description = (form.description.data or "").strip()
        item.price = form.price.data
        item.is_available = form.is_available.data
        if form.image.data and getattr(form.image.data, "filename", ""):
            item.image = store_image(form.image.data)
        elif not item.image:
            item.image = "default.svg"
        db.session.commit()
        flash(f"“{item.name}” saved.", "success")
        return redirect(url_for("manage_food"))
    return render_template("food_form.html", form=form, item=item)


@app.route("/manage/food/<int:item_id>/toggle", methods=["POST"])
@roles_required("staff", "admin")
def food_toggle(item_id):
    item = db.get_or_404(MenuItem, item_id)
    item.is_available = not item.is_available
    db.session.commit()
    flash(f"{item.name} is now {'available' if item.is_available else 'unavailable'}.", "success")
    return redirect(url_for("manage_food"))


@app.route("/admin/food/<int:item_id>/delete", methods=["POST"])
@roles_required("admin")
def food_delete(item_id):
    item = db.get_or_404(MenuItem, item_id)
    if item.order_items.count():
        flash(f"“{item.name}” appears in past orders and cannot be deleted. Mark it unavailable instead.", "warning")
    else:
        db.session.delete(item)
        db.session.commit()
        flash("Food item deleted.", "success")
    return redirect(url_for("manage_food"))


# --------------------------------------------------------------------------- admin
@app.route("/admin")
@roles_required("admin")
def admin_dashboard():
    stats = {
        "customers": User.query.filter_by(role="customer").count(),
        "food_items": MenuItem.query.count(),
        "orders": Order.query.count(),
        "revenue": db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(Order.status == "Delivered").scalar(),
        "pending": Order.query.filter_by(status="Pending").count(),
    }
    series = revenue_by_day(7)
    chart = {"labels": [d.strftime("%a %d") for d in series],
             "revenue": [float(v[0]) for v in series.values()],
             "orders": [v[1] for v in series.values()]}
    status_counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    status_chart = {"labels": [s for s in ORDER_STATUSES if status_counts.get(s)],
                    "values": [status_counts[s] for s in ORDER_STATUSES if status_counts.get(s)],
                    "colors": [STATUS_COLORS[s] for s in ORDER_STATUSES if status_counts.get(s)]}
    recent = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    top = top_items(None, 4)
    return render_template("admin_dashboard.html", stats=stats, chart=chart, status_chart=status_chart, recent=recent, top=top)


def top_items(start, limit):
    q = (db.session.query(MenuItem, func.sum(OrderItem.quantity), func.sum(OrderItem.quantity * OrderItem.price))
         .join(OrderItem, OrderItem.menu_item_id == MenuItem.id).join(Order, Order.id == OrderItem.order_id)
         .filter(Order.status == "Delivered"))
    if start:
        q = q.filter(Order.created_at >= start)
    return q.group_by(MenuItem.id).order_by(func.sum(OrderItem.quantity).desc()).limit(limit).all()


@app.route("/admin/reports")
@roles_required("admin")
def reports():
    days = request.args.get("days", 30, type=int)
    days = days if days in (7, 30, 90) else 30
    start = utcnow().date() - timedelta(days=days - 1)
    orders = Order.query.filter(Order.created_at >= start).all()
    delivered = [o for o in orders if o.status == "Delivered"]
    revenue = sum((o.total_amount for o in delivered), Decimal("0"))
    summary = {"orders": len(orders), "delivered": len(delivered), "revenue": revenue,
               "avg": (revenue / len(delivered)) if delivered else Decimal("0"),
               "cancelled": sum(1 for o in orders if o.status in ("Cancelled", "Rejected"))}
    by_status = {s: sum(1 for o in orders if o.status == s) for s in ORDER_STATUSES}
    daily = revenue_by_day(days)
    by_category = (db.session.query(Category.name, func.sum(OrderItem.quantity * OrderItem.price))
                   .join(MenuItem, MenuItem.category_id == Category.id)
                   .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
                   .join(Order, Order.id == OrderItem.order_id)
                   .filter(Order.status == "Delivered", Order.created_at >= start)
                   .group_by(Category.id).order_by(func.sum(OrderItem.quantity * OrderItem.price).desc()).all())
    chart = {"labels": [d.strftime("%d %b") for d in daily], "revenue": [float(v[0]) for v in daily.values()]}
    return render_template("reports.html", days=days, summary=summary, by_status=by_status, daily=daily,
                           top=top_items(start, 5), by_category=by_category, chart=chart)


@app.route("/admin/categories", methods=["GET", "POST"])
@app.route("/admin/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def manage_categories(cat_id=None):
    editing = db.get_or_404(Category, cat_id) if cat_id else None
    form = CategoryForm(obj=editing)
    if form.validate_on_submit():
        name = form.name.data.strip()
        clash = Category.query.filter(func.lower(Category.name) == name.lower())
        if editing:
            clash = clash.filter(Category.id != editing.id)
        if clash.first():
            form.name.errors.append("A category with this name already exists.")
        else:
            cat = editing or Category()
            cat.name, cat.description = name, (form.description.data or "").strip()
            db.session.add(cat)
            db.session.commit()
            flash("Category saved.", "success")
            return redirect(url_for("manage_categories"))
    cats = Category.query.order_by(Category.name).all()
    return render_template("manage_categories.html", form=form, editing=editing, cats=cats)


@app.route("/admin/categories/<int:cat_id>/delete", methods=["POST"])
@roles_required("admin")
def category_delete(cat_id):
    cat = db.get_or_404(Category, cat_id)
    if cat.items.count():
        flash("This category still has food items. Move or delete them first.", "warning")
    else:
        db.session.delete(cat)
        db.session.commit()
        flash("Category deleted.", "success")
    return redirect(url_for("manage_categories"))


@app.route("/admin/users", methods=["GET", "POST"])
@roles_required("admin")
def manage_users():
    form = UserForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(), role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"{user.role.title()} account created for {user.name}.", "success")
        return redirect(url_for("manage_users"))
    users = User.query.order_by(User.role, User.name).all()
    counts = dict(db.session.query(Order.user_id, func.count(Order.id)).group_by(Order.user_id).all())
    return render_template("manage_users.html", form=form, users=users, counts=counts)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@roles_required("admin")
def user_delete(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == g.user.id:
        flash("You cannot delete your own account.", "danger")
    elif user.orders.count():
        flash("This user has orders and cannot be deleted.", "warning")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", "success")
    return redirect(url_for("manage_users"))


# --------------------------------------------------------------------------- CLI commands
@app.cli.command("init-db")
def init_db_command():
    """Create all database tables."""
    db.create_all()
    click.echo("Database tables created.")


@app.cli.command("seed")
def seed_command():
    """Add sample categories and food items (safe to run twice)."""
    db.create_all()
    cats = {}
    for name, desc in CATEGORIES:
        cat = Category.query.filter_by(name=name).first() or Category(name=name, description=desc)
        db.session.add(cat)
        cats[name] = cat
    db.session.flush()
    added = 0
    for cat_name, name, desc, price, image in ITEMS:
        if not MenuItem.query.filter_by(name=name).first():
            db.session.add(MenuItem(category=cats[cat_name], name=name, description=desc, price=Decimal(price), image=image))
            added += 1
    db.session.commit()
    click.echo(f"Seed complete: {len(cats)} categories, {added} new food items.")


@app.cli.command("create-admin")
@click.option("--name", prompt="Admin name")
@click.option("--email", prompt="Admin email")
@click.password_option("--password", prompt="Admin password (min 8 chars)")
def create_admin_command(name, email, password):
    """Create the first administrator (password is typed hidden, never stored in plain text)."""
    db.create_all()
    email = email.strip().lower()
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")
    if User.query.filter_by(email=email).first():
        raise click.ClickException("A user with that email already exists.")
    user = User(name=name.strip(), email=email, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin account created for {email}.")


@app.cli.command("demo-data")
@click.password_option("--password", prompt="Password for the demo staff and customer accounts")
def demo_data_command(password):
    """Optional: create demo staff/customers and sample orders so dashboards look alive."""
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")
    items = MenuItem.query.all()
    if not items:
        raise click.ClickException("Run 'flask seed' first.")
    people = [("Kitchen Staff", "staff@example.com", "staff"), ("Asha Reddy", "asha@example.com", "customer"),
              ("Ravi Kumar", "ravi@example.com", "customer"), ("Meera Shah", "meera@example.com", "customer")]
    users = []
    for name, email, role in people:
        u = User.query.filter_by(email=email).first()
        if not u:
            u = User(name=name, email=email, role=role)
            u.set_password(password)
            db.session.add(u)
        users.append(u)
    db.session.flush()
    customers = [u for u in users if u.role == "customer"]
    rng = random.Random(7)
    created = 0
    for day in range(9, -1, -1):
        for _ in range(rng.randint(2, 5)):
            status = "Delivered" if day > 0 else rng.choice(["Pending", "Accepted", "Preparing", "Ready", "Delivered"])
            if rng.random() < 0.08:
                status = rng.choice(["Cancelled", "Rejected"])
            order = Order(user=rng.choice(customers), status=status, total_amount=0,
                          delivery_address="Plot 12, Road No. 5, Banjara Hills, Hyderabad", phone="9876543210",
                          created_at=utcnow() - timedelta(days=day, hours=rng.randint(0, 8)))
            total = Decimal("0")
            for it in rng.sample(items, rng.randint(1, 3)):
                q = rng.randint(1, 3)
                order.items.append(OrderItem(menu_item_id=it.id, quantity=q, price=it.price))
                total += it.price * q
            order.total_amount = total
            db.session.add(order)
            created += 1
    db.session.commit()
    click.echo(f"Demo data added: {created} orders. Logins: staff@example.com, asha@example.com (use the password you typed).")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("APP_ENV", "development") != "production")
