# Fluér de Luné 🕶️

**Minimalist luxury eyewear e-commerce** — a warm-beige, mobile-first Django storefront with dual payment options (Paystack/Flutterwave hosted checkout **and** manual bank-transfer via WhatsApp).

---

## Features

- **Full storefront** — home with hero & featured collections, category browsing, product detail pages with image galleries + zoom, search, sorting, pagination
- **Cart system** — session carts for guests that **merge into your account on login**, HTMX slide-in cart drawer, live stock validation
- **Wishlist** — one-tap heart toggles, move items to cart
- **Accounts** — email-based auth, address book with defaults, profile management, password reset
- **3-step checkout** — shipping → payment method → confirm, with free shipping over ₦50,000
- **Dual payments**
  - *Gateway*: Paystack or Flutterwave hosted payment links (card / transfer / USSD / QR) — no card data ever touches the server; webhook + callback verification
  - *Manual*: bank details page + pre-filled WhatsApp confirmation message
- **Order lifecycle** — FDL-XXXXXXXX order numbers, status timeline, cancel-with-stock-restoration, reorder, guest order tracking by number + email
- **Admin dashboard** — manage products/categories/images, orders with status actions, manual-payment bank details, contact messages, site settings
- **PWA-ready** — manifest, service worker (network-first HTML / cache-first static), offline page
- **Accessible** — skip links, ARIA labels, 48px touch targets, WCAG-AA text contrast

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django 5.x+, Python 3.13 |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Frontend | HTMX (partial updates) + Alpine.js (UI state), hand-crafted CSS design system (`static/css/variables.css`) |
| Fonts | Playfair Display + Inter (self-hosted WOFF2) |
| Images | django-imagekit auto-thumbnails (400/800/1200px WebP) |
| Payments | Paystack & Flutterwave REST APIs |
| Static serving | WhiteNoise |

## Quick Start

```bash
# 1. Clone & enter
git clone <your-repo-url>
cd e-commerce_for_idara

# 2. Virtual environment (Python 3.13)
python -m venv .venv
.\.venv\Scripts\activate          # Windows
source .venv/bin/activate         # macOS/Linux

# 3. Dependencies
pip install -r requirements/base.txt
pip install -r requirements/development.txt   # optional dev tools

# 4. Environment
copy dotenv_example.txt .env      # then fill in values (see below)

# 5. Database + admin user
python manage.py migrate
python manage.py createsuperuser

# 6. Run
python manage.py runserver
```

Visit `http://127.0.0.1:8000` · Admin at `/admin`.

### Environment variables (`.env`)

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Set a strong random key in production |
| `DJANGO_DEBUG` | `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated domains |
| `SITE_URL` | Canonical URL (used in gateway metadata) |
| `PAYMENT_GATEWAY` | `paystack` or `flutterwave` |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | From dashboard.paystack.com (`sk_test_…` for testing) |
| `FLUTTERWAVE_SECRET_KEY` / `…PUBLIC_KEY` / `…ENCRYPTION_KEY` | From app.flutterwave.com |

See [`dotenv_example.txt`](dotenv_example.txt) for the full list and [`instructions.md`](instructions.md) for everything you can customise without touching code.

## Testing Payments

- **Without keys:** choose *"Bank Transfer / WhatsApp"* at checkout — complete end-to-end flow.
- **With test keys:** choose *"Pay Now"*. Paystack test card: `4084 0840 8408 4081`, any future expiry, CVV `408`, OTP `123456`. The order flips to **Paid/Confirmed** automatically after verification.

## Project Structure

```
├── apps/
│   ├── core/        # Home, about, contact, legal pages, SiteSettings singleton
│   ├── products/    # Category, Product, ProductImage (+ ImageKit thumbnails)
│   ├── cart/        # Session + user carts, HTMX drawer partials
│   ├── wishlist/    # Toggle, move-to-cart
│   ├── accounts/    # CustomUser (email login), Address book
│   ├── orders/      # Order, OrderItem, status history, admin views
│   ├── payments/    # Gateway services, webhooks, ManualPaymentInfo
│   └── checkout/    # 3-step flow, shipping calc, stock reservation
├── config/settings/ # base / development / production
├── templates/       # One folder per app + base.html
├── static/          # css (design tokens + main.css), js, fonts, images
└── requirements/
```

> See **[instructions.md](instructions.md)** for a guide to customising content, colours, prices, shipping rules and more.
