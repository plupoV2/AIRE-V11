from typing import Dict, Any, Optional, Tuple
import time
from billing import set_plan

ACTIVE_STATUSES = {"active", "trialing"}
GRACE_STATUSES = {"past_due", "unpaid"}  # optionally allow grace in UI logic

def _now() -> int:
    return int(time.time())

def _plan_from_price_ids(price_ids: set, price_pro: str, price_team: str) -> str:
    # Highest plan wins
    if price_team and price_team in price_ids:
        return "team"
    if price_pro and price_pro in price_ids:
        return "pro"
    return "free"

def upsert_from_subscription(sub: Dict[str, Any], workspace_id: Optional[int], price_pro: str, price_team: str) -> Optional[Tuple[int,str,str]]:
    """Update local subscription table from a Stripe subscription object."""
    if not workspace_id:
        # Try metadata fallback
        md = (sub.get("metadata") or {})
        try:
            workspace_id = int(md.get("workspace_id", "0"))
        except Exception:
            workspace_id = 0
    if not workspace_id:
        return None

    items = ((sub.get("items") or {}).get("data") or [])
    price_ids = set()
    for it in items:
        price = (it.get("price") or {}).get("id") or (it.get("plan") or {}).get("id")
        if price:
            price_ids.add(price)

    plan = _plan_from_price_ids(price_ids, price_pro, price_team)
    status = (sub.get("status") or "active").lower()
    customer = sub.get("customer")
    sub_id = sub.get("id")
    cpe = sub.get("current_period_end")
    if isinstance(cpe, (int, float)):
        cpe = int(cpe)
    set_plan(
        int(workspace_id),
        plan=plan,
        status=status,
        stripe_customer_id=str(customer) if customer else None,
        stripe_subscription_id=str(sub_id) if sub_id else None,
        current_period_end=cpe,
    )
    return (int(workspace_id), plan, status)

def process_event(event: Dict[str, Any], price_pro: str, price_team: str) -> Optional[Tuple[int,str,str]]:
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    # Checkout completed: fetch subscription info embedded in session
    if etype == "checkout.session.completed":
        # The checkout session's subscription will be a string id; object contains metadata
        ws = None
        md = obj.get("metadata") or {}
        try:
            ws = int(md.get("workspace_id", "0"))
        except Exception:
            ws = None
        # We don't have full subscription fields here unless expanded; caller can fetch subscription separately.
        # We store minimal info; a subsequent subscription.updated event should fill details.
        sub_id = obj.get("subscription")
        cust_id = obj.get("customer")
        if ws and sub_id:
            # optimistic set; final plan will be set when subscription.updated arrives
            set_plan(ws, plan="pro", status="active", stripe_customer_id=str(cust_id) if cust_id else None, stripe_subscription_id=str(sub_id), current_period_end=None)
            return (ws, "pro", "active")
        return None

    if etype in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        ws = None
        md = obj.get("metadata") or {}
        try:
            ws = int(md.get("workspace_id", "0"))
        except Exception:
            ws = None
        # Deleted: downgrade to free (status canceled)
        if etype == "customer.subscription.deleted":
            if ws:
                set_plan(ws, plan="free", status="canceled", stripe_customer_id=str(obj.get("customer")) if obj.get("customer") else None,
                        stripe_subscription_id=str(obj.get("id")) if obj.get("id") else None,
                        current_period_end=int(obj.get("current_period_end") or 0) or None)
                return (ws, "free", "canceled")
            return None
        return upsert_from_subscription(obj, ws, price_pro, price_team)

    return None
