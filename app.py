import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List

from config import load_config, validate_config
from logger import log_event
from provenance import pick, pack_provenance
from auth import authenticate, create_user, list_workspaces, create_workspace, create_invite, accept_invite, get_role, list_members, set_member_role, remove_member
from billing import get_subscription, plan_limits, set_plan, effective_plan
from usage import count_last_24h, record
from api_keys import create_key, list_keys, revoke_key
import stripe
from landing import render_landing
from onboarding import needs_onboarding, run_onboarding
from export_pdf import build_report_pdf
from lock_screen import render_lock
from feedback import add_feedback, list_feedback
from model_registry import list_models, create_candidate_model, activate_model, get_active_model
import learning
import audit

def count_linked_outcomes(workspace_id: int) -> int:
    """Counts outcomes with a valid report_id (linked), for guardrails."""
    try:
        from db import fetchone
        row = fetchone("SELECT COUNT(1) FROM outcomes WHERE workspace_id=? AND report_id IS NOT NULL AND report_id != 0", (int(workspace_id),))
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass
    return 0

def get_val_f1(model: dict) -> float:
    """Extract validation F1 from model metrics."""
    try:
        m = model.get("metrics") or {}
        if isinstance(m, dict) and "val" in m and isinstance(m["val"], dict):
            return float(m["val"].get("f1", 0.0) or 0.0)
        # backward compatibility: if metrics had flat f1
        return float(m.get("f1", 0.0) or 0.0)
    except Exception:
        return 0.0
from outcomes import upsert_outcome, list_outcomes, read_outcome, find_best_report_match, list_unlinked_outcomes, link_outcome_to_report


def app_header(title: str, subtitle: str = ""):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<div class='kicker'>{subtitle}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
import json
import matplotlib.pyplot as plt


def breadcrumb(step: int):
    """Renders a simple 2-step breadcrumb/progress indicator."""
    s1 = "on" if int(step) == 1 else ""
    s2 = "on" if int(step) == 2 else ""
    st.markdown(
        f"""
        <div class="bcrumb">
          <div class="bstep {s1}"><span class="bdot"></span> Step 1 <span style="opacity:.65;font-weight:800;">Paste</span></div>
          <div class="barrow">→</div>
          <div class="bstep {s2}"><span class="bdot"></span> Step 2 <span style="opacity:.65;font-weight:800;">Report</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
from link_resolver import guess_address_from_url, looks_like_url
from underwriting import DealInputs, run_underwriting
from ai_memo import generate_investment_memo
from storage import (
    save_report, list_reports, read_report,
    upsert_template, list_templates, delete_template,
    add_watchlist, list_watchlist, delete_watchlist,
    save_alert_run, list_alert_runs, read_alert_run
)
from templates import BUILTIN_TEMPLATES, normalize_template
from styles import EXCHANGE_UI_CSS

stripe.api_key = cfg.stripe_secret_key or st.secrets.get("STRIPE_SECRET_KEY", "")

st.set_page_config(page_title="AIRE Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown(r"""
<style>
:root{
  --bg: #f4f7fb;
  --panel: #ffffff;
  --panel2: #f7f9fc;
  --card: #ffffff;
  --border: rgba(23,34,59,.12);
  --text: #1a2438;
  --muted: #667089;
  --brand: #3f7ddb;
  --brand2: #6aa9ff;
  --shadow: 0 20px 50px rgba(32,56,93,.12);
  --radius: 18px;
  --font: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial;
}
html, body, [class*="css"] { font-family: var(--font) !important; }
.stApp{
  background: radial-gradient(1200px 800px at 8% 10%, rgba(95,135,210,.10), transparent 60%),
              radial-gradient(1000px 700px at 92% 20%, rgba(125,169,237,.12), transparent 55%),
              var(--bg);
  color: var(--text);
}
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(245,248,252,.98));
  border-right: 1px solid rgba(23,34,59,.08);
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] .stMarkdown p { color: var(--muted) !important; }

.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.2rem;
  max-width: 1200px;
}

h1, h2, h3{ letter-spacing: -0.02em; }
h1{ font-size: 2.0rem; }
h2{ font-size: 1.35rem; }
h3{ font-size: 1.12rem; color: var(--text); }

.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 18px 16px 18px;
  box-shadow: var(--shadow);
  margin: 10px 0 14px 0;
}
.card-soft{
  background: var(--panel2);
  border: 1px solid rgba(23,34,59,.08);
  border-radius: var(--radius);
  padding: 16px;
}

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div{
  background: #ffffff !important;
  border: 1px solid rgba(23,34,59,.14) !important;
  border-radius: 14px !important;
  box-shadow: inset 0 1px 2px rgba(16,24,40,.04);
}
input, textarea { color: var(--text) !important; }
label { color: var(--muted) !important; font-weight: 700 !important; }

