from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class FieldProvenance:
    value: Any
    source: str  # e.g. "manual", "RentCast", "Estated", "ATTOM"
    confidence: float = 0.6

def pick(manual: Optional[float], auto: Optional[float], auto_source: str) -> FieldProvenance:
    if manual is not None and float(manual) > 0:
        return FieldProvenance(value=float(manual), source="manual", confidence=0.9)
    if auto is not None and float(auto) > 0:
        return FieldProvenance(value=float(auto), source=auto_source, confidence=0.75)
    return FieldProvenance(value=None, source="missing", confidence=0.2)

def pack_provenance(price_p: FieldProvenance, rent_p: FieldProvenance, exp_p: FieldProvenance,
                    last_sale_price: Any, last_sale_date: Any, last_sale_source: str) -> Dict[str, Any]:
    return {
        "price": price_p.__dict__,
        "monthly_rent": rent_p.__dict__,
        "monthly_expenses": exp_p.__dict__,
        "last_sale_price": {"value": last_sale_price, "source": last_sale_source or "missing", "confidence": 0.7 if last_sale_price else 0.2},
        "last_sale_date": {"value": last_sale_date, "source": last_sale_source or "missing", "confidence": 0.7 if last_sale_date else 0.2},
    }
