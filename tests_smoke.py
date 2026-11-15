"""Smoke test of every role and flow. Run:  python tests_smoke.py   (uses a temporary SQLite DB)"""
import os, re, tempfile
tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "t.db")
os.environ["SECRET_KEY"] = "test-secret"
from app import app, db
from models import User, Order
from click.testing import CliRunner

app.config.update(TESTING=True)
runner = app.test_cli_runner()
with app.app_context():
    assert runner.invoke(args=["init-db"]).exit_code == 0
    r = runner.invoke(args=["seed"]); assert r.exit_code == 0, r.output
    r = runner.invoke(args=["seed"]); assert "0 new" in r.output
    r = runner.invoke(args=["create-admin", "--name", "Boss", "--email", "Admin@Example.com"], input="Adm1nPass!\nAdm1nPass!\n"); assert r.exit_code == 0, r.output
    r = runner.invoke(args=["demo-data"], input="DemoPass1!\nDemoPass1!\n"); assert r.exit_code == 0, r.output

def token(c, url="/login"):
    html = c.get(url).get_data(as_text=True)
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)

def login(c, email, pw):
    return c.post("/login", data={"email": email, "password": pw, "csrf_token": token(c)}, follow_redirects=True)

def ok(resp, code=200): assert resp.status_code == code, (resp.status_code, resp.request.path)

# CSRF enforced
c = app.test_client(); ok(c.post("/login", data={"email": "a@b.c", "password": "x"}), 400)
app.config["WTF_CSRF_ENABLED"] = True

# public pages
c = app.test_client()
for u in ["/", "/menu", "/menu?q=biryani", "/menu?category=3", "/food/1", "/login", "/register"]: ok(c.get(u))
assert "Hyderabadi Chicken Biryani" in c.get("/menu?q=biryani").get_data(as_text=True)
ok(c.get("/food/9999"), 404); ok(c.get("/cart"), 302); ok(c.get("/admin"), 302)

# register + login customer
html = c.post("/register", data={"name": "Test User", "email": "t@example.com", "password": "Passw0rd!", "confirm": "Passw0rd!", "csrf_token": token(c, "/register")}, follow_redirects=True).get_data(as_text=True)
assert "Account created" in html
assert "Invalid email" in login(c, "t@example.com", "wrong").get_data(as_text=True)
assert "Welcome back" in login(c, "t@example.com", "Passw0rd!").get_data(as_text=True)

# cart, validation, checkout
tok = token(c, "/menu")
assert "added" in c.post("/cart/add/1", data={"quantity": 2, "csrf_token": tok}, follow_redirects=True).get_data(as_text=True)
c.post("/cart/add/7", data={"quantity": 1, "csrf_token": tok})
assert "between 1 and 20" in c.post("/cart/add/2", data={"quantity": 0, "csrf_token": tok}, follow_redirects=True).get_data(as_text=True)
assert "between 1 and 20" in c.post("/cart/update/1", data={"quantity": 999, "csrf_token": tok}, follow_redirects=True).get_data(as_text=True)
c.post("/cart/update/1", data={"quantity": 3, "csrf_token": tok})
html = c.get("/cart").get_data(as_text=True); assert "₹660.00" in html and "₹340.00" in html, "cart math"
c.post("/cart/remove/7", data={"csrf_token": tok})
html = c.get("/checkout").get_data(as_text=True); assert "₹660.00" in html
r = c.post("/checkout", data={"address": "short", "phone": "123", "csrf_token": token(c, "/checkout")}); assert b"Field must be between" in r.data or b"valid phone" in r.data
r = c.post("/checkout", data={"address": "12 Main Road, Hyderabad", "phone": "9876543210", "csrf_token": token(c, "/checkout")})
ok(r, 302); oid = int(re.search(r"/orders/(\d+)/", r.location).group(1))
assert "Thank you" in c.get(r.location).get_data(as_text=True)
assert c.get("/cart", follow_redirects=True) and "empty" in c.get("/cart").get_data(as_text=True).lower()
ok(c.get("/my_orders" if False else "/orders")); ok(c.get(f"/orders/{oid}"))
assert "Pending" in c.get(f"/orders/{oid}").get_data(as_text=True)

# customer isolation / authorization
with app.app_context():
    other = Order.query.filter(Order.user_id != User.query.filter_by(email="t@example.com").first().id).first().id
