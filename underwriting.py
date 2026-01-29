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
    grade_detail: str
    verdict: str
    confidence: float
    metrics: Dict[str, Any]
    flags: List[str]
    rationale: List[str]
    score_base: float
    score_ai: float
    ai_weight: float
    ai_meta: Dict[str, Any]
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

def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"

def score_to_grade_detail(score: float) -> str:
    letter = score_to_grade(score)
    if letter == "A":
        if score >= 97:
            return "A+"
        if score >= 93:
            return "A"
        return "A-"
    if letter == "B":
        if score >= 87:
            return "B+"
        if score >= 83:
            return "B"
        return "B-"
    if letter == "C":
        if score >= 77:
            return "C+"
        if score >= 73:
            return "C"
        return "C-"
    if letter == "D":
        if score >= 67:
            return "D+"
        if score >= 63:
            return "D"
        return "D-"
    if score >= 55:
        return "F+"
    if score >= 50:
        return "F"
    return "F-"

def verdict_from_score(score: float) -> str:
    if score >= 90:
        return "BUY"
    if score >= 80:
        return "BUY (Selective)"
    if score >= 70:
        return "WATCH / NEGOTIATE"
    if score >= 60:
        return "PASS (Most cases)"
    return "AVOID"

def score_and_grade(i: DealInputs, m: Dict[str, Any]) -> Tuple[float, float, List[str], List[str]]:
    # confidence: how complete the core underwriting data is
    core = 0
    if i.price is not None: core += 1
    if i.monthly_rent is not None: core += 1
    if i.monthly_expenses is not None: core += 1
    if i.last_sale_price is not None: core += 1
    conf = min(1.0, 0.25 + 0.18*core)

    flags: List[str] = []
    reasons: List[str] = ["Base underwriting starts at 50/100."]
    score = 50.0

    cap = m.get("CapRate")
    coc = m.get("CoC")
    dscr = m.get("DSCR")
    irr_v = m.get("IRR")
    chg = m.get("PriceChangePct")

    # Yield
    if cap is not None:
        if cap >= 0.08:
            score += 12
            reasons.append(f"Cap rate {cap:.2%} ≥ 8% adds +12.")
        elif cap >= 0.06:
            score += 7
            reasons.append(f"Cap rate {cap:.2%} ≥ 6% adds +7.")
        elif cap >= 0.045:
            score += 2
            reasons.append(f"Cap rate {cap:.2%} ≥ 4.5% adds +2.")
        else:
            score -= 6
            flags.append("Low cap rate")
            reasons.append(f"Cap rate {cap:.2%} < 4.5% subtracts -6.")
    else:
        flags.append("Missing cap-rate inputs")
        reasons.append("Cap rate unavailable (missing price/rent/expenses).")

    if coc is not None:
        if coc >= 0.12:
            score += 10
            reasons.append(f"Cash-on-cash {coc:.2%} ≥ 12% adds +10.")
        elif coc >= 0.08:
            score += 6
            reasons.append(f"Cash-on-cash {coc:.2%} ≥ 8% adds +6.")
        elif coc >= 0.05:
            score += 2
            reasons.append(f"Cash-on-cash {coc:.2%} ≥ 5% adds +2.")
        else:
            score -= 6
            flags.append("Low cash-on-cash")
            reasons.append(f"Cash-on-cash {coc:.2%} < 5% subtracts -6.")
    else:
        flags.append("Missing CoC inputs")
        reasons.append("Cash-on-cash unavailable (missing rent/expenses/price).")

    if dscr is not None:
        if dscr >= 1.35:
            score += 8
            reasons.append(f"DSCR {dscr:.2f} ≥ 1.35 adds +8.")
        elif dscr >= 1.20:
            score += 5
            reasons.append(f"DSCR {dscr:.2f} ≥ 1.20 adds +5.")
        elif dscr >= 1.05:
            score += 1
            reasons.append(f"DSCR {dscr:.2f} ≥ 1.05 adds +1.")
        else:
            score -= 12
            flags.append("DSCR risk")
            reasons.append(f"DSCR {dscr:.2f} < 1.05 subtracts -12.")
    else:
        flags.append("Missing DSCR inputs")
        reasons.append("DSCR unavailable (missing NOI or debt service).")

    # Forward returns
    if irr_v is not None:
        if irr_v >= 0.18:
            score += 10
            reasons.append(f"IRR {irr_v:.2%} ≥ 18% adds +10.")
        elif irr_v >= 0.14:
            score += 7
            reasons.append(f"IRR {irr_v:.2%} ≥ 14% adds +7.")
        elif irr_v >= 0.10:
            score += 3
            reasons.append(f"IRR {irr_v:.2%} ≥ 10% adds +3.")
        else:
            score -= 7
            flags.append("Low IRR")
            reasons.append(f"IRR {irr_v:.2%} < 10% subtracts -7.")
    else:
        flags.append("IRR unavailable (needs price + rent + expenses)")
        reasons.append("IRR unavailable (needs price + rent + expenses).")

    # Price momentum from last sale
    if chg is not None:
        if chg <= -0.05:
            score += 3
            flags.append("Discount vs last sale")
            reasons.append(f"Price is {abs(chg):.1%} below last sale adds +3.")
        elif chg >= 0.25:
            score -= 6
            flags.append("Big run-up vs last sale")
            reasons.append(f"Price is {chg:.1%} above last sale subtracts -6.")

    score = max(0.0, min(100.0, score))
    reasons.append(f"Base underwriting score: {score:.1f}/100.")

    return score, conf, flags, reasons

