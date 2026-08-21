# Customising Fluér de Luné — What Changes Where

Everything below can be changed **without touching code logic** — most content lives in the Django admin or in a single config file.

---

## 1. Site name, logo, contact info, socials, SEO  ⭐ *most things*

**Where:** Django admin → **Core → Site Settings** (a single editable row).

| Field | Controls |
|---|---|
| Site Name | Browser title, header/footer/mobile-menu wordmark (first word dark, rest gold) |
| Logo image | **Uploading one replaces the text wordmark everywhere automatically** |
| Tagline, Meta Description/Keywords | Hero tagline, `<head>` SEO tags |
| Email / Phone / Address | Footer contact column, contact page |
| Instagram/Facebook/X/TikTok URLs | Footer social icons (blank = icon hidden) |
| WhatsApp Number + Message Template | Floating chat button, product "Ask About This Piece", mobile menu |

> WhatsApp number format: `2348012345678` (country code, no `+`, no spaces).
> The message template supports `{product_name}` on product pages.

---

## 2. Bank details for manual payments

**Where:** Admin → **Payments → Manual Payment Info** (keep only one active).

Controls the bank-name/account-number block shown after a manual checkout, plus its WhatsApp confirmation template with placeholders `{order_number}`, `{amount}`, `{name}`. Also previewable in checkout step 2.

---

## 3. Products & categories

Admin → **Products**.
- Categories: name (slug auto-fills), description, image, sort order, active flag
- Products: price, *compare-at price* (fills it in → automatic "-X%" sale badge), stock quantity + low-stock threshold ("Low Stock" badge), flags for Featured / New Arrival / Bestseller, images inline (first marked primary is used across cards)

---

## 4. Shipping cost & free-shipping threshold  *(code constants)*

File: **`apps/checkout/views.py`**, top of file:

```python
SHIPPING_COST = 1500              # ₦1,500 flat rate
FREE_SHIPPING_THRESHOLD = 50000   # free over ₦50,000
```

⚠️ The cart summary also displays these numbers as text — update them in **`templates/cart/partials/_summary.html`** (`₦{{ threshold… }}`, `₦50,000`, `₦1,500`) and in checkout step templates if you change either value.

---

## 5. Colours & design tokens

File: **`static/css/variables.css`** — every component reads from these variables:

- Brand palette: `--color-beige-50 … --color-beige-900`
- Accent golds: `--color-gold`, `--color-gold-light`, `--color-gold-dark`
- Status colours (success/warning/error/info), radii, shadows, fonts, breakpoints, touch-target sizes

The gold gradient on the logo accent lives separately in **`static/css/main.css`** under `.brand-accent`.

After editing CSS, hard-refresh (Ctrl+Shift+R); in production run `python manage.py collectstatic`.

---

## 6. Fonts & PWA identity

- Fonts: swap the `.woff2` files in **`static/fonts/`**, then update the `@font-face` names at the top of `main.css` and `--font-serif/--font-sans` in `variables.css`.
- App name/icons/theme colour: **`static/manifest.json`**; icons are PNGs in `static/images/`; theme-colour meta is in `templates/base.html`.

---

## 7. Homepage & static copy

- Hero headline/stats/value-props and section headings: **`templates/core/home.html`**
- Our Story content: `templates/core/about.html`
- Legal text (Privacy/Terms/Shipping/Returns): the matching `templates/core/*.html` files
- Password requirement chips: `templates/includes/_password_hints.html`

---

## 8. Environment-driven settings  (`.env`)

| Change | Variable |
|---|---|
| Active gateway | `PAYMENT_GATEWAY=paystack` \| `flutterwave` |
| Gateway keys | See README table |
| Canonical site URL | `SITE_URL=https://yourdomain.com` |
| Debug mode / hosts / secret key | `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_SECRET_KEY` |

---

## 9. Currency symbol

Declared once in **`config/settings/base.py`** (`CURRENCY_SYMBOL = '₦'`). Note: current templates hard-code `₦` inline for display speed — search templates for `₦` when changing currencies.

---

## 10. Minimum password length

Django validator default is 8 (`config/settings/base.py`). If you raise it, also update the chip text in `templates/includes/_password_hints.html` ("8+ characters").

---

## Golden rules

1. Content → **Admin**. Styling → **variables.css**. Copy → **templates**. Numbers/prices/shipping → **checkout/views.py + summary template**. Keys/secrets → **.env**.
2. Never commit your `.env`, `db.sqlite3`, or `media/` folder (already covered by `.gitignore`).
