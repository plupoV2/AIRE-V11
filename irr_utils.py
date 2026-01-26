import math
from typing import List, Optional

def irr(cashflows: List[float], guess: float = 0.1) -> Optional[float]:
    """Compute IRR using Newton-Raphson. Returns decimal (0.12 = 12%)."""
    if not cashflows or len(cashflows) < 2:
        return None

    def npv(rate: float) -> float:
        total = 0.0
        for t, cf in enumerate(cashflows):
            total += cf / ((1.0 + rate) ** t)
        return total

    def d_npv(rate: float) -> float:
        total = 0.0
        for t, cf in enumerate(cashflows[1:], start=1):
            total -= t * cf / ((1.0 + rate) ** (t + 1))
        return total

    r = guess
    for _ in range(50):
        f = npv(r)
        df = d_npv(r)
        if abs(df) < 1e-12:
            break
        nr = r - f / df
        if not math.isfinite(nr):
            break
        if abs(nr - r) < 1e-8:
            r = nr
            break
        r = nr
        r = max(-0.95, min(10.0, r))
    return r if math.isfinite(r) else None
