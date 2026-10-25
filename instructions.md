# Customising Fluér de Luné — What Changes Where

Everything below can be changed **without touching code logic** — most content lives in the Django admin or in a single config file.

---

## 1. Site name, logo, contact info, socials, SEO  ⭐ *most things*

**Where:** Django admin → **Core → Site Settings** (a single editable row).

| Field | Controls |
|---|---|
| Site Name | Browser title, header/footer/mobile-menu wordmark (first word dark, rest gold) |
| Logo image | **Uploading one replaces the text wordmark everywhere automatically**; a missing or broken file safely falls back to the wordmark |
| Tagline, Meta Description/Keywords | Hero tagline, `<head>` SEO tags |
| Email / Phone / Address | Footer contact column, contact page |
| Instagram/Facebook/X/TikTok URLs | Footer social icons (blank = icon hidden) |
| WhatsApp Message Template | Floating chat button, product "Ask About This Piece", mobile menu |

> WhatsApp number format: `2348104260003` (country code, no `+`, no spaces). `WHATSAPP_NUMBER` in `.env` also accepts the local form `08104260003` and converts it automatically. The site settings singleton keeps the number consistent across every page.
> The message template supports `{product_name}` on product pages.

---

## 2. WhatsApp checkout

Checkout is a single WhatsApp flow: details → review → confirm. Only name, email and phone are collected. Placing an order records it and opens WhatsApp with the order number, customer name and total already filled in. How the customer receives the order is agreed with the team in that chat; there are no shipping options, payment routes or bank-detail screens.

To change the number, set `CONTACT_PHONE` and `WHATSAPP_NUMBER` in `.env`. The fallback default is the business line `+234 810 426 0003`.

---

## 3. Products & categories

Admin → **Products**.
- Categories: name (slug auto-fills), description, image, sort order, active flag
- Products: price, *compare-at price* (fills it in → automatic "-X%" sale badge), stock quantity + low-stock threshold ("Low Stock" badge), flags for Featured / New Arrival / Bestseller, images inline (first marked primary is used across cards)

---

## 4. Stock deduction  *(order status)*

Stock is **not** reduced when an order is placed. It is deducted **once**, the first time staff change the order status to **Confirmed**, **Processing** or **Delivered** in the inventory dashboard (or Django admin).

- The order keeps a `stock_deducted` flag, so switching the status back and forth never deducts twice.
- Cancelling or refunding an order restores stock only if it had already been deducted. A refunded order that is confirmed again takes the stock out once more.
- If a product sells out between order placement and confirmation, the team can cancel or adjust the order before stock is taken.

---

## 5. Colours & design tokens

File: **`static/css/variables.css`** — every component reads from these variables:

- Brand palette: `--color-beige-50 … --color-beige-900`
- Accent golds: `--color-gold`, `--color-gold-light`, `--color-gold-dark`
- Status colours (success/warning/error/info), radii, shadows, fonts, breakpoints, touch-target sizes

The gold gradient on the logo accent lives separately in **`static/css/main.css`** under `.brand-accent`.
**Section backgrounds**: `.section` (default beige), `.section--white` (white), `.section--gradient` (beige→white gradient, works in light/dark) — used by Best Sellers on homepage.

After editing CSS, hard-refresh (Ctrl+Shift+R); in production run `python manage.py collectstatic`.

---

## 6. Fonts & PWA identity

- Fonts: swap the `.woff2` files in **`static/fonts/`**, then update the `@font-face` names at the top of `main.css` and `--font-serif/--font-sans` in `variables.css`.
- App name/icons/theme colour: **`static/manifest.json`**; icons are PNGs in `static/images/`; theme-colour meta is in `templates/base.html`.

---

## 7. Homepage & static copy

- Hero headline/stats/value-props and section headings: **`templates/core/home.html`**
- Our Story content: `templates/core/about.html`
- Legal text (Privacy/Terms/Returns): the matching `templates/core/*.html` files
- Password requirement chips: `templates/includes/_password_hints.html`

---

## 8. Environment-driven settings  (`.env`)

| Change | Variable |
|---|---|
| Business WhatsApp number | `WHATSAPP_NUMBER=08104260003` |
| Display phone number | `CONTACT_PHONE=+234 810 426 0003` |
| Canonical site URL | `SITE_URL=https://yourdomain.com` |
| Debug mode / hosts / secret key | `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_SECRET_KEY` |
| ImgBB API key | `IMGBB_API_KEY` |

