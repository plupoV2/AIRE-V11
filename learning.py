import math
import random
from typing import Dict, Any, List, Tuple, Optional

FEATURE_KEYS = [
    "cap_rate",
    "cash_on_cash",
    "dscr",
    "rent_to_price",
    "price_to_rent",
    "year_built_norm",
    "dom_norm",
    "crime_norm",
    "school_norm",
    "market_growth_norm",
    "volatility_norm",
    "liquidity_norm",
]

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _safe(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)

def _norm01(x: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.5
    return _clip((x - lo) / (hi - lo), 0.0, 1.0)

def extract_features(payload: Dict[str, Any]) -> Dict[str, float]:
    u = payload.get("underwriting", {}) or {}
    m = payload.get("market", {}) or {}
    r = payload.get("risk", {}) or {}

    cap_rate = _safe(u.get("cap_rate"))
    coc = _safe(u.get("cash_on_cash"))
    dscr = _safe(u.get("dscr"))
    rtp = _safe(u.get("rent_to_price"))
    ptr = _safe(u.get("price_to_rent"))

    year_built = _safe(u.get("year_built"), 1980)
    year_built_norm = _norm01(year_built, 1900, 2025)

    dom = _safe(m.get("days_on_market"), 45)
    dom_norm = 1.0 - _norm01(dom, 0, 180)

    crime = _safe(r.get("crime_index"), 50)
    crime_norm = 1.0 - _norm01(crime, 0, 100)

    school = _safe(r.get("school_score"), 5)
    school_norm = _norm01(school, 0, 10)

    growth = _safe(m.get("yoy_growth_pct"), 3.0)
    market_growth_norm = _norm01(growth, -10, 20)

    vol = _safe(m.get("volatility_pct"), 8.0)
    volatility_norm = 1.0 - _norm01(vol, 0, 30)

    liq = _safe(m.get("liquidity_score"), 0.5)
    liquidity_norm = _clip(liq, 0.0, 1.0)

    return {
        "cap_rate": _clip(cap_rate, -0.5, 0.5),
        "cash_on_cash": _clip(coc, -1.0, 2.0),
        "dscr": _clip(dscr, 0.0, 5.0),
        "rent_to_price": _clip(rtp, 0.0, 0.05),
        "price_to_rent": _clip(ptr, 0.0, 50.0),
        "year_built_norm": year_built_norm,
        "dom_norm": dom_norm,
        "crime_norm": crime_norm,
        "school_norm": school_norm,
        "market_growth_norm": market_growth_norm,
        "volatility_norm": volatility_norm,
        "liquidity_norm": liquidity_norm,
    }

def default_weights() -> Dict[str, float]:
    return {
        "_bias": -0.25,
        "cap_rate": 2.3,
        "cash_on_cash": 1.2,
        "dscr": 0.8,
        "rent_to_price": 18.0,
        "price_to_rent": -0.06,
        "year_built_norm": 0.15,
        "dom_norm": 0.25,
        "crime_norm": 0.35,
        "school_norm": 0.25,
        "market_growth_norm": 0.30,
        "volatility_norm": 0.20,
        "liquidity_norm": 0.20,
    }

def sigmoid(z: float) -> float:
    z = max(-20.0, min(20.0, z))
    return 1.0 / (1.0 + math.exp(-z))

def predict_proba(weights: Dict[str, float], features: Dict[str, float]) -> float:
    z = float(weights.get("_bias", 0.0))
    for k, v in features.items():
        z += float(weights.get(k, 0.0)) * float(v)
    return sigmoid(z)

def proba_to_score(p: float) -> float:
    return float(_clip(p * 100.0, 0.0, 100.0))

def score_to_grade(score: float) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"

def explain(weights: Dict[str, float], features: Dict[str, float], top_k: int = 6):
    contribs = []
    for k, v in features.items():
        contribs.append((k, float(weights.get(k, 0.0)) * float(v)))
    contribs.sort(key=lambda x: abs(x[1]), reverse=True)
    return contribs[:top_k]

def train_sgd(rows: List[Tuple[Dict[str, float], int]], start_weights: Optional[Dict[str, float]] = None, lr: float = 0.05, l2: float = 0.001, epochs: int = 12) -> Dict[str, float]:
    w = dict(start_weights or default_weights())
    for k in FEATURE_KEYS:
        w.setdefault(k, 0.0)
    w.setdefault("_bias", 0.0)
    for _ in range(max(1, int(epochs))):
        for feats, y in rows:
            p = predict_proba(w, feats)
            err = (float(y) - p)
            w["_bias"] += lr * err
            for k, x in feats.items():
                w[k] += lr * (err * float(x) - l2 * float(w.get(k, 0.0)))
    return w

def eval_simple(rows: List[Tuple[Dict[str, float], int]], weights: Dict[str, float]) -> Dict[str, float]:
    if not rows:
        return {"n": 0, "acc": 0.0}
    correct = 0
    for feats, y in rows:
        p = predict_proba(weights, feats)
        pred = 1 if p >= 0.5 else 0
        correct += 1 if pred == int(y) else 0
    return {"n": len(rows), "acc": correct/len(rows)}

def label_from_outcome(outcome: Dict[str, Any], irr_threshold: float = 0.12, max_vacancy_days: int = 60) -> int:
    """Convert ground-truth outcome to a binary label used for training.
    1 = good investment (meets IRR threshold AND vacancy acceptable), else 0.
    """
    irr_realized = outcome.get("irr_realized")
    vacancy = outcome.get("vacancy_days") or 0
    try:
        irr_realized = float(irr_realized) if irr_realized is not None else None
    except Exception:
        irr_realized = None
    try:
        vacancy = int(vacancy)
    except Exception:
        vacancy = 0
    if irr_realized is None:
        return 0
    return 1 if (irr_realized >= float(irr_threshold) and vacancy <= int(max_vacancy_days)) else 0

def feature_completeness(features: Dict[str, float]) -> float:
    """Rough completeness score in [0..1] based on non-default-ish values."""
    if not features:
        return 0.0
    present = 0
    for k in FEATURE_KEYS:
        if k in features and features[k] is not None:
            present += 1
    return present / max(1, len(FEATURE_KEYS))

def eval_metrics(rows: List[Tuple[Dict[str, float], int]], weights: Dict[str, float]) -> Dict[str, float]:
    """Compute simple classification metrics (no external deps)."""
    if not rows:
        return {"n": 0, "acc": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
    tp=fp=tn=fn=0
    for feats, y in rows:
        p = predict_proba(weights, feats)
        pred = 1 if p >= 0.5 else 0
        if pred==1 and y==1: tp += 1
        elif pred==1 and y==0: fp += 1
        elif pred==0 and y==0: tn += 1
        elif pred==0 and y==1: fn += 1
    acc = (tp+tn)/max(1,(tp+tn+fp+fn))
    precision = tp/max(1,(tp+fp))
    recall = tp/max(1,(tp+fn))
    f1 = 0.0 if (precision+recall)==0 else 2*precision*recall/(precision+recall)
    return {"n": len(rows), "acc": acc, "precision": precision, "recall": recall, "f1": f1}

def train_val_split(rows: List[Tuple[Dict[str, float], int]], val_frac: float = 0.2, seed: int = 7):
    rows2 = list(rows)
    rnd = random.Random(seed)
    rnd.shuffle(rows2)
    n = len(rows2)
    k = int(max(1, n*val_frac))
    val = rows2[:k]
    train = rows2[k:]
    return train, val