ok(c.get(f"/orders/{other}"), 403)
for u in ["/admin", "/staff", "/manage/orders", "/manage/food", "/admin/users", "/admin/reports", "/admin/categories"]: ok(c.get(u), 403)
ok(c.post(f"/orders/{oid}/status", data={"status": "Accepted", "csrf_token": tok}), 403)

# staff
s = app.test_client(); login(s, "staff@example.com", "DemoPass1!")
for u in ["/staff", "/manage/orders", "/manage/orders?status=Pending", "/manage/food", "/manage/food/new", "/manage/food/1/edit", f"/orders/{oid}"]: ok(s.get(u))
for u in ["/admin", "/admin/users", "/admin/reports", "/admin/categories", "/cart"]: ok(s.get(u), 403)
t = token(s, "/staff")
assert "Cannot change" in s.post(f"/orders/{oid}/status", data={"status": "Delivered", "csrf_token": t}, follow_redirects=True).get_data(as_text=True)
for st in ["Accepted", "Preparing", "Ready", "Delivered"]:
    assert f"now {st}" in s.post(f"/orders/{oid}/status", data={"status": st, "csrf_token": t}, follow_redirects=True).get_data(as_text=True)
assert "Only orders that are still Pending" in c.post(f"/orders/{oid}/cancel", data={"csrf_token": tok}, follow_redirects=True).get_data(as_text=True)
assert "Delivered" in c.get(f"/orders/{oid}").get_data(as_text=True)
assert "unavailable" in s.post("/manage/food/1/toggle", data={"csrf_token": t}, follow_redirects=True).get_data(as_text=True)
assert "currently unavailable" in c.post("/cart/add/1", data={"quantity": 1, "csrf_token": tok}, follow_redirects=True).get_data(as_text=True).lower()
s.post("/manage/food/1/toggle", data={"csrf_token": t})
ok(s.post("/admin/food/1/delete", data={"csrf_token": t}), 403)
# staff edits food
r = s.post("/manage/food/new", data={"name": "Test Dish", "category_id": 1, "description": "x", "price": "99.50", "is_available": "y", "csrf_token": token(s, "/manage/food/new")}); ok(r, 302)

# customer cancels own pending order
tok = token(c, "/menu"); c.post("/cart/add/3", data={"quantity": 1, "csrf_token": tok})
r = c.post("/checkout", data={"address": "12 Main Road, Hyderabad", "phone": "9876543210", "csrf_token": token(c, "/checkout")}); oid2 = int(re.search(r"/orders/(\d+)/", r.location).group(1))
assert "cancelled" in c.post(f"/orders/{oid2}/cancel", data={"csrf_token": tok}, follow_redirects=True).get_data(as_text=True).lower()

# admin
a = app.test_client(); assert "Welcome back" in login(a, "admin@example.com", "Adm1nPass!").get_data(as_text=True)
for u in ["/admin", "/admin/reports", "/admin/reports?days=7", "/admin/users", "/admin/categories", "/admin/categories/1/edit", "/manage/orders", "/manage/food", f"/orders/{oid}", f"/orders/{oid2}"]: ok(a.get(u))
html = a.get("/admin").get_data(as_text=True); assert "Total revenue" in html and "revChart" in html
t = token(a, "/admin/categories")
assert "Category saved" in a.post("/admin/categories", data={"name": "Salads", "description": "Fresh", "csrf_token": t}, follow_redirects=True).get_data(as_text=True)
assert "already exists" in a.post("/admin/categories", data={"name": "salads", "csrf_token": t}).get_data(as_text=True)
assert "still has food items" in a.post("/admin/categories/1/delete", data={"csrf_token": t}, follow_redirects=True).get_data(as_text=True)
assert "created" in a.post("/admin/users", data={"name": "New Staff", "email": "ns@example.com", "role": "staff", "password": "StaffPass1", "csrf_token": token(a, "/admin/users")}, follow_redirects=True).get_data(as_text=True)
assert "cannot delete your own" in a.post("/admin/users/%d/delete" % 1, data={"csrf_token": t}, follow_redirects=True).get_data(as_text=True)
assert "appears in past orders" in a.post("/admin/food/3/delete", data={"csrf_token": t}, follow_redirects=True).get_data(as_text=True)
assert "Cancelled" in a.post(f"/orders/{oid2}/status", data={"status": "Cancelled", "csrf_token": t}, follow_redirects=True).get_data(as_text=True)
# logout
assert "logged out" in a.post("/logout", data={"csrf_token": t}, follow_redirects=True).get_data(as_text=True)
ok(a.get("/admin"), 302)
print("ALL TESTS PASSED")
