# AIRE Terminal (Ultimate)

**Exchange-style UI + third‑grader simple workflow.**

What you can do:
- **Grade a Deal:** paste link/address → A–F grade + BUY/PASS
- **Batch Screener:** rank deals like an exchange table (“orderbook” vibe)
- **Alerts:** watchlist + scan for hits (optional email via SendGrid)
- **Templates:** strategy presets + custom strategies
- **Reports:** saved history + export

## Streamlit Cloud Deploy
- Main file path: `app.py`

### Secrets
```toml
RENTCAST_APIKEY = "YOUR_KEY"
ESTATED_TOKEN = ""
ATTOM_APIKEY = ""
OPENAI_API_KEY = ""

# Optional email alerts (SendGrid)
SENDGRID_API_KEY = ""
ALERT_EMAIL_TO = "you@example.com"
```


## Enterprise Options
- Optional access gate:
```toml
APP_ACCESS_KEY = "set_a_password_here"
```
- Performance:
```toml
API_TIMEOUT_SEC = 15
CACHE_TTL_SEC = 3600
```

## 10M Product Upgrades (Included)
- Accounts + login/signup (SQLite, hashed passwords)
- Team workspaces (create + invite code join)
- Usage limits by plan (free/pro/team)
- Stripe subscription wiring (Checkout + demo fallback)
- API keys + FastAPI API (`api_server.py`) with rate limits

## Deploy
### Streamlit UI
- Main file: `app.py`
- Add secrets in Streamlit Cloud (see below)

### API Backend (FastAPI)
- Run locally:
```bash
pip install -r requirements.txt
uvicorn api_server:app --reload --port 8000
```
- Deploy the API using Render/Fly/Railway (use `Dockerfile.api`).

## Streamlit Secrets (example)
```toml
RENTCAST_APIKEY = "YOUR_KEY"
OPENAI_API_KEY = ""

# Access gate (optional)
APP_ACCESS_KEY = ""

# Stripe
STRIPE_SECRET_KEY = ""
STRIPE_PRICE_ID_PRO = ""
STRIPE_PRICE_ID_TEAM = ""
STRIPE_SUCCESS_URL = "https://your-app.streamlit.app/?billing=success"
STRIPE_CANCEL_URL = "https://your-app.streamlit.app/?billing=cancel"

# Performance
API_TIMEOUT_SEC = 15
CACHE_TTL_SEC = 3600
```


## Ads Same-Day
- Send traffic to: `/?landing=1`
- Landing page explains value + pricing + calls to action.
- Sidebar allows instant signup/login.

## Marketing site (real company feel)
A complete static website is in `/marketing_site`.

### Deploy in 5 minutes (recommended)
- GitHub Pages: Settings → Pages → Deploy from branch → `/marketing_site`
- or Netlify: drag-and-drop the `marketing_site` folder

### Important
Replace `https://YOUR-STREAMLIT-APP.streamlit.app` with your actual Streamlit URL in the HTML files.

## Stripe webhook (live enforcement)
To enforce subscriptions by Stripe status, deploy the API service (`api_server.py`) and add a Stripe webhook endpoint:

- Endpoint: `POST https://YOUR-API-DOMAIN/stripe/webhook`
- Events to subscribe:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

### Required env vars on the API host
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_PRO`
- `STRIPE_PRICE_ID_TEAM`

### Streamlit secrets (UI)
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID_PRO`
- `STRIPE_PRICE_ID_TEAM`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- Optional: `DEV_BYPASS_KEY` and/or `DEV_ADMIN_EMAILS`

## Stripe Customer Portal
Billing includes a Stripe Customer Portal button so users can cancel/upgrade themselves.

### Streamlit secrets (UI)
- `STRIPE_PORTAL_RETURN_URL` (required)
- Optional: `STRIPE_PORTAL_CONFIGURATION_ID`

## "Real Company" Upgrades Included
This build adds:
- **RBAC (roles):** owner/admin/member/viewer with Workspace Settings UI
- **Team management:** list members, change roles, remove members, generate invite codes with role
- **Stripe Customer Portal:** self-serve cancel/upgrade/payment method updates
- **Hard lock screen:** paid-but-inactive workspaces are locked until reactivated (Billing still accessible)
- **Tax & address collection:** Stripe Checkout now requires billing address and enables tax ID collection
- **Production DB option:** supports `DATABASE_URL` for Postgres (requires psycopg2-binary). Defaults to SQLite.

### Postgres setup
Set an environment variable on Streamlit (or your host):
- `DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME`

SQLite remains the default. For SQLite you can optionally set:
- `SQLITE_PATH=/path/to/aire.db`

### New secrets
Add these to Streamlit secrets:
- `STRIPE_PORTAL_RETURN_URL`
- Optional: `STRIPE_PORTAL_CONFIGURATION_ID`

Developer demo:
- `DEV_BYPASS_KEY`
- `DEV_ADMIN_EMAILS`

## Outcomes (Institution-grade learning)
This build adds a first-class **Outcomes** system so the model can learn from **real returns**, not opinions.

### What users can do
- Add outcomes with a simple form (address + purchase price + actual rent + vacancy + repairs + hold + resale)
- Import outcomes via CSV (bulk upload from property management/accounting exports)
- Compute derived metrics automatically (appreciation %, realized IRR)

### How learning works (enterprise-safe)
- Outcomes are turned into training labels (good/bad) using an IRR threshold + vacancy threshold
- Governance page trains a **candidate** model from outcomes and you manually **activate** it
- The production model never silently changes

### CSV format (required columns)
- address
- purchase_price
- actual_monthly_rent
- vacancy_days
- repair_costs
- hold_months
- resale_price

Optional: url, notes, report_id (highly recommended)

## Audit Logging + Admin Override
This build adds bank-style governance:

- Forced audit logging for promotions: who, when, why, from→to model, metrics snapshot
- Admin-only override with required reason (and the blocked guardrail reason is also recorded)
- Separate **Audit** page for viewing events
