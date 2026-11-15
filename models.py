"""Database models (SQLAlchemy). Works on SQLite and MySQL."""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

ORDER_STATUSES = ["Pending", "Accepted", "Preparing", "Ready", "Delivered", "Rejected", "Cancelled"]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # admin | staff | customer
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    orders = db.relationship("Order", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), default="")

    items = db.relationship("MenuItem", back_populates="category", lazy="dynamic")


class MenuItem(db.Model):
    __tablename__ = "menu_items"
    __table_args__ = (db.CheckConstraint("price >= 0", name="ck_menu_price_nonneg"),)
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(255), default="default.svg")
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    category = db.relationship("Category", back_populates="items")
    order_items = db.relationship("OrderItem", back_populates="menu_item", lazy="dynamic")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending", index=True)
    payment_method = db.Column(db.String(30), nullable=False, default="Cash on Delivery")
    delivery_address = db.Column(db.String(255), nullable=False, default="")
    phone = db.Column(db.String(20), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    __table_args__ = (db.CheckConstraint("quantity > 0", name="ck_orderitem_qty_pos"),)
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # price at time of order

    order = db.relationship("Order", back_populates="items")
    menu_item = db.relationship("MenuItem", back_populates="order_items")

    @property
    def subtotal(self):
        return self.price * self.quantity