.stButton button{
  border-radius: 999px !important;
  border: 1px solid rgba(63,125,219,.2) !important;
  background: linear-gradient(90deg, #3f7ddb, #6aa9ff) !important;
  color: #ffffff !important;
  font-weight: 800 !important;
  padding: 0.68rem 1.2rem !important;
  box-shadow: 0 12px 32px rgba(63,125,219,.28);
}
.stButton button:hover{
  transform: translateY(-1px);
  filter: brightness(1.03);
}

[data-testid="stMetric"]{
  background: #ffffff;
  border: 1px solid rgba(23,34,59,.08);
  border-radius: 16px;
  padding: 12px 14px;
  box-shadow: 0 10px 20px rgba(32,56,93,.08);
}

.stTabs [data-baseweb="tab-list"]{
  gap: 8px;
  background: #ffffff;
  border: 1px solid rgba(23,34,59,.08);
  padding: 8px;
  border-radius: 16px;
  box-shadow: inset 0 1px 2px rgba(16,24,40,.04);
}
.stTabs [data-baseweb="tab"]{
  border-radius: 12px !important;
  padding: 10px 12px !important;
  color: var(--muted) !important;
}
.stTabs [aria-selected="true"]{
  background: rgba(63,125,219,.12) !important;
  color: var(--text) !important;
  border: 1px solid rgba(63,125,219,.24) !important;
}

div[data-testid="stDataFrame"], .stDataFrame{
  border: 1px solid rgba(23,34,59,.08);
  border-radius: 16px;
  overflow: hidden;
  background: #ffffff;
}
.stAlert{
  border-radius: 14px !important;
  border: 1px solid rgba(23,34,59,.10) !important;
  background: #ffffff !important;
  box-shadow: 0 10px 24px rgba(32,56,93,.08);
}
.kicker{ color: var(--muted); font-size: 0.92rem; }
.badge{
  display:inline-block; padding:4px 10px; border-radius:999px;
  border:1px solid rgba(23,34,59,.12);
  background: rgba(63,125,219,.08);
  color: var(--muted);
  font-size: 0.82rem;
}
/* Breadcrumb / progress */
.bcrumb{
  display:flex; align-items:center; gap:10px;
  padding:10px 12px; border-radius: 14px;
  border:1px solid rgba(23,34,59,.10);
  background: #ffffff;
  margin: 6px 0 10px 0;
}
.bstep{
  display:flex; align-items:center; gap:8px;
  padding:6px 10px; border-radius: 999px;
  border:1px solid rgba(23,34,59,.12);
  background: rgba(63,125,219,.08);
  color: var(--muted);
  font-weight: 800; font-size: 0.86rem;
}
.bstep.on{
  background: rgba(63,125,219,.18);
  border-color: rgba(63,125,219,.24);
  color: var(--text);
}
.bdot{
  width:10px; height:10px; border-radius: 999px;
  background: rgba(26,36,56,.18);
}
.bstep.on .bdot{
  background: linear-gradient(90deg, #3f7ddb, #6aa9ff);
}
.barrow{ color: rgba(26,36,56,.45); font-weight: 900; }
</style>
""", unsafe_allow_html=True)
st.markdown(EXCHANGE_UI_CSS, unsafe_allow_html=True)

# Secrets / Config
cfg = load_config()
issues = validate_config(cfg)
RENTCAST_APIKEY = cfg.rentcast_apikey
ESTATED_TOKEN = cfg.estated_token
ATTOM_APIKEY = cfg.attom_apikey
OPENAI_API_KEY = cfg.openai_api_key
SENDGRID_API_KEY = cfg.sendgrid_api_key
ALERT_EMAIL_TO = cfg.alert_email_to

import rentcast as rc
import estated as es
import attom as at
import requests

connected_count = sum(bool(x) for x in [RENTCAST_APIKEY, ESTATED_TOKEN, ATTOM_APIKEY, OPENAI_API_KEY])
status_class = "dotlive" if connected_count >= 2 else ("dotwarn" if connected_count == 1 else "dotbad")

st.markdown(f"""
<div class="navbar">
  <div class="brand"><span class="dot"></span> AIRE <span style="opacity:.65;font-weight:900;">Terminal</span></div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="badge"><span class="{status_class}"></span> Connected: {connected_count}/4</span>
    <span class="pillbtn">Book a demo</span>
    <span class="pillbtn">v1.1</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Public landing (perfect for running ads same day)
qs = st.query_params
if qs.get("landing", "0") == "1":
    render_landing()
    st.stop()
# Optional access gate (for private demos / B2B)
# --- Accounts (simple auth) ---
if "user" not in st.session_state:
    st.session_state.user = None
if "active_workspace_id" not in st.session_state:
    st.session_state.active_workspace_id = 0
if "dev_mode" not in st.session_state:
    st.session_state.dev_mode = False

def _require_login():
    if not st.session_state.user:
        st.warning("Please log in to use AIRE Terminal.")
        st.stop()

def _login_ui():
    st.sidebar.markdown("### 👤 Account")
    tab1, tab2 = st.sidebar.tabs(["Log in", "Sign up"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Log in", use_container_width=True):
            u = authenticate(email, pw)
            if not u:
                st.error("Invalid login.")
            else:
                st.session_state.user = u
                st.success("Logged in.")
                st.rerun()
    with tab2:
        email2 = st.text_input("Email", key="su_email")
        pw2 = st.text_input("Password", type="password", key="su_pw")
        if st.button("Create account", type="primary", use_container_width=True):
            try:
                uid = create_user(email2, pw2)
                st.success("Account created. Log in now.")
            except Exception:
                st.error("Couldn’t create account (email may already exist).")

if not st.session_state.user:
    _login_ui()
    st.stop()

# Workspace switcher
wss = list_workspaces(int(st.session_state.user["id"]))
if not wss:
    st.error("No workspace found for this user.")
    st.stop()
if st.session_state.active_workspace_id == 0:
    st.session_state.active_workspace_id = int(wss[0]["id"])

ws_names = [f'{w["name"]} ({w["role"]})' for w in wss]
ws_ids = [int(w["id"]) for w in wss]
cur_idx = ws_ids.index(int(st.session_state.active_workspace_id)) if int(st.session_state.active_workspace_id) in ws_ids else 0
chosen_ws = st.sidebar.selectbox("Workspace", ws_names, index=cur_idx)
st.session_state.active_workspace_id = int(ws_ids[ws_names.index(chosen_ws)])

st.sidebar.markdown('---')
st.sidebar.markdown('### 📣 Support')
st.sidebar.write('• Docs: **/marketing_site/**')
st.sidebar.write('• Email: support@YOURDOMAIN.com')
st.sidebar.write('• Status: status@YOURDOMAIN.com')

st.sidebar.markdown("### 🛠️ Developer mode")
admin_emails = [e.strip().lower() for e in (cfg.dev_admin_emails or "").split(",") if e.strip()]
if admin_emails and (st.session_state.user.get("email","").lower() in admin_emails):
    st.session_state.dev_mode = True
if cfg.dev_bypass_key:
    dk = st.sidebar.text_input("Demo bypass key", type="password", help="Optional. Enables full access for investor demos.")
    if dk and dk == cfg.dev_bypass_key:
        st.session_state.dev_mode = True
st.sidebar.caption("Dev mode bypasses subscription enforcement (your session only).")


# Plan + usage guardrails
sub = get_subscription(st.session_state.active_workspace_id)
# Hard lock when subscription inactive (unless dev mode)
stored_plan = (sub.get("plan","free") or "free").lower()
stored_status = (sub.get("status","active") or "active").lower()
inactive_paid = (stored_plan != "free") and (stored_status not in ("active","trialing"))

if (not st.session_state.dev_mode) and inactive_paid:
    # Only allow Billing so user can re-activate; everything else is locked
    if page_key != "Billing":
        render_lock(f"Plan is inactive by Stripe (status: {stored_status}).")
        st.stop()

# Subscription enforcement banner
if (not st.session_state.dev_mode) and (effective_plan(sub) == "free") and ((sub.get("plan","free") != "free") or (sub.get("status","active") not in ("active","trialing"))):
    st.warning("Your subscription is not active. Some features may be limited. Go to Billing to re-activate.")

enforced_plan = sub.get("plan","free")
limits = plan_limits(enforced_plan)
if not st.session_state.dev_mode:
    enforced_plan = effective_plan(sub)
    limits = plan_limits(enforced_plan)

st.sidebar.caption(f'Plan: **{enforced_plan.upper()}** • Grades/day: {limits["grades_per_day"]} • Batch rows: {limits["batch_rows"]}')
if needs_onboarding():
    run_onboarding(st.session_state.active_workspace_id, int(st.session_state.user['id']))
    st.stop()
if cfg.access_key:
    with st.sidebar:
        st.markdown("### 🔐 Access")
        key = st.text_input("Enter access key", type="password")
        if key != cfg.access_key:
            st.info("This app is private. Enter the access key to continue.")
            st.stop()
def infer_last_sale(payload: dict):
    if not payload or not isinstance(payload, dict):
        return None, None
    price = None
    for k in ["lastSalePrice","last_sale_price","salePrice","last_sale_amount"]:
        v = payload.get(k)
        if isinstance(v, (int,float)) and v > 0:
            price = float(v); break
    date = payload.get("lastSaleDate") or payload.get("last_sale_date") or payload.get("saleDate") or payload.get("lastSaleRecordingDate")
    return price, date

@st.cache_data(ttl=cfg.cache_ttl_sec, show_spinner=False)
def pull_property_data(address: str) -> Dict[str, Any]:
    notes: List[str] = []
    out: Dict[str, Any] = {}
    if RENTCAST_APIKEY:
        v = rc.value_avm(RENTCAST_APIKEY, address)
        r = rc.rent_avm(RENTCAST_APIKEY, address)
        pr = rc.property_record(RENTCAST_APIKEY, address)
        if isinstance(v, dict):
            out["price"] = v.get("price") or v.get("value") or v.get("estimatedValue")
            out["price_source"] = "RentCast"
            notes.append("RentCast value AVM")
        if isinstance(r, dict):
            out["monthly_rent"] = r.get("rent") or r.get("estimatedRent")
            out["rent_source"] = "RentCast"
            notes.append("RentCast rent AVM")
        if isinstance(pr, dict):
            lsp, lsd = infer_last_sale(pr)
            out["last_sale_price"], out["last_sale_date"] = lsp, lsd
            if (lsp or lsd):
                out["last_sale_source"] = "RentCast"
            notes.append("RentCast property record")
    if ESTATED_TOKEN:
        j = es.property_lookup(ESTATED_TOKEN, address)
        if isinstance(j, dict):
            cand = j.get("data") or j.get("property") or j
            if isinstance(cand, dict):
                out["price"] = out.get("price") or cand.get("market_value") or cand.get("avm") or cand.get("value")
                if out.get("price") and not out.get("price_source"):
                    out["price_source"] = "Estated"
                lsp, lsd = infer_last_sale(cand)
                out["last_sale_price"] = out.get("last_sale_price") or lsp
                if lsp and not out.get("last_sale_source"):
                    out["last_sale_source"] = "ATTOM"
                if lsp and not out.get("last_sale_source"):
                    out["last_sale_source"] = "Estated"
                out["last_sale_date"] = out.get("last_sale_date") or lsd
                if lsd and not out.get("last_sale_source"):
                    out["last_sale_source"] = "ATTOM"
                if lsd and not out.get("last_sale_source"):
                    out["last_sale_source"] = "Estated"
            notes.append("Estated lookup")
    if ATTOM_APIKEY:
        j = at.property_detail(ATTOM_APIKEY, address)
        if isinstance(j, dict):
            cand = j.get("property") or j.get("data") or j
            if isinstance(cand, dict):
                lsp, lsd = infer_last_sale(cand)
                out["last_sale_price"] = out.get("last_sale_price") or lsp
                if lsp and not out.get("last_sale_source"):
                    out["last_sale_source"] = "Estated"
                out["last_sale_date"] = out.get("last_sale_date") or lsd
                if lsd and not out.get("last_sale_source"):
                    out["last_sale_source"] = "Estated"
            notes.append("ATTOM detail")
    out["notes"] = notes
    return out

def templates_all():
    built = [{"id": f"builtin::{k}", "name": k, "template": normalize_template(v), "builtin": True} for k,v in BUILTIN_TEMPLATES.items()]
    user = [{"id": f"user::{t['id']}", "name": t["name"], "template": normalize_template(t["template"]), "builtin": False} for t in list_templates(st.session_state.active_workspace_id)]
    return built + user

def apply_template(t: Dict[str, Any], price: float, rent: float, exp: float):
    defaults = (t.get("defaults") or {})
    exp_pct = float(defaults.get("monthly_expenses_pct_of_rent", 0.45))
    exp_est = exp if exp and exp > 0 else (rent * exp_pct if rent and rent > 0 else 0.0)
    return {
        "vacancy_rate": float(t.get("vacancy_rate", 0.08)),
        "down_payment_pct": float(t.get("down_payment_pct", 20.0)),
        "interest_rate_pct": float(t.get("interest_rate_pct", 7.25)),
        "term_years": int(t.get("term_years", 30)),
        "hold_years": int(t.get("hold_years", 7)),
        "rent_growth": float(t.get("rent_growth", 0.03)),
        "expense_growth": float(t.get("expense_growth", 0.03)),
        "appreciation": float(t.get("appreciation", 0.03)),
        "sale_cost_pct": float(t.get("sale_cost_pct", 0.07)),
        "use_exit_cap": bool(t.get("use_exit_cap", False)),
        "exit_cap_rate": float(t.get("exit_cap_rate", 0.065)),
        "price": price if price and price > 0 else None,
        "monthly_rent": rent if rent and rent > 0 else None,
        "monthly_expenses": exp_est if exp_est and exp_est > 0 else None,
    }

def run_one(raw: str, template: Dict[str, Any], manual: Dict[str, Any], use_auto: bool, use_ai: bool):
    log_event("grade_start", raw=raw, use_auto=use_auto, use_ai=use_ai)
    raw = (raw or "").strip()
    if not raw:
        return None

    if looks_like_url(raw):
        resolved = guess_address_from_url(raw)
        addr = resolved.address_guess or manual.get("address_override")
        if not addr:
            return {"error": "I couldn’t read that link. Paste the address as one line instead.", "raw": raw}
        url = raw
    else:
        addr, url = raw, ""

    pulled = pull_property_data(addr) if use_auto else {}
    price = float(manual.get("price", 0.0) or 0.0)
    rent  = float(manual.get("rent", 0.0) or 0.0)
    exp   = float(manual.get("exp", 0.0) or 0.0)

    final_price = price if price > 0 else pulled.get("price")
    final_rent  = rent if rent > 0 else pulled.get("monthly_rent")
    final_exp   = exp  if exp  > 0 else pulled.get("monthly_expenses")

    merged = apply_template(template, float(final_price or 0.0), float(final_rent or 0.0), float(final_exp or 0.0))

    i = DealInputs(
        address=addr,
        listing_url=url,
        price=float(merged["price"]) if merged["price"] else None,
        monthly_rent=float(merged["monthly_rent"]) if merged["monthly_rent"] else None,
        monthly_expenses=float(merged["monthly_expenses"]) if merged["monthly_expenses"] else None,
        vacancy_rate=float(merged["vacancy_rate"]),
        down_payment_pct=float(merged["down_payment_pct"]),
        interest_rate_pct=float(merged["interest_rate_pct"]),
        term_years=int(merged["term_years"]),
        last_sale_price=(float(pulled.get("last_sale_price")) if pulled.get("last_sale_price") else None),
        last_sale_date=(str(pulled.get("last_sale_date")) if pulled.get("last_sale_date") else None),
        hold_years=int(merged["hold_years"]),
        rent_growth=float(merged["rent_growth"]),
        expense_growth=float(merged["expense_growth"]),
        appreciation=float(merged["appreciation"]),
        sale_cost_pct=float(merged["sale_cost_pct"]),
        use_exit_cap=bool(merged["use_exit_cap"]),
        exit_cap_rate=float(merged["exit_cap_rate"]),
    )

    out = run_underwriting(i)
    memo = generate_investment_memo(out.narrative_seed, OPENAI_API_KEY) if (use_ai and OPENAI_API_KEY) else None

    metrics_summary = {
        "cap_rate": out.metrics.get("CapRate"),
        "cash_on_cash": out.metrics.get("CoC"),
        "dscr": out.metrics.get("DSCR"),
        "irr": out.metrics.get("IRR"),
        "noi_monthly": (out.metrics.get("NOI") / 12.0) if isinstance(out.metrics.get("NOI"), (int, float)) else None,
        "payment_monthly": out.metrics.get("LoanPaymentMonthly"),
        "cashflow_monthly": out.metrics.get("CashFlowMonthly"),
    }

    payload = {
        "inputs": i.__dict__,
        "outputs": {
            "score": out.score,
            "score_base": out.score_base,
            "score_ai": out.score_ai,
            "ai_weight": out.ai_weight,
            "grade": out.grade,
            "grade_detail": out.grade_detail,
            "verdict": out.verdict,
            "confidence": out.confidence,
            "metrics": out.metrics,
            "metrics_summary": metrics_summary,
            "flags": out.flags,
            "rationale": out.rationale,
            "ai_meta": out.ai_meta,
            "memo": memo,
        },
        "sources": pulled.get("notes", []) if isinstance(pulled, dict) else [],
        "provenance": prov
    }
    rid = save_report(addr, url, out.grade, out.score, out.confidence, payload, workspace_id=st.session_state.active_workspace_id, user_id=st.session_state.user['id'])
    log_event("grade_saved", report_id=rid, grade=out.grade, score=out.score, confidence=out.confidence)

    return {
        "address": addr,
        "url": url,
        "grade": out.grade,
        "grade_detail": out.grade_detail,
        "score": out.score,
        "score_base": out.score_base,
        "score_ai": out.score_ai,
        "ai_weight": out.ai_weight,
        "confidence": out.confidence,
        "verdict": out.verdict,
        "cap_rate": out.metrics.get("CapRate"),
        "coc": out.metrics.get("CoC"),
        "dscr": out.metrics.get("DSCR"),
        "irr": out.metrics.get("IRR"),
        "price": i.price, "rent": i.monthly_rent, "expenses": i.monthly_expenses,
        "sources": ", ".join(payload["sources"]) if payload["sources"] else "Manual / none",
        "metrics": metrics_summary,
        "report_id": rid,
        "memo": memo,
        "flags": "; ".join(out.flags[:6]) if out.flags else "",
        "rationale": out.rationale,
        "ai_meta": out.ai_meta,
        "payload": payload
    }

def pct(x: Optional[float]) -> str:
    return f"{x*100:.2f}%" if isinstance(x, (int,float)) else "—"

def num(x: Optional[float], nd: int = 2) -> str:
    return f"{x:.{nd}f}" if isinstance(x, (int,float)) else "—"

def mini_line(title: str, ys: List[float], xlabel: str = "Year", ylabel: str = ""):
    if not ys:
        return
    fig = plt.figure()
    plt.plot(list(range(len(ys))), ys)
    plt.title(title)
    plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    st.pyplot(fig, clear_figure=True)

# Sidebar (icon nav)
st.sidebar.markdown("## ⚡ AIRE")
simple_mode = st.sidebar.toggle("Simple Mode (recommended)", value=True)
st.sidebar.caption("Paste → Grade → Done.")

nav_items = [
    ("🏠", "Home"),
    ("⚡", "Grade a Deal"),
    ("📚", "Batch Screener"),
    ("🔔", "Alerts"),
    ("🧩", "Templates"),
    ("🗂️", "Reports"),
    ("💳", "Billing"),
    ("🔑", "API"),
    ("⚙️", "Settings"),
]
nav_labels = [f"{i[0]}  {i[1]}" for i in nav_items]
page = st.sidebar.radio("Navigation", nav_labels, index=1)
page_key = dict(zip(nav_labels, [i[1] for i in nav_items]))[page]

tpls = templates_all()
tpl_names = [t["name"] for t in tpls]
default_idx = tpl_names.index("Long-Term Rental (LTR)") if "Long-Term Rental (LTR)" in tpl_names else 0
chosen_name = st.sidebar.selectbox("Strategy", tpl_names, index=default_idx)
chosen_template = next(t for t in tpls if t["name"] == chosen_name)["template"]

use_auto = st.sidebar.checkbox("Auto-pull data", value=True)
use_ai = st.sidebar.checkbox("AI Summary", value=bool(OPENAI_API_KEY))

# Home
if page_key == "Home":
    st.markdown('<div class="card hero">', unsafe_allow_html=True)
    st.markdown('<h1>Like a Bloomberg terminal — but for <span style="background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;color:transparent;">real estate</span>.</h1>', unsafe_allow_html=True)
    st.markdown('<p>Third‑grader simple: paste a link/address → click Grade → read A–F + BUY/PASS. Batch screen and alerts make it feel like a trading platform.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    reports = list_reports(200, workspace_id=st.session_state.active_workspace_id)
    wl = list_watchlist(workspace_id=st.session_state.active_workspace_id)
    hist = list_alert_runs(200, workspace_id=st.session_state.active_workspace_id)
    total_hits = sum(1 for r in hist if int(r.get("hit",0)) == 1)

    st.markdown('<div class="kpis">', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi"><div class="label">Reports</div><div class="value">{len(reports)}</div><div class="hint">Saved underwriting runs</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi"><div class="label">Watchlist</div><div class="value">{len(wl)}</div><div class="hint">Deals monitored</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi"><div class="label">Alert hits</div><div class="value">{total_hits}</div><div class="hint">Scans meeting targets</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 0.8], gap="large")
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Recent activity")
        if reports:
            st.dataframe(pd.DataFrame(reports[:25]), use_container_width=True, hide_index=True)
        else:
            st.caption("No reports yet. Go to **Grade a Deal**.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Quick start")
        st.write("1) Paste link/address")
        st.write("2) Click **Grade**")
        st.write("3) Read grade + verdict")
        st.caption("Tip: For best reliability, paste a one-line address.")
        st.caption("Not financial advice. Verify all figures; data may be incomplete or delayed.")
        st.caption("AIRE_BUILD: launch-ready-real-company")
        st.markdown('</div>', unsafe_allow_html=True)

# Grade a Deal
if page_key == "Grade a Deal":
    # Two-step flow: 1) paste → 2) results (simple for beginners, expandable for pros)
    if "deal_step" not in st.session_state:
        st.session_state.deal_step = 1
    if "last_grade_result" not in st.session_state:
        st.session_state.last_grade_result = None

    left, right = st.columns([1.15, 0.85], gap="large")

    # ---------- Step 1: Paste & Grade ----------
    if st.session_state.deal_step == 1:
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            app_header("⚡ Grade a Deal", "Step 1 of 2 — paste a link/address. That's it.")
            breadcrumb(1)
            raw = st.text_input("Link or address", key="deal_raw", placeholder="https://...  OR  123 Main St, City, ST 12345")
            # Beginner-friendly: keep overrides hidden
            with st.expander("Optional inputs (advanced)", expanded=False):
                c1, c2, c3 = st.columns(3)
                price = c1.number_input("Price ($)", 0.0, 50_000_000.0, 0.0, 1000.0, key="deal_price")
                rent  = c2.number_input("Rent ($/mo)", 0.0, 1_000_000.0, 0.0, 50.0, key="deal_rent")
                exp   = c3.number_input("Expenses ($/mo)", 0.0, 1_000_000.0, 0.0, 50.0, key="deal_exp")
                st.caption("Tip: leave these blank if you don't know them — we'll estimate from available data.")
            run = st.button("✅ Next: Grade", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            app_header("Result", "Step 2 will show the grade + report.")
            breadcrumb(1)
            st.caption("Paste a link/address and press **Next: Grade**.")
            st.markdown('</div>', unsafe_allow_html=True)

        if run:
            raw = (st.session_state.get("deal_raw") or "").strip()
            if not raw:
                st.error("Paste a link or address.")
            else:
                used = count_last_24h(st.session_state.active_workspace_id, "grade")
                if used >= limits["grades_per_day"]:
                    st.error("Daily grade limit reached for your plan. Upgrade in Billing.")
                else:
                    record(st.session_state.active_workspace_id, st.session_state.user['id'], "grade")
                    overrides = {
                        "price": float(st.session_state.get("deal_price", 0.0) or 0.0),
                        "rent": float(st.session_state.get("deal_rent", 0.0) or 0.0),
                        "exp": float(st.session_state.get("deal_exp", 0.0) or 0.0),
                        "address_override": None,
                    }
                    r = run_one(raw, chosen_template, overrides, use_auto, use_ai)
                    st.session_state.last_grade_result = r
                    st.session_state.deal_step = 2
                    st.rerun()

    # ---------- Step 2: Results & Pro Controls ----------
    else:
        r = st.session_state.last_grade_result or {}

        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            app_header("✅ Report", "Step 2 of 2 — results + export. Advanced controls are optional.")
            cta1, cta2 = st.columns([1, 1])
            if cta1.button("↩ Grade another deal", use_container_width=True):
                st.session_state.deal_step = 1
                st.session_state.last_grade_result = None
                st.rerun()
            if cta2.button("🔄 Re-run with same inputs", use_container_width=True):
                raw = (st.session_state.get("deal_raw") or "").strip()
                if raw:
                    used = count_last_24h(st.session_state.active_workspace_id, "grade")
                    if used >= limits["grades_per_day"]:
                        st.error("Daily grade limit reached for your plan. Upgrade in Billing.")
                    else:
                        record(st.session_state.active_workspace_id, st.session_state.user['id'], "grade")
                        overrides = {
                            "price": float(st.session_state.get("deal_price", 0.0) or 0.0),
                            "rent": float(st.session_state.get("deal_rent", 0.0) or 0.0),
                            "exp": float(st.session_state.get("deal_exp", 0.0) or 0.0),
                            "address_override": None,
                        }
                        r = run_one(raw, chosen_template, overrides, use_auto, use_ai)
                        st.session_state.last_grade_result = r
                        st.rerun()

            # Pro / firm controls: everything technical goes here, without cluttering the main flow
            with st.expander("Pro controls (firms / analysts)", expanded=False):
                st.caption("For institutions: override assumptions, choose templates, force manual inputs, or disable AI.")
                c1, c2, c3 = st.columns(3)
                st.session_state.deal_price = c1.number_input("Price ($)", 0.0, 50_000_000.0, float(st.session_state.get("deal_price", 0.0) or 0.0), 1000.0)
                st.session_state.deal_rent  = c2.number_input("Rent ($/mo)", 0.0, 1_000_000.0, float(st.session_state.get("deal_rent", 0.0) or 0.0), 50.0)
                st.session_state.deal_exp   = c3.number_input("Expenses ($/mo)", 0.0, 1_000_000.0, float(st.session_state.get("deal_exp", 0.0) or 0.0), 50.0)

                c4, c5 = st.columns(2)
                _use_auto = c4.checkbox("Auto-pull data (APIs)", value=bool(use_auto))
                _use_ai   = c5.checkbox("AI memo summary", value=bool(use_ai), disabled=not bool(OPENAI_API_KEY))

                st.caption("Template selection is managed in the sidebar for consistency across pages.")
                if st.button("Apply pro settings + Re-run", type="primary", use_container_width=True):
                    raw = (st.session_state.get("deal_raw") or "").strip()
                    if not raw:
                        st.error("Paste a link or address.")
                    else:
                        used = count_last_24h(st.session_state.active_workspace_id, "grade")
                        if used >= limits["grades_per_day"]:
                            st.error("Daily grade limit reached for your plan. Upgrade in Billing.")
                        else:
                            record(st.session_state.active_workspace_id, st.session_state.user['id'], "grade")
                            overrides = {
                                "price": float(st.session_state.get("deal_price", 0.0) or 0.0),
                                "rent": float(st.session_state.get("deal_rent", 0.0) or 0.0),
                                "exp": float(st.session_state.get("deal_exp", 0.0) or 0.0),
                                "address_override": None,
                            }
                            rr = run_one(raw, chosen_template, overrides, _use_auto, _use_ai)
                            st.session_state.last_grade_result = rr
                            st.success("Updated.")
                            st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            app_header("Final Report", "Step 2 of 2 — overview first, details on-demand.")
            breadcrumb(2)

            if not r:
                st.error("Paste a link or address.")
            elif r.get("error"):
                st.error(r["error"])
            else:
                src_short = "API" if "RentCast" in r.get("sources","") else ("Mixed" if "API" in (r.get("sources","")) else "Manual")
                grade_display = r.get("grade_detail", r["grade"])
                st.markdown(
                    f"""
                    <div class="gradehero">
                      <div class="gradecopy">
                        <div class="gradelabel">Investment Grade</div>
                        <div class="gradevalue">{grade_display}</div>
                        <div class="gradeverdict">{r["verdict"]}</div>
                      </div>
                      <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end;">
                        <span class="badge-soft">Score: {r['score']:.1f}/100</span>
                        <span class="badge-soft">Confidence: {int(r['confidence']*100)}%</span>
                        <span class="badge-soft">Data: {src_short}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                t_over, t_details, t_export = st.tabs(["Overview", "Details", "Export"])

                with t_over:
                    st.markdown(
                        f"""
                        <div class="report-grid">
                          <div class="report-card">
                            <h4>Key metrics</h4>
                            <div class="metric-list">
                              <span>Cap rate: <strong>{pct(r.get('cap_rate'))}</strong></span>
                              <span>Cash-on-cash: <strong>{pct(r.get('coc'))}</strong></span>
                              <span>DSCR: <strong>{num(r.get('dscr'))}</strong></span>
                              <span>IRR (est.): <strong>{pct(r.get('irr'))}</strong></span>
                            </div>
                          </div>
                          <div class="report-card">
                            <h4>Score blend</h4>
                            <div class="scoreblend">
                              <span class="pill">Base: {r.get('score_base', 0.0):.1f}/100</span>
                              <span class="pill">AI: {r.get('score_ai', 0.0):.1f}/100</span>
                              <span class="pill">AI weight: {int((r.get('ai_weight') or 0.0)*100)}%</span>
                            </div>
                            <div style="margin-top:8px; color:var(--muted); font-size:12px;">
                              Proprietary blend: base underwriting + AI signal.
                            </div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    rationale = r.get("rationale") or (r.get("payload") or {}).get("outputs", {}).get("rationale") or []
                    flags = [f.strip() for f in (r.get("flags") or "").split(";") if f.strip()]
                    if rationale or flags:
                        st.markdown(
                            """
                            <div class="report-grid" style="margin-top:12px;">
                              <div class="report-card">
                                <h4>Grade rationale</h4>
                                <div class="bullet-list">
                            """,
                            unsafe_allow_html=True,
                        )
                        if rationale:
                            for reason in rationale[:10]:
                                st.markdown(f"<div>{reason}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div>Rationale unavailable.</div>", unsafe_allow_html=True)
                        st.markdown(
                            """
                                </div>
                              </div>
                              <div class="report-card">
                                <h4>Risk flags</h4>
                                <div class="bullet-list">
                            """,
                            unsafe_allow_html=True,
                        )
                        if flags:
                            for f in flags[:10]:
                                st.markdown(f"<div>{f}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown("<div>No flags.</div>", unsafe_allow_html=True)
                        st.markdown(
                            """
                                </div>
                              </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if r.get("memo"):
                        st.markdown("#### AI summary")
                        st.write(r["memo"])

                    st.success(f"Saved report #{r['report_id']}.")

                with t_details:
                    # Keep heavy/long items here to reduce scrolling
                    with st.expander("Data provenance (where numbers came from)", expanded=False):
                        prov = (r.get("payload") or {}).get("provenance", {}) or {}
                        st.json(prov)

                    if (not simple_mode):
                        metrics = (r.get("payload") or {}).get("outputs", {}).get("metrics", {}) or {}
                        cashflows = metrics.get("Cashflows")
                        if isinstance(cashflows, list) and cashflows:
                            st.markdown("#### Mini chart")
                            mini_line("Projected Cashflows (Annual)", cashflows, ylabel="$")

                    with st.expander("Raw payload (advanced)", expanded=False):
                        st.json(r.get("payload") or {})

                with t_export:
                    st.markdown("#### Export")
                    payload_json = json.dumps(r["payload"], indent=2)
                    col_a, col_b, col_c = st.columns(3)
                    pdf_bytes = build_report_pdf(r)
                    col_a.download_button("Download PDF", pdf_bytes, f"aire_report_{r['report_id']}.pdf", "application/pdf", use_container_width=True)
                    col_a.download_button("Download JSON", payload_json.encode("utf-8"), f"aire_report_{r['report_id']}.json", "application/json", use_container_width=True)

                    flags_md = "- None"
                    if r.get("flags"):
                        flags_md = "- " + "\n- ".join([x.strip() for x in r["flags"].split(";") if x.strip()])
                    grade_display = r.get("grade_detail", r["grade"])
                    rationale_md = "- None"
                    if r.get("rationale"):
                        rationale_md = "- " + "\n- ".join([str(x) for x in r["rationale"] if str(x).strip()])
                    md = f"""# AIRE Report

**Address:** {r['address']}

**Grade:** {grade_display} ({r['score']:.1f}/100)

**Verdict:** {r['verdict']}

## Key Metrics
- Cap rate: {pct(r.get('cap_rate'))}
- Cash-on-cash: {pct(r.get('coc'))}
- DSCR: {num(r.get('dscr'))}
- IRR (est.): {pct(r.get('irr'))}

## Flags
{flags_md}

## Grade Rationale
{rationale_md}
"""
                    col_b.download_button("Download Markdown", md.encode("utf-8"), f"aire_report_{r['report_id']}.md", "text/markdown", use_container_width=True)
                    col_c.download_button(
                        "Download CSV (1 row)",
                        pd.DataFrame([{k:v for k,v in r.items() if k not in ('payload','memo')}]).to_csv(index=False).encode("utf-8"),
                        f"aire_report_{r['report_id']}.csv",
                        "text/csv",
                        use_container_width=True,
                    )

            st.markdown('</div>', unsafe_allow_html=True)# Batch Screener
if page_key == "Batch Screener":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📚 Batch Screener (Orderbook style)")
    bulk = st.text_area("Links/addresses (one per line)", height=220)
    c1, c2, c3 = st.columns(3)
    max_rows = c1.number_input("Max rows", 1, 800, min(75, limits["batch_rows"]), 1)
    st.caption(f"Your plan allows up to {limits['batch_rows']} rows per batch.")
    ai_top = c2.checkbox("AI summaries for top 5", value=False, disabled=not bool(OPENAI_API_KEY))
    runb = c3.button("✅ Grade batch", type="primary", use_container_width=True)

    if runb:
        cap = min(int(max_rows), int(limits['batch_rows']))
        lines = [l.strip() for l in (bulk or "").splitlines() if l.strip()][:cap]
        results, errors = [], []
        with st.spinner("Grading batch…"):
            for raw in lines:
                r = run_one(raw, chosen_template, {"price":0.0,"rent":0.0,"exp":0.0,"address_override":None}, use_auto, False)
                if not r or r.get("error"):
                    errors.append({"raw": raw, "error": (r or {}).get("error","Could not resolve")})
                else:
                    results.append(r)

        if errors:
            st.warning(f"{len(errors)} couldn't be resolved. Paste a one-line address for those.")
            st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

        df = pd.DataFrame(results)
        if df.empty:
            st.error("No successful rows.")
        else:
            df = df.sort_values(["score","confidence"], ascending=[False, False])
            cols = ["grade_detail","grade","score","confidence","verdict","address","cap_rate","coc","dscr","irr","price","rent","expenses","sources","flags","report_id"]
            cols = [c for c in cols if c in df.columns]
            st.markdown('<div class="tablewrap">', unsafe_allow_html=True)
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button("Download ranked CSV", df.to_csv(index=False).encode("utf-8"), "ranked_deals.csv", "text/csv", use_container_width=True)

            if ai_top and OPENAI_API_KEY:
                st.divider()
                st.markdown("### AI summaries (Top 5)")
                for row in df.head(5).to_dict("records"):
                    grade_display = row.get("grade_detail") or row.get("grade")
                    st.markdown(f"#### {row['address']} — {grade_display} ({row['score']:.1f})")
                    memo = generate_investment_memo((row.get("payload") or {}).get("outputs", {}), OPENAI_API_KEY)
                    st.write(memo or "AI summary unavailable.")

    st.markdown('</div>', unsafe_allow_html=True)

# Alerts
if page_key == "Alerts":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔔 Alerts (Watchlist)")
    wl = list_watchlist(workspace_id=st.session_state.active_workspace_id)

    c1, c2 = st.columns([2,1])
    addr_or_link = c1.text_input("Paste address or link", placeholder="123 Main St... or https://...")
    note = c2.text_input("Note", placeholder="Why you care")
    c3, c4 = st.columns(2)
    tgt_grade = c3.selectbox("Target grade", ["A","B","C","D"], index=1)
    tgt_score = c4.slider("Target score", 50, 99, 80, 1)

    if st.button("Add to watchlist", type="primary", use_container_width=True):
        raw = (addr_or_link or "").strip()
        if not raw:
            st.error("Paste an address or link.")
        else:
            if looks_like_url(raw):
                res = guess_address_from_url(raw)
                addr = res.address_guess or raw
                url = raw
            else:
                addr, url = raw, ""
            add_watchlist(addr, url, tgt_grade, float(tgt_score), note, workspace_id=st.session_state.active_workspace_id, user_id=st.session_state.user['id'])
            st.success("Added.")

    st.divider()
    if wl:
        st.dataframe(pd.DataFrame(wl), use_container_width=True, hide_index=True)
        del_id = st.number_input("Delete by ID", min_value=0, value=0, step=1)
        if del_id and st.button("Delete item", use_container_width=True):
            delete_watchlist(int(del_id))
            st.success("Deleted. Reload.")
    else:
        st.caption("No watchlist items yet.")

    st.divider()
    email_me = st.checkbox("Email me when a hit occurs (optional)", value=False, disabled=not bool(SENDGRID_API_KEY and ALERT_EMAIL_TO))
    if email_me and not (SENDGRID_API_KEY and ALERT_EMAIL_TO):
        st.caption("Add SENDGRID_API_KEY and ALERT_EMAIL_TO in Secrets to enable email alerts.")

    if st.button("Scan watchlist", use_container_width=True):
        if not wl:
            st.warning("Add items first.")
        else:
            rank = {"A":4,"B":3,"C":2,"D":1,"F":0}
            results = []
            hits = []
            with st.spinner("Scanning…"):
                for item in wl:
                    raw = item["url"] if item["url"] else item["address"]
                    r = run_one(raw, chosen_template, {"price":0.0,"rent":0.0,"exp":0.0,"address_override": item["address"]}, use_auto, False)
                    if not r or r.get("error"):
                        continue
                    hit = int((r["score"] >= float(item["target_score"])) and (rank.get(r["grade"],0) >= rank.get(item["target_grade"],0)))
                    save_alert_run(item["id"], r["address"], r["url"], r["grade"], r["score"], r["confidence"], hit, r["payload"], workspace_id=st.session_state.active_workspace_id, user_id=st.session_state.user['id'])
                    r["hit"] = "✅" if hit else ""
                    r["watchlist_id"] = item["id"]
                    results.append(r)
                    if hit:
                        hits.append(r)

            if results:
                df = pd.DataFrame(results).sort_values(["hit","score"], ascending=[False, False])
                st.dataframe(df[["hit","watchlist_id","address","grade","score","confidence","verdict","sources","flags","report_id"]],
                             use_container_width=True, hide_index=True)
            else:
                st.info("No results (couldn’t resolve entries).")

            if email_me and hits and SENDGRID_API_KEY and ALERT_EMAIL_TO:
                try:
                    subject = f"AIRE Alert: {len(hits)} hit(s)"
                    lines = [f"{h['address']} — {h['grade']} ({h['score']:.1f}) — {h['verdict']}" for h in hits[:12]]
                    body = "Hits:\n" + "\n".join(lines)
                    resp = requests.post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "personalizations": [{"to": [{"email": ALERT_EMAIL_TO}]}],
                            "from": {"email": ALERT_EMAIL_TO},
                            "subject": subject,
                            "content": [{"type": "text/plain", "value": body}]
                        },
                        timeout=cfg.api_timeout_sec
                    )
                    if 200 <= resp.status_code < 300:
                        st.success(f"Email sent to {ALERT_EMAIL_TO}.")
                    else:
                        st.warning("Email failed (check SendGrid config).")
                except Exception:
                    st.warning("Email failed (network/config).")

    st.divider()
    hist = list_alert_runs(100, workspace_id=st.session_state.active_workspace_id)
    if hist:
        st.markdown("#### Alert history")
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
        rid = st.number_input("Open alert payload by ID", min_value=0, value=0, step=1, key="alert_open")
        if rid:
            st.json(read_alert_run(int(rid)))
    else:
        st.caption("No alert runs yet.")
    st.markdown('</div>', unsafe_allow_html=True)

# Outcomes
if page_key == "Outcomes":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📈 Outcomes (Ground Truth)")
    st.caption("This is what makes the model institution-grade: real rent, vacancy, repairs, resale, and IRR.")

    role = (st.session_state.get("active_role") or "member").lower()
    is_admin = role in ("owner","admin")

    # Simple form (average user)
    st.markdown("#### Add outcome (simple)")
    with st.form("outcome_simple_form"):
        address = st.text_input("Property address", placeholder="123 Main St, City, ST")
        purchase_price = st.number_input("Purchase price", min_value=0.0, value=0.0, step=1000.0)
        actual_rent = st.number_input("Actual monthly rent achieved", min_value=0.0, value=0.0, step=50.0)
        vacancy_days = st.number_input("Vacancy time (days vacant)", min_value=0, value=0, step=5)
        repairs = st.number_input("Repair costs (total)", min_value=0.0, value=0.0, step=250.0)
        hold_months = st.number_input("Hold period (months)", min_value=0, value=12, step=1)
        resale_price = st.number_input("Resale price (or current value)", min_value=0.0, value=0.0, step=1000.0)
        url = st.text_input("Link (optional)", placeholder="https://www.zillow.com/...")
        notes = st.text_area("Notes (optional)", height=90)
        saved = st.form_submit_button("Save outcome", use_container_width=True)
        if saved:
            oid = upsert_outcome(
                st.session_state.active_workspace_id,
                int(st.session_state.user["id"]),
                report_id=0,
                address=address.strip(),
                url=url.strip(),
                actual_monthly_rent=float(actual_rent),
                vacancy_days=int(vacancy_days),
                repair_costs=float(repairs),
                hold_months=int(hold_months),
                resale_price=float(resale_price),
                purchase_price=float(purchase_price),
                notes=notes.strip(),
            )
            st.success(f"Saved outcome #{oid}.")

    st.divider()
    st.markdown("#### Import outcomes (CSV)")
    st.caption("Upload a CSV export from your property management/accounting tool. Required columns: address, purchase_price, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price. Optional: url, notes.")
    csv_file = st.file_uploader("Upload CSV", type=["csv"])
    if csv_file is not None:
        import pandas as pd
        df = pd.read_csv(csv_file)
        st.write("Preview:")
        st.dataframe(df.head(25), use_container_width=True)

        required = ["address","purchase_price","actual_monthly_rent","vacancy_days","repair_costs","hold_months","resale_price"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
        else:
            if st.button("Import all rows", use_container_width=True):
                imported = 0
                for _, row in df.iterrows():
                    # Auto-link if report_id missing (by URL/address)
                    rid = int(row.get('report_id') or 0)
                    if rid <= 0:
                        best_id, conf = find_best_report_match(st.session_state.active_workspace_id, str(row.get('address') or ''), str(row.get('url') or ''))
                        if best_id and conf >= 0.70:
                            rid = int(best_id)
                    try:
                        upsert_outcome(
                            st.session_state.active_workspace_id,
                            int(st.session_state.user["id"]),
                            report_id=rid,
                            address=str(row.get("address") or "").strip(),
                            url=str(row.get("url") or "").strip(),
                            actual_monthly_rent=float(row.get("actual_monthly_rent") or 0),
                            vacancy_days=int(row.get("vacancy_days") or 0),
                            repair_costs=float(row.get("repair_costs") or 0),
                            hold_months=int(row.get("hold_months") or 0),
                            resale_price=float(row.get("resale_price") or 0),
                            purchase_price=float(row.get("purchase_price") or 0),
                            notes=str(row.get("notes") or "").strip(),
                        )
                        imported += 1
                    except Exception:
                        continue
                st.success(f"Imported {imported} outcomes.")
                st.rerun()

    st.divider()
    st.markdown("#### Outcomes table")
st.divider()
st.markdown("#### 🧩 Outcome Linking Wizard (recommended)")
st.caption("Auto-matches outcomes (missing report_id) to past reports using URL + address similarity, so training learns from the original feature set.")

unlinked = list_unlinked_outcomes(st.session_state.active_workspace_id, limit=250)
st.write(f"Unlinked outcomes: **{len(unlinked)}**")
if unlinked:
    cprev, cauto = st.columns(2)
    if cprev.button("Preview matches", use_container_width=True):
        preview = []
        for o in unlinked[:100]:
            rid, confm = find_best_report_match(st.session_state.active_workspace_id, o.get("address",""), o.get("url",""))
            preview.append({"outcome_id": o["id"], "address": o.get("address",""), "suggested_report_id": rid, "confidence": confm})
        import pandas as pd
        st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

    if cauto.button("Auto-match unlinked outcomes", use_container_width=True):
        linked = 0
        for o in unlinked:
            rid, conf = find_best_report_match(st.session_state.active_workspace_id, o.get("address",""), o.get("url",""))
            if rid and conf >= 0.70:
                link_outcome_to_report(st.session_state.active_workspace_id, int(o["id"]), int(rid))
                linked += 1
        st.success(f"Auto-linked {linked} outcomes (confidence ≥ 0.70).")
        st.rerun()

    with st.expander("Manual linking (advanced)", expanded=False):
        st.caption("Pick a report for any outcome the auto-matcher missed.")
        from db import fetchall
        rep_rows = fetchall(
            "SELECT id, address FROM reports WHERE workspace_id=? ORDER BY created_at DESC LIMIT 500",
            (int(st.session_state.active_workspace_id),)
        )
        rep_options = [(int(r[0]), (r[1] or f"Report #{r[0]}")) for r in rep_rows]
        rep_map = {rid: label for rid, label in rep_options}

        for o in unlinked[:50]:
            c1, c2, c3 = st.columns([4, 4, 2])
            c1.write(o.get("address","") or "(no address)")
            default_id, _conf = find_best_report_match(st.session_state.active_workspace_id, o.get("address",""), o.get("url",""))
            choices = [0] + [rid for rid, _ in rep_options]
            default_idx = choices.index(default_id) if default_id in choices else 0
            chosen = c2.selectbox(
                "Report",
                options=choices,
                format_func=lambda x: "— Select —" if x == 0 else f"{x}: {rep_map.get(x,'')}"[:80],
                index=default_idx,
                key=f"link_{o['id']}"
            )
            if c3.button("Link", key=f"btn_link_{o['id']}"):
                if int(chosen) > 0:
                    link_outcome_to_report(st.session_state.active_workspace_id, int(o["id"]), int(chosen))
                    st.success("Linked.")
                    st.rerun()
                else:
                    st.warning("Pick a report.")

    outs = list_outcomes(st.session_state.active_workspace_id, limit=200)
    st.write(f"Rows: **{len(outs)}**")
    if outs:
        import pandas as pd
        df = pd.DataFrame(outs)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Advanced (for technical teams)")
    st.caption("Admins can train models directly from outcomes in Governance (candidate → activate).")
    if not is_admin:
        st.info("Only admins can train/promote models.")

    st.markdown('</div>', unsafe_allow_html=True)


# Templates
if page_key == "Templates":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🧩 Templates")
    with st.expander("Built-in templates", expanded=False):
        built = pd.DataFrame([{"name": k, **normalize_template(v)} for k,v in BUILTIN_TEMPLATES.items()])
        st.dataframe(built, use_container_width=True, hide_index=True)

    user = list_templates(st.session_state.active_workspace_id)
    if user:
        st.markdown("#### Your templates")
        st.dataframe(pd.DataFrame([{"id": t["id"], "name": t["name"], **t["template"]} for t in user]), use_container_width=True, hide_index=True)
        del_id = st.number_input("Delete template by ID", min_value=0, value=0, step=1)
        if del_id and st.button("Delete template", use_container_width=True):
            delete_template(int(del_id))
            st.success("Deleted. Reload.")
    else:
        st.caption("No custom templates yet.")

    st.divider()
    st.markdown("#### Create template")
    name = st.text_input("Template name", value="My Strategy")
    c1, c2, c3 = st.columns(3)
    vacancy = c1.slider("Vacancy (%)", 0, 30, 8, 1) / 100.0
    down = c2.slider("Down payment (%)", 0, 100, 20, 1)
    rate = c3.number_input("Interest rate (%)", 0.0, 30.0, 7.25, 0.05)
    c4, c5, c6 = st.columns(3)
    term = c4.number_input("Term (years)", 1, 40, 30, 1)
    hold = c5.number_input("Hold (years)", 1, 20, 7, 1)
    sale_cost = c6.slider("Sale cost (%)", 0, 15, 7, 1) / 100.0
    exp_pct = st.slider("Expense estimate (% of rent) if missing", 0, 80, 45, 1) / 100.0
    if st.button("Save template", type="primary", use_container_width=True):
        tid = upsert_template(name, {
            "vacancy_rate": vacancy, "down_payment_pct": float(down), "interest_rate_pct": float(rate),
            "term_years": int(term), "hold_years": int(hold),
            "rent_growth": 0.03, "expense_growth": 0.03, "appreciation": 0.03,
            "sale_cost_pct": sale_cost, "use_exit_cap": False, "exit_cap_rate": 0.065,
            "defaults": {"monthly_expenses_pct_of_rent": exp_pct}
        }, workspace_id=st.session_state.active_workspace_id, user_id=st.session_state.user['id'])
        st.success(f"Saved template #{tid}.")
    st.markdown('</div>', unsafe_allow_html=True)

# Reports
if page_key == "Reports":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🗂️ Reports")
    rows = list_reports(200, workspace_id=st.session_state.active_workspace_id)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        rid = st.number_input("Open report by ID", min_value=0, value=0, step=1)
        if rid:
            payload = read_report(int(rid))
            st.json(payload if payload else {"error":"not found"})
    else:
        st.caption("No reports yet.")
    st.markdown('</div>', unsafe_allow_html=True)


# Billing
if page_key == "Billing":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 💳 Billing")

    sub = get_subscription(st.session_state.active_workspace_id)
    stored_plan = (sub.get("plan","free") or "free").lower()
    stored_status = (sub.get("status","active") or "active").lower()

    enforced_plan_local = stored_plan
    if not st.session_state.dev_mode:
        enforced_plan_local = effective_plan(sub)

    limits_local = plan_limits(enforced_plan_local)

    st.write(f"**Current plan:** `{stored_plan}`  •  **Status:** `{stored_status}`")
    st.write(f"**Enforced plan:** `{enforced_plan_local}`")
    st.write(f"**Daily grades:** {limits_local['grades_per_day']} • **Batch rows:** {limits_local['batch_rows']} • **API calls/day:** {limits_local['api_calls_per_day']}")

    if (not st.session_state.dev_mode) and (enforced_plan_local == "free") and (stored_plan != "free" or stored_status not in ("active","trialing")):
        st.warning("Your subscription is not active. Re-activate below or manage it in the customer portal.")

    st.divider()
    st.markdown("#### Customer Portal")
    cust_id = sub.get("stripe_customer_id")
    if stripe.api_key and cust_id:
        try:
            return_url = (cfg.stripe_portal_return_url or st.secrets.get("STRIPE_PORTAL_RETURN_URL","")).strip() or "http://localhost:8501/"
            portal_kwargs = {"customer": cust_id, "return_url": return_url}
            cfg_id = (cfg.stripe_portal_configuration_id or st.secrets.get("STRIPE_PORTAL_CONFIGURATION_ID","")).strip()
            if cfg_id:
                portal_kwargs["configuration"] = cfg_id
            ps = stripe.billing_portal.Session.create(**portal_kwargs)
            st.link_button("Open Stripe Customer Portal", ps.url, use_container_width=True)
            st.caption("Cancel, upgrade, downgrade, and manage payment methods.")
        except Exception:
            st.warning("Customer portal unavailable. Check Stripe keys and portal settings.")
    else:
        st.caption("Portal appears after your first successful checkout (Stripe customer ID).")

    st.divider()
    st.markdown("#### Upgrade / Subscribe")
    st.caption("Live billing: Stripe Checkout + webhook enforcement. Developer mode bypass is available for investor demos (your session only).")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Free**")
        st.write("- 5 grades/day")
        st.write("- Batch up to 25 rows")
        if st.button("Free (no checkout)", use_container_width=True):
            if st.session_state.dev_mode:
                set_plan(st.session_state.active_workspace_id, "free")
                st.success("Set to Free (dev mode).")
            else:
                st.info("To cancel a paid plan, use the Customer Portal above (or contact support).")

    with col2:
        st.markdown("**Pro**")
        st.write("- 100 grades/day")
        st.write("- Batch up to 200 rows")
        if st.button("Subscribe to Pro", type="primary", use_container_width=True):
            price_id = cfg.stripe_price_id_pro or st.secrets.get("STRIPE_PRICE_ID_PRO","")
            if not stripe.api_key or not price_id:
                if st.session_state.dev_mode:
                    set_plan(st.session_state.active_workspace_id, "pro")
                    st.success("Pro enabled (dev mode). Configure Stripe to charge customers.")
                else:
                    st.error("Stripe not configured. Add STRIPE_SECRET_KEY + STRIPE_PRICE_ID_PRO to go live.")
            else:
                try:
                    success_url = (cfg.stripe_success_url or st.secrets.get("STRIPE_SUCCESS_URL","")).strip() or "http://localhost:8501/?billing=success"
                    cancel_url  = (cfg.stripe_cancel_url  or st.secrets.get("STRIPE_CANCEL_URL","")).strip()  or "http://localhost:8501/?billing=cancel"
                    session = stripe.checkout.Session.create(
                        mode="subscription",
                        billing_address_collection="required",
                        tax_id_collection={"enabled": True},
                        automatic_tax={"enabled": True},
                        line_items=[{"price": price_id, "quantity": 1}],
                        success_url=success_url,
                        cancel_url=cancel_url,
                        client_reference_id=str(st.session_state.active_workspace_id),
                        customer_email=st.session_state.user.get("email"),
                        customer_update={"name": "auto", "address": "auto"},
                        allow_promotion_codes=True,
                        metadata={
                            "workspace_id": str(st.session_state.active_workspace_id),
                            "user_id": str(st.session_state.user.get("id")),
                            "product": "AIRE Terminal",
                            "plan_requested": "pro"
                        },
                    )
                    st.link_button("Continue to Stripe Checkout", session.url, use_container_width=True)
                    st.info("Stripe will update your plan via webhook (usually within seconds).")
                except Exception:
                    st.error("Stripe checkout failed. Check Stripe secrets and Price IDs.")

    with col3:
        st.markdown("**Team**")
        st.write("- 500 grades/day")
        st.write("- Batch up to 500 rows")
        if st.button("Subscribe to Team", use_container_width=True):
            price_id = cfg.stripe_price_id_team or st.secrets.get("STRIPE_PRICE_ID_TEAM","")
            if not stripe.api_key or not price_id:
                if st.session_state.dev_mode:
                    set_plan(st.session_state.active_workspace_id, "team")
                    st.success("Team enabled (dev mode). Configure Stripe to charge customers.")
                else:
                    st.error("Stripe not configured. Add STRIPE_SECRET_KEY + STRIPE_PRICE_ID_TEAM to go live.")
            else:
                try:
                    success_url = (cfg.stripe_success_url or st.secrets.get("STRIPE_SUCCESS_URL","")).strip() or "http://localhost:8501/?billing=success"
                    cancel_url  = (cfg.stripe_cancel_url  or st.secrets.get("STRIPE_CANCEL_URL","")).strip()  or "http://localhost:8501/?billing=cancel"
                    session = stripe.checkout.Session.create(
                        mode="subscription",
                        billing_address_collection="required",
                        tax_id_collection={"enabled": True},
                        automatic_tax={"enabled": True},
                        line_items=[{"price": price_id, "quantity": 1}],
                        success_url=success_url,
                        cancel_url=cancel_url,
                        client_reference_id=str(st.session_state.active_workspace_id),
                        customer_email=st.session_state.user.get("email"),
                        customer_update={"name": "auto", "address": "auto"},
                        allow_promotion_codes=True,
                        metadata={
                            "workspace_id": str(st.session_state.active_workspace_id),
                            "user_id": str(st.session_state.user.get("id")),
                            "product": "AIRE Terminal",
                            "plan_requested": "team"
                        },
                    )
                    st.link_button("Continue to Stripe Checkout", session.url, use_container_width=True)
                    st.info("Stripe will update your plan via webhook (usually within seconds).")
                except Exception:
                    st.error("Stripe checkout failed. Check Stripe secrets and Price IDs.")

    st.divider()
    st.markdown("#### Team workspace")
    c1, c2 = st.columns(2)
    with c1:
        new_ws_name = st.text_input("Create new workspace", placeholder="Acme Capital - Underwriting")
        if st.button("Create workspace", use_container_width=True):
            if new_ws_name.strip():
                wid = create_workspace(int(st.session_state.user["id"]), new_ws_name.strip())
                st.success(f"Created workspace #{wid}.")
                st.rerun()
    with c2:
        code = st.text_input("Join via invite code", placeholder="paste invite code")
        if st.button("Join workspace", use_container_width=True):
            wid = accept_invite(int(st.session_state.user["id"]), code.strip())
            if wid:
                st.success("Joined workspace.")
                st.rerun()
            else:
                st.error("Invalid invite code.")

    st.markdown('</div>', unsafe_allow_html=True)
# Workspace
if page_key == "Workspace":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🏢 Workspace Settings")

    role = (st.session_state.get("active_role") or "member").lower()
    is_owner = role == "owner"
    is_admin = role in ("owner","admin")

    st.write(f"**Your role:** `{role}`")

    if not is_admin:
        st.info("Only workspace admins can manage members and invites.")
    else:
        st.markdown("#### Members")
        members = list_members(st.session_state.active_workspace_id)
        if not members:
            st.caption("No members found.")
        else:
            for mem in members:
                cols = st.columns([4,2,3,2])
                cols[0].write(mem["email"])
                cols[1].write(f"`{mem['role']}`")
                if mem["role"] == "owner" and not is_owner:
                    cols[2].write("Owner")
                    cols[3].write("")
                    continue
                # role selector
                new_role = cols[2].selectbox(
                    "Role",
                    options=["owner","admin","member","viewer"],
                    index=["owner","admin","member","viewer"].index(mem["role"]) if mem["role"] in ["owner","admin","member","viewer"] else 2,
                    key=f"role_{mem['user_id']}",
                    disabled=(mem["role"]=="owner" and not is_owner),
                    label_visibility="collapsed",
                )
                if cols[3].button("Save", key=f"save_role_{mem['user_id']}"):
                    if (mem["role"]=="owner") and not is_owner:
                        st.warning("Only the owner can change the owner role.")
                    else:
                        set_member_role(st.session_state.active_workspace_id, mem["user_id"], new_role)
                        st.success("Updated.")
                        st.rerun()

            st.divider()
            st.markdown("#### Invites")
            c1, c2 = st.columns([2,1])
            invite_role = c1.selectbox("Invite role", ["member","viewer","admin"], index=0)
            if c2.button("Generate invite code", use_container_width=True):
                code = create_invite(int(st.session_state.user["id"]), st.session_state.active_workspace_id, invite_role)
                st.code(code)
                st.caption("Share this code so they can join your workspace.")

            st.divider()
            st.markdown("#### Remove member")
            rm_email = st.text_input("Remove by email", placeholder="someone@company.com")
            if st.button("Remove", use_container_width=True):
                if not rm_email.strip():
                    st.warning("Enter an email.")
                else:
                    # find user id
                    target = [m for m in members if m["email"].lower() == rm_email.lower().strip()]
                    if not target:
                        st.error("Member not found in this workspace.")
                    elif target[0]["role"] == "owner":
                        st.error("You cannot remove the owner.")
                    else:
                        remove_member(st.session_state.active_workspace_id, target[0]["user_id"])
                        st.success("Removed.")
                        st.rerun()

    st.divider()
    st.markdown("#### Billing profile (shown on invoices)")
    bp = get_billing_profile(st.session_state.active_workspace_id)
    with st.form("billing_profile_form"):
        company = st.text_input("Company / legal name", value=bp.get("company_name",""))
        bill_email = st.text_input("Billing email", value=bp.get("billing_email","") or st.session_state.user.get("email",""))
        tax_id = st.text_input("Tax ID (optional)", value=bp.get("tax_id",""))
        saved = st.form_submit_button("Save billing profile")
        if saved:
            upsert_billing_profile(st.session_state.active_workspace_id, company, bill_email, tax_id, bp.get("address",{}))
            st.success("Saved.")

    st.caption("Note: Stripe will still collect address and tax information during checkout. This profile is used for your internal records and metadata.")
    st.markdown('</div>', unsafe_allow_html=True)


# API
if page_key == "API":
    role = (st.session_state.get('active_role') or 'member').lower()
    is_admin = role in ('owner','admin')
    if not is_admin:
        st.warning('Only workspace admins can manage API keys.')

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔑 API Keys")
    sub = get_subscription(st.session_state.active_workspace_id)
# Hard lock when subscription inactive (unless dev mode)
stored_plan = (sub.get("plan","free") or "free").lower()
stored_status = (sub.get("status","active") or "active").lower()
inactive_paid = (stored_plan != "free") and (stored_status not in ("active","trialing"))

if (not st.session_state.dev_mode) and inactive_paid:
    # Only allow Billing so user can re-activate; everything else is locked
    if page_key != "Billing":
        render_lock(f"Plan is inactive by Stripe (status: {stored_status}).")
        st.stop()

# Subscription enforcement banner
if (not st.session_state.dev_mode) and (effective_plan(sub) == "free") and ((sub.get("plan","free") != "free") or (sub.get("status","active") not in ("active","trialing"))):
    st.warning("Your subscription is not active. Some features may be limited. Go to Billing to re-activate.")

    limits_local = plan_limits(sub.get("plan","free"))
    if limits_local.get("api_calls_per_day", 0) <= 0:
        st.warning("API access is disabled on your current plan. Upgrade to Pro/Team to enable.")
    keys = list_keys(st.session_state.active_workspace_id)
    if keys:
        st.dataframe(pd.DataFrame(keys), use_container_width=True, hide_index=True)
        kid = st.number_input("Revoke key by ID", min_value=0, value=0, step=1)
        if kid and st.button("Revoke", use_container_width=True):
            revoke_key(st.session_state.active_workspace_id, int(kid))
            st.success("Revoked. Reload.")
    else:
        st.caption("No API keys yet.")

    st.divider()
    st.markdown("#### Create key")
    label = st.text_input("Label", value="My integration")
    if st.button("Create API key", type="primary", use_container_width=True):
        if limits_local.get("api_calls_per_day", 0) <= 0:
            st.error("Upgrade plan to enable API keys.")
        else:
            k = create_key(st.session_state.active_workspace_id, label)
            st.success("API key created. Copy it now — it won’t be shown again.")
            st.code(k["api_key"])

    st.divider()
    st.markdown("#### API endpoint")
    st.code("""POST /v1/grade
Header: X-API-Key: <your key>
Body:
{
  "raw": "https://... or 123 Main St, City, ST 12345",
  "template_name": "Long-Term Rental (LTR)",
  "price": null,
  "monthly_rent": null,
  "monthly_expenses": null
}
""", language="json")

    st.caption("This FastAPI service is in `api_server.py`. Deploy it on Render/Fly/Railway; keep Streamlit as the UI.")
    st.markdown('</div>', unsafe_allow_html=True)

# Settings
if page_key == "Settings":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Settings / Health")
    a,b,c,d = st.columns(4)
    a.metric("RentCast", "✅" if RENTCAST_APIKEY else "—")
    b.metric("Estated", "✅" if ESTATED_TOKEN else "—")
    c.metric("ATTOM", "✅" if ATTOM_APIKEY else "—")
    d.metric("AI", "✅" if OPENAI_API_KEY else "—")

    st.divider()
    st.markdown("#### Secrets (copy/paste into Streamlit)")
    st.code("""RENTCAST_APIKEY = "YOUR_KEY"
ESTATED_TOKEN = ""
ATTOM_APIKEY = ""
OPENAI_API_KEY = ""

# Optional: private app gate
APP_ACCESS_KEY = ""

# Optional: performance
API_TIMEOUT_SEC = 15
CACHE_TTL_SEC = 3600

# Optional email alerts (SendGrid)
SENDGRID_API_KEY = ""
ALERT_EMAIL_TO = "you@example.com"

# Stripe (subscriptions)
STRIPE_SECRET_KEY = ""
STRIPE_PRICE_ID_PRO = ""
STRIPE_PRICE_ID_TEAM = ""
STRIPE_SUCCESS_URL = "https://your-streamlit-app.streamlit.app/?billing=success"
STRIPE_CANCEL_URL = "https://your-streamlit-app.streamlit.app/?billing=cancel"
""", language="toml")

    st.caption("If you only add one key: start with RentCast.")
    st.markdown('</div>', unsafe_allow_html=True)

# Governance
if page_key == "Governance":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    app_header("🧠 Model Governance", "Candidate models, guardrails, and audited promotions — enterprise-safe learning.")
    role = (st.session_state.get("active_role") or "member").lower()
    is_admin = role in ("owner","admin")
    if not is_admin:
        st.warning("Only workspace admins can access model governance.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    st.caption("This is **enterprise-safe learning**: feedback → candidate model → human approval → active model. No silent self-modifying behavior.")
    st.info("Tip: open the **Audit** tab to view full promotion logs.")
    st.divider()
    st.markdown("#### 🛡️ Promotion Guardrails")
    st.caption("Prevents model regression: you can only activate a candidate if it beats the current model on **validation F1** and you have enough linked outcomes.")
    cga, cgb, cgc = st.columns([2,2,2])
    guard_enabled = cga.checkbox("Enable guardrails", value=True)
    min_linked_outcomes = cgb.number_input("Min linked outcomes", min_value=0, value=50, step=10)
    f1_margin = cgc.number_input("Min validation F1 improvement", min_value=0.0, value=0.01, step=0.01, format="%.2f")
    linked_n = count_linked_outcomes(st.session_state.active_workspace_id)
    st.write(f"Linked outcomes available: **{linked_n}**")

    active = get_active_model(st.session_state.active_workspace_id)
    if active:
        st.success(f"Active model: **{active['name']}** (id {active['id']})")
        if active.get("metrics"):
            st.write("Metrics:", active["metrics"])
    else:
        st.info("Active model: baseline (hand-tuned, auditable).")

    st.divider()
    st.markdown("#### Feedback dataset")
    fb = list_feedback(st.session_state.active_workspace_id, limit=500)
    st.write(f"Feedback rows: **{len(fb)}**")
    if fb:
        good = sum(1 for x in fb if x["label"] == 1)
        bad = len(fb) - good
        st.write(f"👍 {good}  •  👎 {bad}")

    st.divider()
    st.divider()
st.markdown("#### Train from outcomes (recommended)")
st.caption("Uses real rent/vacancy/repairs/resale to compute IRR. Trains on *ROI truth* (institution-grade).")
outs = list_outcomes(st.session_state.active_workspace_id, limit=2000)
st.write(f"Outcome rows available: **{len(outs)}**")
with st.form("train_from_outcomes"):
    irr_threshold = st.slider("Good investment IRR threshold", 0.0, 0.50, 0.12, 0.01, help="Annual IRR. 0.12 = 12%")
    max_vacancy = st.slider("Max vacancy days", 0, 365, 60, 5)
    lr_o = st.slider("Learning rate (outcomes)", 0.01, 0.20, 0.05, 0.01, key="lr_o")
    epochs_o = st.slider("Epochs (outcomes)", 5, 60, 18, 1, key="ep_o")
    train_o = st.form_submit_button("Train candidate from outcomes")
    if train_o:
        if len(outs) < 30:
            st.error("Need at least ~30 outcome rows for meaningful training.")
        else:
            from storage import read_report
            rows = []
            for o in outs:
                rid = int(o.get("report_id") or 0)
                if rid <= 0:
                    continue
                payload = read_report(rid) or {}
                feats = learning.extract_features(payload)
                y = learning.label_from_outcome(o, irr_threshold=float(irr_threshold), max_vacancy_days=int(max_vacancy))
                rows.append((feats, int(y)))
            if len(rows) < 30:
                st.error("Not enough outcomes linked to reports (need report_id set so we can learn from the original feature set).")
            else:
                active = get_active_model(st.session_state.active_workspace_id)
                start_w = (active.get("weights") if active else None) or learning.default_weights()
                train_rows, val_rows = learning.train_val_split(rows, val_frac=0.2)
                cand_w = learning.train_sgd(train_rows, start_weights=start_w, lr=float(lr_o), epochs=int(epochs_o))
                metrics = {"train": learning.eval_metrics(train_rows, cand_w), "val": learning.eval_metrics(val_rows, cand_w)}
                mid = create_candidate_model(
                        st.session_state.active_workspace_id,
                        f"outcomes-{int(time.time())}",
                        cand_w,
                        metrics=metrics,
                        notes=f"Trained from outcomes: irr>={irr_threshold:.2f}, vac<={max_vacancy}",
                    )
                st.success(f"Trained candidate #{mid}. Val acc={metrics['val'].get('acc',0):.2f}  Val f1={metrics['val'].get('f1',0):.2f}")
                st.rerun()
st.markdown("#### Train candidate model")
with st.form("train_model_form"):
    model_name = st.text_input("Candidate model name", value="candidate-v1")
    lr = st.slider("Learning rate", 0.01, 0.20, 0.05, 0.01)
    epochs = st.slider("Epochs", 5, 40, 12, 1)
    train_btn = st.form_submit_button("Train from feedback")
    if train_btn:
        if len(fb) < 20:
            st.error("Need at least ~20 feedback rows to train a meaningful model.")
        else:
            from storage import read_report
            rows = []
            for item in fb:
                rid = int(item.get("report_id") or 0)
                if rid <= 0:
                    continue
                payload = read_report(rid) or {}
                feats = learning.extract_features(payload)
                rows.append((feats, int(item["label"])))
            if len(rows) < 20:
                st.error("Not enough linked report payloads to train (need feedback tied to report IDs).")
            else:
                active = get_active_model(st.session_state.active_workspace_id)
                start_w = (active.get("weights") if active else None) or learning.default_weights()
                train_rows, val_rows = learning.train_val_split(rows, val_frac=0.2)
                cand_w = learning.train_sgd(train_rows, start_weights=start_w, lr=float(lr), epochs=int(epochs))
                metrics = {"train": learning.eval_metrics(train_rows, cand_w), "val": learning.eval_metrics(val_rows, cand_w)}
                mid = create_candidate_model(
                    st.session_state.active_workspace_id,
                    model_name.strip()[:64],
                    cand_w,
                    metrics=metrics,
                    notes="Trained from feedback via SGD (train/val split)",
                )
                st.success(f"Trained candidate #{mid}. Val acc={metrics['val'].get('acc',0):.2f}  Val f1={metrics['val'].get('f1',0):.2f}")
                st.rerun()

    st.divider()
    st.markdown("#### Models")
    models = list_models(st.session_state.active_workspace_id)
    if not models:
        st.caption("No workspace models yet.")
    else:
        for m in models:
            cols = st.columns([3,2,3,4])
            cols[0].write(f"**{m['name']}**")
            cols[1].write(f"`{m['status']}`")
            if isinstance(m.get('metrics'), dict) and 'val' in m['metrics']:
                cols[2].write(f"val acc={m['metrics']['val'].get('acc',0):.2f}  f1={m['metrics']['val'].get('f1',0):.2f}")
            else:
                cols[2].write(f"n={m['metrics'].get('n',0)} acc={m['metrics'].get('acc',0):.2f}")

            # Banking-style: require a reason for any promotion
            reason = cols[3].text_input("Reason", placeholder="e.g., Val F1 improved with 200 linked outcomes", key=f"reason_{m['id']}")
            override = cols[3].checkbox("Override guardrails (admin only)", value=False, key=f"ovr_{m['id']}")
            if cols[3].button("Activate", key=f"act_{m['id']}", use_container_width=True):
                if not reason or len(reason.strip()) < 8:
                    st.error("Promotion requires a reason (min 8 characters).")
                else:
                    active_now = get_active_model(st.session_state.active_workspace_id)
                    active_f1 = get_val_f1(active_now) if active_now else 0.0
                    cand_f1 = get_val_f1(m)
                    linked_n = count_linked_outcomes(st.session_state.active_workspace_id)

                    # Guardrail settings from UI above (fallback defaults)
                    try:
                        _guard_enabled = bool(guard_enabled)
                        _min_n = int(min_linked_outcomes)
                        _margin = float(f1_margin)
                    except Exception:
                        _guard_enabled, _min_n, _margin = True, 50, 0.01

                    role = (st.session_state.get("active_role") or "member").lower()
                    is_admin = role in ("owner", "admin")

                    blocked_reason = None
                    if _guard_enabled:
                        if linked_n < _min_n:
                            blocked_reason = f"Need at least {_min_n} linked outcomes (have {linked_n})."
                        elif cand_f1 < (active_f1 + _margin):
                            blocked_reason = f"Candidate val F1 ({cand_f1:.2f}) must exceed active ({active_f1:.2f}) by ≥ {_margin:.2f}."

                    if blocked_reason and not override:
                        st.error("Blocked by guardrails: " + blocked_reason)
                    elif blocked_reason and override:
                        if not is_admin:
                            st.error("Override is admin-only.")
                        else:
                            # Force activation + audit
                            activate_model(st.session_state.active_workspace_id, int(m["id"]))
                            audit.log_event(
                                st.session_state.active_workspace_id,
                                int(st.session_state.user["id"]),
                                "model_promoted",
                                {
                                    "override": True,
                                    "blocked_reason": blocked_reason,
                                    "reason": reason.strip(),
                                    "from_model_id": int(active_now["id"]) if active_now else 0,
                                    "from_model_name": (active_now.get("name") if active_now else ""),
                                    "to_model_id": int(m["id"]),
                                    "to_model_name": m.get("name"),
                                    "from_metrics": (active_now.get("metrics") if active_now else {}),
                                    "to_metrics": (m.get("metrics") or {}),
                                    "linked_outcomes": linked_n,
                                    "guardrails": {"enabled": _guard_enabled, "min_linked_outcomes": _min_n, "min_f1_margin": _margin},
                                },
                            )
                            st.success("Activated (override logged).")
                            st.rerun()
                    else:
                        # Normal activation + audit
                        activate_model(st.session_state.active_workspace_id, int(m["id"]))
                        audit.log_event(
                            st.session_state.active_workspace_id,
                            int(st.session_state.user["id"]),
                            "model_promoted",
                            {
                                "override": False,
                                "reason": reason.strip(),
                                "from_model_id": int(active_now["id"]) if active_now else 0,
                                "from_model_name": (active_now.get("name") if active_now else ""),
                                "to_model_id": int(m["id"]),
                                "to_model_name": m.get("name"),
                                "from_metrics": (active_now.get("metrics") if active_now else {}),
                                "to_metrics": (m.get("metrics") or {}),
                                "linked_outcomes": linked_n,
                                "guardrails": {"enabled": _guard_enabled, "min_linked_outcomes": _min_n, "min_f1_margin": _margin},
                            },
                        )
                        st.success("Activated (promotion logged).")
                        st.rerun()

    st.divider()
    st.markdown("#### Why this is corporate-trustworthy")
    st.write("- No auto-updates to production models without approval")
    st.write("- Explainability: features + top drivers stored with each report")
    st.write("- Versioned models with metrics and notes")
    st.markdown('</div>', unsafe_allow_html=True)


# Audit
if page_key == "Audit":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    app_header("🧾 Audit Log", "Every promotion is logged: who, when, why, what changed, and metrics snapshots.")
    st.caption("Every promotion is logged (who, when, why, what changed, and a metrics snapshot).")
    events = audit.list_events(st.session_state.active_workspace_id, limit=300)
    if not events:
        st.info("No audit events yet.")
    else:
        import pandas as pd
        rows = []
        for e in events:
            payload = e.get("payload") or {}
            rows.append({
                "time": e.get("created_at"),
                "actor_user_id": e.get("actor_user_id"),
                "event": e.get("event_type"),
                "from_model": payload.get("from_model_name") or payload.get("from_model_id"),
                "to_model": payload.get("to_model_name") or payload.get("to_model_id"),
                "override": payload.get("override", False),
                "reason": payload.get("reason","")[:120],
                "val_f1_from": (payload.get("from_metrics",{}).get("val",{}).get("f1") if isinstance(payload.get("from_metrics"), dict) else None),
                "val_f1_to": (payload.get("to_metrics",{}).get("val",{}).get("f1") if isinstance(payload.get("to_metrics"), dict) else None),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("Raw event payloads (advanced)"):
            st.json(events)
    st.markdown('</div>', unsafe_allow_html=True)
