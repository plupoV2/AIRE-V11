from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import math

@dataclass
class DealInputs:
    address: str
    listing_url: str = ""
    price: Optional[float] = None
    monthly_rent: Optional[float] = None
    monthly_expenses: Optional[float] = None
    vacancy_rate: float = 0.08

    down_payment_pct: float = 20.0
    interest_rate_pct: float = 7.25
    term_years: int = 30

    last_sale_price: Optional[float] = None
    last_sale_date: Optional[str] = None

    # Forward model assumptions
    hold_years: int = 7
    rent_growth: float = 0.03
    expense_growth: float = 0.03
    appreciation: float = 0.03
    sale_cost_pct: float = 0.07
    use_exit_cap: bool = False
    exit_cap_rate: float = 0.065  # decimal

@dataclass
class DealOutputs:
    score: float
    grade: str
    verdict: str
    confidence: float
    metrics: Dict[str, Any]
    flags: List[str]
    narrative_seed: Dict[str, Any]

def monthly_payment(principal: float, annual_rate: float, years: int) -> Optional[float]:
    try:
        if principal <= 0 or years <= 0:
            return None
        r = max(0.0, annual_rate) / 12.0
        n = years * 12
        if r == 0:
            return principal / n
        return principal * (r * (1 + r) ** n) / (((1 + r) ** n) - 1)
    except Exception:
        return None

def irr(cashflows: List[float]) -> Optional[float]:
    """Robust IRR solver (no numpy). Returns periodic IRR or None."""
    if not cashflows or len(cashflows) < 2:
        return None
    if not (any(cf < 0 for cf in cashflows) and any(cf > 0 for cf in cashflows)):
        return None

    def npv(rate: float) -> float:
        total = 0.0
        for t, cf in enumerate(cashflows):
            total += cf / ((1 + rate) ** t)
        return total

    lo, hi = -0.95, 3.0
    f_lo, f_hi = npv(lo), npv(hi)

    # Expand hi if needed
    tries = 0
    while f_lo * f_hi > 0 and tries < 15:
        hi *= 1.5
        f_hi = npv(hi)
        tries += 1
        if hi > 100:
            break

    if f_lo * f_hi > 0:
        return None

    for _ in range(120):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-7:
            return mid
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0

def npv(discount: float, cashflows: List[float]) -> Optional[float]:
    try:
        total = 0.0
        for t, cf in enumerate(cashflows):
            total += cf / ((1 + discount) ** t)
        return total
    except Exception:
        return None

def project_cashflows(i: DealInputs) -> Dict[str, Any]:
    if i.price is None:
        return {"cashflows": [], "irr": None, "npv": None, "exit_value": None, "noi0": None, "debt0": None}

    vac = max(0.0, min(0.50, float(i.vacancy_rate or 0.0)))
    rent0 = float(i.monthly_rent or 0.0) * 12.0
    exp0 = float(i.monthly_expenses or 0.0) * 12.0
    noi0 = (rent0 * (1 - vac)) - exp0

    down = max(0.0, min(1.0, i.down_payment_pct / 100.0))
    equity0 = i.price * down
    loan = i.price * (1 - down)

    debt_m = monthly_payment(loan, i.interest_rate_pct / 100.0, int(i.term_years)) if loan > 0 else None
    debt0 = (debt_m or 0.0) * 12.0

    cashflows = [-equity0]
    noi = noi0
    for yr in range(1, int(i.hold_years) + 1):
        if yr > 1:
            noi *= (1 + float(i.rent_growth))
            # conservative tilt to account for expense creep beyond explicit expenses
            noi -= abs(noi) * float(i.expense_growth) * 0.35
        cashflows.append(noi - debt0)

    if i.use_exit_cap and i.exit_cap_rate and i.exit_cap_rate > 0:
        exit_value = noi / float(i.exit_cap_rate)
    else:
        exit_value = i.price * ((1 + float(i.appreciation)) ** int(i.hold_years))

    net_sale = exit_value * (1 - float(i.sale_cost_pct))
    if loan > 0:
        net_sale -= loan
    cashflows[-1] += net_sale

    return {
        "cashflows": cashflows,
        "irr": irr(cashflows),
        "npv": npv(0.10, cashflows),
        "exit_value": exit_value,
        "noi0": noi0,
        "debt0": debt0,
    }

def compute_metrics(i: DealInputs) -> Dict[str, Any]:
    m: Dict[str, Any] = {}

    if i.price is not None and i.monthly_rent is not None and i.monthly_expenses is not None:
        vac = max(0.0, min(0.50, float(i.vacancy_rate or 0.0)))
        gross = i.monthly_rent * 12.0
        exp = i.monthly_expenses * 12.0
        noi = (gross * (1 - vac)) - exp
        m["NOI"] = noi
        m["CapRate"] = (noi / i.price) if i.price else None

        down = max(0.0, min(1.0, i.down_payment_pct/100.0))
        loan = i.price * (1 - down)
        pay = monthly_payment(loan, i.interest_rate_pct/100.0, int(i.term_years)) if loan > 0 else 0.0
        m["LoanPaymentMonthly"] = pay
        cf_m = (gross*(1-vac)/12.0) - i.monthly_expenses - (pay or 0.0)
        m["CashFlowMonthly"] = cf_m
        equity = i.price * down if i.price else None
        m["CoC"] = (cf_m*12.0/equity) if equity and equity > 0 else None
        m["DSCR"] = (noi / ((pay or 0.0)*12.0)) if pay and pay > 0 else None

    if i.price is not None and i.last_sale_price is not None and i.last_sale_price > 0:
        m["PriceChangePct"] = (i.price - i.last_sale_price) / i.last_sale_price
        m["PriceChangeAbs"] = i.price - i.last_sale_price

    model = project_cashflows(i)
    m["IRR"] = model.get("irr")
    m["NPV10"] = model.get("npv")
    m["ExitValue"] = model.get("exit_value")
    m["Cashflows"] = model.get("cashflows")
    m["NOI0"] = model.get("noi0")
    m["DebtAnnual"] = model.get("debt0")
    return m

