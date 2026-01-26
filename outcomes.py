import json
import time
from typing import Dict, Any, Optional, List

from db import backend, connect, fetchall, fetchone, exec_commit, insert_returning_id
from irr_utils import irr

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn
    if b == "postgres":
        cur.execute("""CREATE TABLE IF NOT EXISTS outcomes(
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL,
            workspace_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            report_id BIGINT,
            address TEXT,
            url TEXT,
            actual_monthly_rent DOUBLE PRECISION,
            vacancy_days BIGINT,
            repair_costs DOUBLE PRECISION,
            hold_months BIGINT,
            resale_price DOUBLE PRECISION,
            appreciation_pct DOUBLE PRECISION,
            irr_realized DOUBLE PRECISION,
            notes TEXT,
            meta_json TEXT
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS outcomes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            workspace_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            report_id INTEGER,
            address TEXT,
            url TEXT,
            actual_monthly_rent REAL,
            vacancy_days INTEGER,
            repair_costs REAL,
            hold_months INTEGER,
            resale_price REAL,
            appreciation_pct REAL,
            irr_realized REAL,
            notes TEXT,
            meta_json TEXT
        )""")
    conn.commit()
    try: conn.close()
    except Exception: pass

def compute_outcome_metrics(purchase_price: float, monthly_rent: float, vacancy_days: int, repair_costs: float, hold_months: int, resale_price: float) -> Dict[str, Any]:
    purchase_price = float(purchase_price or 0.0)
    monthly_rent = float(monthly_rent or 0.0)
    vacancy_days = int(vacancy_days or 0)
    repair_costs = float(repair_costs or 0.0)
    hold_months = int(hold_months or 0)
    resale_price = float(resale_price or 0.0)

    vacancy_months = vacancy_days / 30.0
    effective_months = max(0.0, hold_months - vacancy_months)

    cashflows = [-purchase_price - repair_costs]
    for m in range(1, hold_months + 1):
        cashflows.append(monthly_rent if m <= effective_months else 0.0)
    if hold_months >= 1:
        cashflows[-1] += resale_price

    irr_m = irr(cashflows, guess=0.01)
    irr_a = None
    if irr_m is not None:
        irr_a = (1.0 + irr_m) ** 12 - 1.0

    appreciation_pct = None
    if purchase_price > 0 and resale_price > 0:
        appreciation_pct = (resale_price - purchase_price) / purchase_price * 100.0

    return {"cashflows": cashflows, "irr_realized": irr_a, "appreciation_pct": appreciation_pct}

def upsert_outcome(
    workspace_id: int,
    user_id: int,
    report_id: int = 0,
    address: str = "",
    url: str = "",
    actual_monthly_rent: float = 0.0,
    vacancy_days: int = 0,
    repair_costs: float = 0.0,
    hold_months: int = 0,
    resale_price: float = 0.0,
    purchase_price: float = 0.0,
    notes: str = "",
    meta: Optional[Dict[str, Any]] = None,
    outcome_id: Optional[int] = None,
) -> int:
    migrate()
    computed = compute_outcome_metrics(purchase_price, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price)
    irr_realized = computed.get("irr_realized")
    appreciation_pct = computed.get("appreciation_pct")
    meta_all = dict(meta or {})
    meta_all.setdefault("cashflows", computed.get("cashflows", []))

    if outcome_id:
        exec_commit("""UPDATE outcomes SET
            updated_at=?,
            report_id=?,
            address=?,
            url=?,
            actual_monthly_rent=?,
            vacancy_days=?,
            repair_costs=?,
            hold_months=?,
            resale_price=?,
            appreciation_pct=?,
            irr_realized=?,
            notes=?,
            meta_json=?
            WHERE id=? AND workspace_id=?""",
            (now(), int(report_id) if report_id else None, address, url, float(actual_monthly_rent), int(vacancy_days), float(repair_costs),
             int(hold_months), float(resale_price), (float(appreciation_pct) if appreciation_pct is not None else None),
             (float(irr_realized) if irr_realized is not None else None), (notes or "")[:800], json.dumps(meta_all), int(outcome_id), int(workspace_id)))
        return int(outcome_id)

    return insert_returning_id(
        "INSERT INTO outcomes(created_at, updated_at, workspace_id, user_id, report_id, address, url, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price, appreciation_pct, irr_realized, notes, meta_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (now(), now(), int(workspace_id), int(user_id), int(report_id) if report_id else None, address, url, float(actual_monthly_rent), int(vacancy_days),
         float(repair_costs), int(hold_months), float(resale_price),
         (float(appreciation_pct) if appreciation_pct is not None else None),
         (float(irr_realized) if irr_realized is not None else None),
         (notes or "")[:800], json.dumps(meta_all)),
        sql_postgres="INSERT INTO outcomes(created_at, updated_at, workspace_id, user_id, report_id, address, url, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price, appreciation_pct, irr_realized, notes, meta_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
    )