---

## 9. Currency symbol

Declared once in **`config/settings/base.py`** (`CURRENCY_SYMBOL = '₦'`). Note: current templates hard-code `₦` inline for display speed — search templates for `₦` when changing currencies.

---

## 10. Minimum password length

Django validator default is 8 (`config/settings/base.py`). If you raise it, also update the chip text in `templates/includes/_password_hints.html` ("8+ characters").

---

## 11. Image loading & proxy  *(new)*

- **All external images (ImgBB) go through `/products/image-proxy/`** — served with `Cache-Control: public, max-age=31536000, immutable` so browsers cache 1 year.
- **Template tag**: `{% image_proxy_url image.url [width] [height] %}` — only proxies ImgBB URLs; others pass through.
- **Skeleton placeholders**: pulse animation while loading → fade-in on complete. Used everywhere: product cards, category cards, detail gallery, inventory tables, form previews.
- **Error fallback**: broken/missing images show a minimalist SVG placeholder.
- **Preload critical images**: hero & primary product image get `<link rel="preload" as="image" fetchpriority="high">` in page `<head>`.
- **Non-blocking decode**: `decoding="async"` on all `<img>` tags.
- **Medium quality on cards**: product grid uses `medium_url` (320px) instead of tiny `thumbnail_url` (150px) — sharp at 400px display.

---

## 12. Global loading bar

- **`#fdl-loading`** in `templates/base.html` — shows immediately on page start, hides on `window.load`.
- Also shows during HTMX requests and full-page navigation (`beforeunload`).
- **3-second force-hide** safety timeout in `static/js/main.js` if load event misfires.
- Gold progress bar with indeterminate animation.

---

## 13. Mobile theme toggle

- **Sun/moon icon button** at bottom-left of both mobile nav drawers (main site + inventory).
- Click toggles `data-theme` on `<html>`, persists to `localStorage`, updates browser theme-color meta.
- Logic lives in `static/js/main.js` → `toggleTheme()` (single line in `@click` avoids Alpine parsing issues).
- Icon swap via CSS `[data-theme="light"]` / `[data-theme="dark"]` selectors.

---

## 14. Best Sellers gradient section

- Homepage Best Sellers uses `.section--gradient` (beige→white in light, dark beige→darker in dark).
- Defined in `static/css/main.css` with dark-mode override.
- Sits between Featured (default beige) and New Arrivals (white) for visual rhythm.

---

## 15. Password reset (staff-issued link)

Self-service reset needs an email or SMS provider, and none is configured, so the customer form points people to WhatsApp instead. Staff issue the link from inventory:

- **`/inventory/password-reset-link/`** — linked from the Dashboard and Orders headers (`apps/inventory/views.py`, `templates/inventory/password_reset_link.html`).
- Enter the customer's account email → the page builds a signed, single-use link with Django's `default_token_generator` and offers **Copy link** / **Send on WhatsApp** (pre-filled message, normalised to `wa.me` format).
- The link expires after `PASSWORD_RESET_TIMEOUT` (10 minutes in `config/settings/base.py` and `production.py`).
- The customer opens the link on the storefront and sets a new password; the token stops working once used or once the password changes.
- The public `/accounts/password/reset/` page remains a "message us on WhatsApp" explainer, not a self-service form. The login page's "Forgot your password?" link goes straight there.
- **Temporary test option:** with `PASSWORD_RESET_TEST_MODE=True` (set in the local `.env`), the reset page also shows **Without our team**, which opens the signed reset link immediately instead of delivering it. It is off by default in production. Delete the block marked `TEMPORARY TEST MODE` in `templates/accounts/password_reset_under_development.html` to remove it, and unset `PASSWORD_RESET_TEST_MODE` to close the endpoint.
- Registration and profile editing require a phone number (10–15 digits); it is stored as the WhatsApp number used for reset delivery. Existing accounts without one still appear in the tool, where staff can copy the link manually.

---

## Golden rules

1. Content → **Admin**. Styling → **variables.css**. Copy → **templates**. Numbers/prices → **settings + summary templates**. Keys/secrets → **.env**.
2. Never commit your `.env`, `db.sqlite3`, or `media/` folder (already covered by `.gitignore`).