def score_and_grade(i: DealInputs, m: Dict[str, Any]) -> Tuple[float, float, List[str], str, str]:
    # confidence: how complete the core underwriting data is
    core = 0
    if i.price is not None: core += 1
    if i.monthly_rent is not None: core += 1
    if i.monthly_expenses is not None: core += 1
    if i.last_sale_price is not None: core += 1
    conf = min(1.0, 0.25 + 0.18*core)

    flags: List[str] = []
    score = 50.0

    cap = m.get("CapRate")
    coc = m.get("CoC")
    dscr = m.get("DSCR")
    irr_v = m.get("IRR")
    chg = m.get("PriceChangePct")

    # Yield
    if cap is not None:
        if cap >= 0.08: score += 12
        elif cap >= 0.06: score += 7
        elif cap >= 0.045: score += 2
        else: score -= 6; flags.append("Low cap rate")
    else:
        flags.append("Missing cap-rate inputs")

    if coc is not None:
        if coc >= 0.12: score += 10
        elif coc >= 0.08: score += 6
        elif coc >= 0.05: score += 2
        else: score -= 6; flags.append("Low cash-on-cash")
    else:
        flags.append("Missing CoC inputs")

    if dscr is not None:
        if dscr >= 1.35: score += 8
        elif dscr >= 1.20: score += 5
        elif dscr >= 1.05: score += 1
        else: score -= 12; flags.append("DSCR risk")
    else:
        flags.append("Missing DSCR inputs")

    # Forward returns
    if irr_v is not None:
        if irr_v >= 0.18: score += 10
        elif irr_v >= 0.14: score += 7
        elif irr_v >= 0.10: score += 3
        else: score -= 7; flags.append("Low IRR")
    else:
        flags.append("IRR unavailable (needs price + rent + expenses)")

    # Price momentum from last sale
    if chg is not None:
        if chg <= -0.05:
            score += 3; flags.append("Discount vs last sale")
        elif chg >= 0.25:
            score -= 6; flags.append("Big run-up vs last sale")

    score = max(0.0, min(100.0, score))

    if score >= 90: grade, verdict = "A", "BUY"
    elif score >= 80: grade, verdict = "B", "BUY (Selective)"
    elif score >= 70: grade, verdict = "C", "WATCH / NEGOTIATE"
    elif score >= 60: grade, verdict = "D", "PASS (Most cases)"
    else: grade, verdict = "F", "AVOID"

    return score, conf, flags, grade, verdict

def run_underwriting(i: DealInputs) -> DealOutputs:
    m = compute_metrics(i)
    score, conf, flags, grade, verdict = score_and_grade(i, m)
    seed = {
        "address": i.address,
        "price": i.price,
        "rent": i.monthly_rent,
        "expenses": i.monthly_expenses,
        "vacancy": i.vacancy_rate,
        "cap_rate": m.get("CapRate"),
        "coc": m.get("CoC"),
        "dscr": m.get("DSCR"),
        "irr": m.get("IRR"),
        "npv10": m.get("NPV10"),
        "last_sale_price": i.last_sale_price,
        "last_sale_date": i.last_sale_date,
        "price_change_pct": m.get("PriceChangePct"),
        "flags": flags,
        "grade": grade,
        "score": score,
        "confidence": conf
    }
    return DealOutputs(score=score, grade=grade, verdict=verdict, confidence=conf, metrics=m, flags=flags, narrative_seed=seed)

def grade_with_model(payload: Dict[str, Any], workspace_id: int = 0) -> Tuple[str, float, float, Dict[str, Any]]:
    """Enterprise-safe scorer.
    Uses baseline weights by default; uses ACTIVE workspace model if present.
    Returns explainability + model metadata for auditing.
    """
    features = learning.extract_features(payload)
    model = get_active_model(int(workspace_id)) if workspace_id else None
    weights = (model.get("weights") if model else None) or learning.default_weights()
    p = learning.predict_proba(weights, features)
    score = learning.proba_to_score(p)
    grade = learning.score_to_grade(score)
    drivers = learning.explain(weights, features, top_k=6)
    dq = learning.feature_completeness(features)
    meta = {
        "data_quality": float(dq),
        "model": {
            "name": (model.get("name") if model else "baseline"),
            "id": (model.get("id") if model else None),
            "status": (model.get("status") if model else "baseline"),
        },
        "features": features,
        "top_drivers": [{"feature": k, "contribution": float(v)} for k, v in drivers],
    }
    base_conf = float(min(0.95, max(0.50, abs(p - 0.5) * 2.0)))
    confidence = float(max(0.40, min(0.95, base_conf * (0.75 + 0.25 * dq))))
    return grade, float(score), confidence, meta
