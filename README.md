# Fluér de Luné 🕶️

**Minimalist luxury eyewear e-commerce** — a warm-beige, mobile-first Django storefront with a single WhatsApp checkout flow.

---

## Features

- **Full storefront** — home with hero & featured collections, category browsing, product detail pages with image galleries + zoom, search, sorting, pagination
- **Cart system** — session carts for guests that **merge into your account on login**, HTMX slide-in cart drawer, live stock validation
- **Wishlist** — one-tap heart toggles, move items to cart, **persisted in database per user** (survives restarts/deploy)
- **Accounts** — email-based auth, profile management, required WhatsApp number, staff-issued password reset links
- **3-step checkout** — details → review → confirm. Only name, email and phone are collected; how the customer receives the order is agreed on WhatsApp
- **WhatsApp checkout** — after placing an order, the customer is handed off to WhatsApp with the order details pre-filled; the team confirms everything directly in chat
- **Order lifecycle** — FDL-XXXXXXXX order numbers, status timeline, reorder, guest order tracking by number + email. Stock is deducted **once**, when an order first becomes Confirmed, Processing or Delivered, and restored if it is cancelled or refunded
- **Admin dashboard** — manage products/categories/images, orders with status actions, contact messages, site settings
- **Image reliability** — **server-side image proxy** for all external (ImgBB) images: long-term browser caching, skeleton loading placeholders, error fallback, preload critical images, `decoding="async"`
- **Global loading indicator** — gold progress bar on initial load, HTMX requests, and page navigation; 3s force-hide safety
- **PWA-ready** — manifest, service worker (network-first HTML / cache-first static), offline page
- **Accessible** — skip links, ARIA labels, 48px touch targets, WCAG-AA text contrast

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django 5.x+, Python 3.13 |
| Database | SQLite (dev) → PostgreSQL (prod, Neon + PgBouncer) |
| Frontend | HTMX (partial updates) + Alpine.js (UI state), hand-crafted CSS design system (`static/css/variables.css`) |
| Fonts | Playfair Display + Inter (self-hosted WOFF2) |
| Images | django-imagekit auto-thumbnails (400/800/1200px WebP) + **ImgBB proxy** |
| Orders | WhatsApp hand-off with pre-filled order details |
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
| `SITE_URL` | Canonical URL for links and metadata |
| `WHATSAPP_NUMBER` | Business WhatsApp line, local or international format (defaults to `2348104260003`) |
| `CONTACT_PHONE` | Display phone number (defaults to `+234 810 426 0003`) |
| `IMGBB_API_KEY` | For uploading product/category images to ImgBB |

See [`dotenv_example.txt`](dotenv_example.txt) for the full list and [`instructions.md`](instructions.md) for everything you can customise without touching code.

## Testing the Order Flow

Place a test order through checkout and continue to WhatsApp. The order is recorded first, then the pre-filled message opens in WhatsApp. Stock is not reduced at that point: it is deducted once staff move the order to Confirmed, Processing or Delivered in the inventory dashboard.

## Project Structure

```
├── apps/
│   ├── core/        # Home, about, contact, legal pages, SiteSettings singleton
│   ├── products/    # Category, Product, ProductImage (+ ImageKit thumbnails), **Image Proxy view**
│   ├── cart/        # Session + user carts, HTMX drawer partials
│   ├── wishlist/    # Toggle, move-to-cart, **DB-persisted per user**
│   ├── accounts/    # CustomUser (email login), profile and password management
│   ├── orders/      # Order, OrderItem, status history, admin views
│   └── checkout/    # 3-step details → review → confirm, WhatsApp hand-off
├── config/settings/ # base / development / production
├── templates/       # One folder per app + base.html
├── static/          # css (design tokens + main.css), js, fonts, images
└── requirements/
```

> See **[instructions.md](instructions.md)** for a guide to customising content, colours, prices and more.