def _ai_payload(i: DealInputs, m: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    price = i.price or 0.0
    rent = i.monthly_rent or 0.0
    annual_rent = rent * 12.0 if rent else 0.0
    rent_to_price = (annual_rent / price) if (price and annual_rent) else None
    price_to_rent = (price / annual_rent) if (price and annual_rent) else None
    ai_inputs = {
        "cap_rate": m.get("CapRate"),
        "cash_on_cash": m.get("CoC"),
        "dscr": m.get("DSCR"),
        "rent_to_price": rent_to_price,
        "price_to_rent": price_to_rent,
    }
    present = sum(1 for v in ai_inputs.values() if v is not None)
    completeness = present / max(1, len(ai_inputs))
    return {
        "underwriting": {
            "cap_rate": ai_inputs["cap_rate"],
            "cash_on_cash": ai_inputs["cash_on_cash"],
            "dscr": ai_inputs["dscr"],
            "rent_to_price": ai_inputs["rent_to_price"],
            "price_to_rent": ai_inputs["price_to_rent"],
        },
        "market": {},
        "risk": {},
    }, completeness

def _driver_label(feature: str) -> str:
    labels = {
        "cap_rate": "Cap rate",
        "cash_on_cash": "Cash-on-cash",
        "dscr": "DSCR",
        "rent_to_price": "Rent-to-price",
        "price_to_rent": "Price-to-rent",
        "year_built_norm": "Year built",
        "dom_norm": "Days on market",
        "crime_norm": "Crime",
        "school_norm": "School score",
        "market_growth_norm": "Market growth",
        "volatility_norm": "Volatility",
        "liquidity_norm": "Liquidity",
    }
    return labels.get(feature, feature.replace("_", " ").title())

def run_underwriting(i: DealInputs) -> DealOutputs:
    m = compute_metrics(i)
    base_score, conf, flags, reasons = score_and_grade(i, m)
    ai_payload, ai_completeness = _ai_payload(i, m)
    ai_grade, ai_score, ai_conf, ai_meta = grade_with_model(ai_payload)
    ai_weight = 0.0 if ai_completeness <= 0 else min(0.35, 0.15 + 0.20 * ai_completeness)
    score = base_score if ai_weight <= 0 else (base_score * (1 - ai_weight) + ai_score * ai_weight)
    score = max(0.0, min(100.0, float(score)))
    grade = score_to_grade(score)
    grade_detail = score_to_grade_detail(score)
    verdict = verdict_from_score(score)
    reasons.append(
        f"AI score {ai_score:.1f}/100 blended at {ai_weight:.0%} weight → final {score:.1f}/100."
    )
    ai_drivers = []
    for item in ai_meta.get("top_drivers", [])[:5]:
        feat = _driver_label(str(item.get("feature")))
        contrib = float(item.get("contribution") or 0.0)
        direction = "supports" if contrib >= 0 else "pressures"
        ai_drivers.append(f"AI driver: {feat} {direction} the grade ({contrib:+.2f}).")
    reasons.extend(ai_drivers)
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
        "confidence": conf,
        "grade_detail": grade_detail,
        "score_base": base_score,
        "score_ai": ai_score,
        "ai_weight": ai_weight,
        "rationale": reasons,
        "ai_meta": ai_meta,
    }
    return DealOutputs(
        score=score,
        grade=grade,
        grade_detail=grade_detail,
        verdict=verdict,
        confidence=conf,
        metrics=m,
        flags=flags,
        rationale=reasons,
        score_base=base_score,
        score_ai=ai_score,
        ai_weight=ai_weight,
        ai_meta=ai_meta,
        narrative_seed=seed,
    )

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
