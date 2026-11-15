# Spice Route Kitchen – Online Food Ordering & Restaurant Management System

A Flask web application where customers order food, restaurant staff process orders, and administrators manage the menu, users and reports.
Runs locally with **SQLite** and deploys to **AWS (EC2 + RDS MySQL)** with the same code.

## Objectives
- Let customers browse, search, order (Cash on Delivery) and track food orders.
- Give staff a kitchen dashboard to accept, reject and progress orders.
- Give admins full control of users, categories, food items, orders and reports.
- Demonstrate secure, cloud-ready development (RBAC, CSRF, hashed passwords, env-based secrets).

## Features
| Role | Capabilities |
|---|---|
| Customer | Register/login, browse, search, filter by category, food details, cart (add/update/remove), COD checkout, order history, live order tracking, cancel pending orders. Can only see own orders. |
| Staff | Kitchen dashboard, accept/reject orders, update status (Accepted → Preparing → Ready → Delivered), add/edit food, toggle availability. |
| Admin | Dashboard with revenue/order charts, manage users (staff/admin), categories, food items, all orders, reports (7/30/90 days). |

Order flow: `Pending → Accepted → Preparing → Ready → Delivered`, plus `Rejected` (staff) and `Cancelled` (customer while Pending, or admin). Invalid transitions are refused on the server.

## Technology stack
Python, Flask, Flask-SQLAlchemy, Flask-WTF (CSRF), Jinja2, Bootstrap 5, Chart.js, SQLite (local) / MySQL on Amazon RDS (AWS), Gunicorn, Nginx, systemd.

## Folder structure
```
Food-Ordering-System/
├── app.py              routes, forms, CLI commands (init-db, seed, create-admin, demo-data)
├── config.py           settings from environment variables (.env)
├── models.py           SQLAlchemy models
├── seed_data.py        sample categories and food items
├── requirements.txt  .env.example  .gitignore
├── tests_smoke.py      automated end-to-end test of all roles
├── tools/generate_images.py   regenerates the dish illustrations
├── templates/          Jinja2 pages (dashboard_base.html = admin/staff layout)
├── static/css/style.css  static/js/script.js
├── static/images/foods/   dish images (also where uploaded photos go)
└── instance/           local SQLite database (not committed)
```

## Database design
- **users** (id, name, email*, password_hash, role, created_at)
- **categories** (id, name*, description)
- **menu_items** (id, category_id → categories, name, description, price ≥ 0, image, is_available, created_at)
- **orders** (id, user_id → users, total_amount, status, payment_method, delivery_address, phone, created_at)
- **order_items** (id, order_id → orders, menu_item_id → menu_items, quantity > 0, price)

`order_items.price` stores the price at the time of ordering. Prices are always recalculated on the server.

## Local installation (Windows PowerShell + VS Code)
```powershell
cd Food-Ordering-System
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then edit .env and set SECRET_KEY
flask --app app init-db
flask --app app seed
flask --app app create-admin    # prompts for name, email, hidden password
flask --app app demo-data       # optional: demo staff/customers + sample orders
flask --app app run
```
Open http://127.0.0.1:5000. Generate a secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`.
If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Run the automated test any time: `python tests_smoke.py`.

## AWS architecture
```
Customer Browser → Internet Gateway → EC2 Ubuntu (public subnet: Nginx → Gunicorn → Flask)
                                              ↓ port 3306 (security-group to security-group)
                                     Amazon RDS MySQL (private subnets, 2 AZs)
```
VPC 10.0.0.0/16 · Web subnet 10.0.1.0/24 (ap-south-1a) · DB subnets 10.0.2.0/24 (1a) and 10.0.3.0/24 (1b).
The AWS setup guide, deployment commands, Gunicorn/Nginx files and troubleshooting are delivered as the next step, after local testing.
The same code switches to RDS automatically when `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` are set in `.env`.

## Security
Werkzeug password hashing · session auth with cookie hardening · CSRF on every POST · server-side role checks on every route · order ownership checks · ORM queries only · secrets only in `.env` · image upload type/size limits.

## Screenshots
Add your screenshots here (home, menu, cart, order tracking, staff dashboard, admin dashboard, reports).

## Future enhancements
S3 image storage (`store_image()` in `app.py` is the single place to change) · Secrets Manager · HTTPS with a domain · GitHub Actions CI/CD · Docker · CloudWatch · RDS backups.