def list_outcomes(workspace_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("""SELECT id, created_at, updated_at, report_id, address, url, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price, appreciation_pct, irr_realized, notes
                      FROM outcomes WHERE workspace_id=? ORDER BY updated_at DESC LIMIT ?""",
                    (int(workspace_id), int(limit)))
    out = []
    for r in rows:
        out.append({
            "id": r[0], "created_at": r[1], "updated_at": r[2], "report_id": r[3] or 0,
            "address": r[4] or "", "url": r[5] or "",
            "actual_monthly_rent": r[6] or 0.0, "vacancy_days": r[7] or 0, "repair_costs": r[8] or 0.0,
            "hold_months": r[9] or 0, "resale_price": r[10] or 0.0, "appreciation_pct": r[11], "irr_realized": r[12],
            "notes": r[13] or ""
        })
    return out

def read_outcome(outcome_id: int, workspace_id: int) -> Dict[str, Any]:
    migrate()
    row = fetchone("""SELECT id, report_id, address, url, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price, appreciation_pct, irr_realized, notes, meta_json
                     FROM outcomes WHERE id=? AND workspace_id=?""", (int(outcome_id), int(workspace_id)))
    if not row:
        return {}
    try:
        meta = json.loads(row[12] or "{}")
    except Exception:
        meta = {}
    return {
        "id": row[0], "report_id": row[1] or 0, "address": row[2] or "", "url": row[3] or "",
        "actual_monthly_rent": row[4] or 0.0, "vacancy_days": row[5] or 0, "repair_costs": row[6] or 0.0,
        "hold_months": row[7] or 0, "resale_price": row[8] or 0.0, "appreciation_pct": row[9], "irr_realized": row[10],
        "notes": row[11] or "", "meta": meta
    }

import re
import difflib
from typing import Tuple

def _norm_addr(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9\s]", "", s)
    # common abbreviations
    s = s.replace(" street ", " st ").replace(" avenue ", " ave ").replace(" road ", " rd ").replace(" drive ", " dr ")
    s = s.replace(" boulevard ", " blvd ").replace(" lane ", " ln ").replace(" court ", " ct ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _addr_similarity(a: str, b: str) -> float:
    ta = set(_norm_addr(a).split())
    tb = set(_norm_addr(b).split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0

def find_best_report_match(workspace_id: int, address: str = "", url: str = "", limit: int = 800) -> Tuple[int, float]:
    """Return (report_id, confidence) where confidence in [0..1]."""
    migrate()
    address = (address or "").strip()
    url = (url or "").strip()

    if url:
        row = fetchone("SELECT id FROM reports WHERE workspace_id=? AND url=? ORDER BY created_at DESC LIMIT 1", (int(workspace_id), url))
        if row:
            return int(row[0]), 0.99

    rows = fetchall("SELECT id, address, url FROM reports WHERE workspace_id=? ORDER BY created_at DESC LIMIT ?",
                    (int(workspace_id), int(limit)))
    best_id, best_score = 0, 0.0
    na = _norm_addr(address)
    hn = _house_number(address)
    for rid, raddr, rurl in rows:
        token_sim = _addr_similarity(na, raddr or "")
        seq_sim = _seq_similarity(na, raddr or "")
        sim = 0.65 * token_sim + 0.35 * seq_sim
        # strong bonus if house number matches
        if hn and hn == _house_number(raddr or ""):
            sim = min(1.0, sim + 0.12)
        # bonus if URL looks similar
        if url and rurl and (url.split("?")[0] in rurl or rurl.split("?")[0] in url):
            sim = min(1.0, sim + 0.15)
        if sim > best_score:
            best_score = sim
            best_id = int(rid)

    if best_score >= 0.85:
        conf = 0.95
    elif best_score >= 0.70:
        conf = 0.85
    elif best_score >= 0.55:
        conf = 0.70
    elif best_score >= 0.40:
        conf = 0.55
    else:
        conf = 0.0
    return best_id, conf

def list_unlinked_outcomes(workspace_id: int, limit: int = 300) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("""SELECT id, updated_at, address, url, actual_monthly_rent, vacancy_days, repair_costs, hold_months, resale_price, irr_realized
                      FROM outcomes WHERE workspace_id=? AND (report_id IS NULL OR report_id=0) ORDER BY updated_at DESC LIMIT ?""",
                    (int(workspace_id), int(limit)))
    out = []
    for r in rows:
        out.append({
            "id": r[0], "updated_at": r[1], "address": r[2] or "", "url": r[3] or "",
            "actual_monthly_rent": r[4] or 0.0, "vacancy_days": r[5] or 0, "repair_costs": r[6] or 0.0,
            "hold_months": r[7] or 0, "resale_price": r[8] or 0.0, "irr_realized": r[9]
        })
    return out

def link_outcome_to_report(workspace_id: int, outcome_id: int, report_id: int) -> None:
    migrate()
    exec_commit("UPDATE outcomes SET report_id=?, updated_at=? WHERE id=? AND workspace_id=?",
                (int(report_id), now(), int(outcome_id), int(workspace_id)))

def _seq_similarity(a: str, b: str) -> float:
    a = _norm_addr(a)
    b = _norm_addr(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()

def _house_number(s: str) -> str:
    s = _norm_addr(s)
    m = re.match(r"^(\d+)", s)
    return m.group(1) if m else ""
