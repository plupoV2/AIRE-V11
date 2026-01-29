from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import stripe
import os

from api_keys import resolve_workspace, verify_key
from billing import get_subscription, plan_limits, effective_plan
from stripe_webhooks import process_event
from usage import count_last_24h, record

from underwriting import DealInputs, run_underwriting
from link_resolver import guess_address_from_url, looks_like_url
from templates import BUILTIN_TEMPLATES, normalize_template
from provenance import pick, pack_provenance

app = FastAPI(title="AIRE API", version="1.0")
# Stripe config (API service)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "")
STRIPE_PRICE_ID_TEAM = os.getenv("STRIPE_PRICE_ID_TEAM", "")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


class GradeRequest(BaseModel):
    raw: str
    template_name: str = "Long-Term Rental (LTR)"
    price: Optional[float] = None
    monthly_rent: Optional[float] = None
    monthly_expenses: Optional[float] = None
    use_auto: bool = False  # backend can be wired to real data similarly

class GradeResponse(BaseModel):
    address: str
    grade: str
    grade_detail: str
    score: float
    score_base: float
    score_ai: float
    ai_weight: float
    confidence: float
    verdict: str
    metrics: Dict[str, Any]
    flags: List[str]
    rationale: List[str]
    provenance: Dict[str, Any]

def _template_by_name(name: str) -> Dict[str, Any]:
    if name in BUILTIN_TEMPLATES:
        return normalize_template(BUILTIN_TEMPLATES[name])
    return normalize_template(BUILTIN_TEMPLATES["Long-Term Rental (LTR)"])

def _apply_template(t: Dict[str, Any], price: float, rent: float, exp: float):
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

def _auth(api_key: str) -> int:
    ws = resolve_workspace(api_key)
    if not ws:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not verify_key(ws, api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    sub = get_subscription(ws)
    plan = effective_plan(sub)
    limits = plan_limits(plan)
    if limits.get("api_calls_per_day", 0) <= 0:
        raise HTTPException(status_code=402, detail="API access not enabled on this plan")
    used = count_last_24h(ws, "api_call")
    if used >= limits["api_calls_per_day"]:
        raise HTTPException(status_code=429, detail="API rate limit exceeded")
    record(ws, 0, "api_call")
    return ws

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/v1/grade", response_model=GradeResponse)
def grade(req: GradeRequest, x_api_key: str = Header(default="")):
    ws = _auth(x_api_key)
    raw = (req.raw or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Missing raw")
    if looks_like_url(raw):
        resolved = guess_address_from_url(raw)
        addr = resolved.address_guess or raw
    else:
        addr = raw

    t = _template_by_name(req.template_name)
    merged = _apply_template(t, float(req.price or 0.0), float(req.monthly_rent or 0.0), float(req.monthly_expenses or 0.0))

    price_p = pick(req.price, merged.get("price"), "template/manual")
    rent_p  = pick(req.monthly_rent, merged.get("monthly_rent"), "template/manual")
    exp_p   = pick(req.monthly_expenses, merged.get("monthly_expenses"), "template/manual")
    prov = pack_provenance(price_p, rent_p, exp_p, None, None, "")

    i = DealInputs(
        address=addr,
        listing_url=raw if looks_like_url(raw) else "",
        price=float(price_p.value) if price_p.value else None,
        monthly_rent=float(rent_p.value) if rent_p.value else None,
        monthly_expenses=float(exp_p.value) if exp_p.value else None,
        vacancy_rate=float(merged["vacancy_rate"]),
        down_payment_pct=float(merged["down_payment_pct"]),
        interest_rate_pct=float(merged["interest_rate_pct"]),
        term_years=int(merged["term_years"]),
        last_sale_price=None,
        last_sale_date=None,
        hold_years=int(merged["hold_years"]),
        rent_growth=float(merged["rent_growth"]),
        expense_growth=float(merged["expense_growth"]),
        appreciation=float(merged["appreciation"]),
        sale_cost_pct=float(merged["sale_cost_pct"]),
        use_exit_cap=bool(merged["use_exit_cap"]),
        exit_cap_rate=float(merged["exit_cap_rate"]),
    )

    out = run_underwriting(i)
    return GradeResponse(
        address=addr,
        grade=out.grade,
        grade_detail=out.grade_detail,
        score=float(out.score),
        score_base=float(out.score_base),
        score_ai=float(out.score_ai),
        ai_weight=float(out.ai_weight),
        confidence=float(out.confidence),
        verdict=out.verdict,
        metrics=out.metrics,
        flags=out.flags,
        rationale=out.rationale,
        provenance=prov,
    )

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="", alias="Stripe-Signature")):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=stripe_signature, secret=STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # If subscription events are not expanded, fetch the subscription from Stripe for accuracy.
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if etype in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        # obj already is subscription
        process_event(event, STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_TEAM)
    elif etype == "checkout.session.completed":
        # Optionally fetch subscription (recommended) for accurate plan mapping
        sub_id = obj.get("subscription")
        if sub_id and STRIPE_SECRET_KEY:
            try:
                sub = stripe.Subscription.retrieve(sub_id)
                # Ensure workspace_id is present in metadata by copying from checkout session metadata if needed
                if (sub.get("metadata") or {}).get("workspace_id") is None and (obj.get("metadata") or {}).get("workspace_id") is not None:
                    try:
                        stripe.Subscription.modify(sub_id, metadata={"workspace_id": (obj.get("metadata") or {}).get("workspace_id")})
                        sub = stripe.Subscription.retrieve(sub_id)
                    except Exception:
                        pass
                process_event({"type": "customer.subscription.updated", "data": {"object": sub}}, STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_TEAM)
            except Exception:
                # fall back to processing the checkout event
                process_event(event, STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_TEAM)
        else:
            process_event(event, STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_TEAM)
    return {"received": True}
