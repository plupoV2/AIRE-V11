import time
from db import backend, connect, exec_commit, fetchone
from typing import Dict, Any, Optional

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn

    cur.execute("""CREATE TABLE IF NOT EXISTS subscriptions(
        workspace_id INTEGER PRIMARY KEY,
        plan TEXT NOT NULL DEFAULT 'free',
        status TEXT NOT NULL DEFAULT 'active',
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        current_period_end INTEGER,
        updated_at INTEGER NOT NULL
    )""" if b == "sqlite" else """CREATE TABLE IF NOT EXISTS subscriptions(
        workspace_id BIGINT PRIMARY KEY,
        plan TEXT NOT NULL DEFAULT 'free',
        status TEXT NOT NULL DEFAULT 'active',
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        current_period_end BIGINT,
        updated_at BIGINT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS billing_profile(
        workspace_id INTEGER PRIMARY KEY,
        company_name TEXT,
        billing_email TEXT,
        tax_id TEXT,
        address_json TEXT,
        updated_at INTEGER NOT NULL
    )""" if b == "sqlite" else """CREATE TABLE IF NOT EXISTS billing_profile(
        workspace_id BIGINT PRIMARY KEY,
        company_name TEXT,
        billing_email TEXT,
        tax_id TEXT,
        address_json TEXT,
        updated_at BIGINT NOT NULL
    )""")

    conn.commit()
    try:
        conn.close()
    except Exception:
        pass

def get_subscription(workspace_id: int) -> Dict[str, Any]:
    migrate()
    row = fetchone("SELECT plan, status, stripe_customer_id, stripe_subscription_id, current_period_end FROM subscriptions WHERE workspace_id=?", (int(workspace_id),))
    if not row:
        return {"plan": "free", "status": "active"}
    return {"plan": row[0], "status": row[1], "stripe_customer_id": row[2], "stripe_subscription_id": row[3], "current_period_end": row[4]}

def set_plan(workspace_id: int, plan: str, status: str="active",
             stripe_customer_id: Optional[str]=None, stripe_subscription_id: Optional[str]=None,
             current_period_end: Optional[int]=None) -> None:
    migrate()
    exec_commit("""INSERT INTO subscriptions(workspace_id, plan, status, stripe_customer_id, stripe_subscription_id, current_period_end, updated_at)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(workspace_id) DO UPDATE SET
                      plan=excluded.plan,
                      status=excluded.status,
                      stripe_customer_id=excluded.stripe_customer_id,
                      stripe_subscription_id=excluded.stripe_subscription_id,
                      current_period_end=excluded.current_period_end,
                      updated_at=excluded.updated_at""",
                 (int(workspace_id), plan, status, stripe_customer_id, stripe_subscription_id, current_period_end, now()))

def plan_limits(plan: str) -> Dict[str, int]:
    # daily limits (can be tuned later)
    plan = (plan or "free").lower()
    if plan == "team":
        return {"grades_per_day": 500, "batch_rows": 500, "api_calls_per_day": 3000}
    if plan == "pro":
        return {"grades_per_day": 100, "batch_rows": 200, "api_calls_per_day": 800}
    return {"grades_per_day": 5, "batch_rows": 25, "api_calls_per_day": 0}

ACTIVE_STATUSES = {"active", "trialing"}

def effective_plan(sub: Dict[str, Any]) -> str:
    """Return the plan that should be enforced. If subscription isn't active/trialing, enforce free."""
    status = (sub.get("status") or "active").lower()
    plan = (sub.get("plan") or "free").lower()
    if status in ACTIVE_STATUSES:
        return plan
    # If not active, enforce free (UI can still show the stored plan + status)
    return "free"

def get_billing_profile(workspace_id: int) -> Dict[str, Any]:
    migrate()
    row = fetchone("SELECT company_name, billing_email, tax_id, address_json FROM billing_profile WHERE workspace_id=?",
                   (int(workspace_id),))
    if not row:
        return {"company_name": "", "billing_email": "", "tax_id": "", "address": {}}
    import json as _json
    try:
        addr = _json.loads(row[3] or "{}")
    except Exception:
        addr = {}
    return {"company_name": row[0] or "", "billing_email": row[1] or "", "tax_id": row[2] or "", "address": addr}

def upsert_billing_profile(workspace_id: int, company_name: str = "", billing_email: str = "", tax_id: str = "", address: Optional[Dict[str, Any]] = None) -> None:
    migrate()
    import json as _json
    addr_json = _json.dumps(address or {})
    exec_commit("""INSERT INTO billing_profile(workspace_id, company_name, billing_email, tax_id, address_json, updated_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(workspace_id) DO UPDATE SET
                      company_name=excluded.company_name,
                      billing_email=excluded.billing_email,
                      tax_id=excluded.tax_id,
                      address_json=excluded.address_json,
                      updated_at=excluded.updated_at""",

               (int(workspace_id), (company_name or "")[:120], (billing_email or "")[:120], (tax_id or "")[:80], addr_json, now()))
