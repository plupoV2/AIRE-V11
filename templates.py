from typing import Dict, Any

BUILTIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
  "Long-Term Rental (LTR)": {
    "vacancy_rate": 0.08,
    "down_payment_pct": 20.0,
    "interest_rate_pct": 7.25,
    "term_years": 30,
    "hold_years": 7,
    "rent_growth": 0.03,
    "expense_growth": 0.03,
    "appreciation": 0.03,
    "sale_cost_pct": 0.07,
    "use_exit_cap": False,
    "exit_cap_rate": 0.065,
    "defaults": {
      "expense_rule": "simple",  # just a label for UI
      "monthly_expenses_pct_of_rent": 0.45,
    }
  },
  "BRRRR": {
    "vacancy_rate": 0.08,
    "down_payment_pct": 25.0,
    "interest_rate_pct": 7.75,
    "term_years": 30,
    "hold_years": 5,
    "rent_growth": 0.03,
    "expense_growth": 0.03,
    "appreciation": 0.03,
    "sale_cost_pct": 0.07,
    "use_exit_cap": False,
    "exit_cap_rate": 0.07,
    "defaults": {
      "expense_rule": "simple",
      "monthly_expenses_pct_of_rent": 0.48,
    }
  },
  "Flip": {
    "vacancy_rate": 0.00,
    "down_payment_pct": 35.0,
    "interest_rate_pct": 10.5,
    "term_years": 1,
    "hold_years": 1,
    "rent_growth": 0.00,
    "expense_growth": 0.00,
    "appreciation": 0.07,
    "sale_cost_pct": 0.09,
    "use_exit_cap": False,
    "exit_cap_rate": 0.0,
    "defaults": {
      "expense_rule": "flip",
      "monthly_expenses_pct_of_rent": 0.0,
    }
  },
  "Short-Term Rental (STR)": {
    "vacancy_rate": 0.18,
    "down_payment_pct": 25.0,
    "interest_rate_pct": 7.25,
    "term_years": 30,
    "hold_years": 7,
    "rent_growth": 0.04,
    "expense_growth": 0.035,
    "appreciation": 0.03,
    "sale_cost_pct": 0.07,
    "use_exit_cap": False,
    "exit_cap_rate": 0.07,
    "defaults": {
      "expense_rule": "str",
      "monthly_expenses_pct_of_rent": 0.55,
    }
  },
}

def normalize_template(t: Dict[str, Any]) -> Dict[str, Any]:
    # ensure required keys exist
    out = dict(t or {})
    out.setdefault("vacancy_rate", 0.08)
    out.setdefault("down_payment_pct", 20.0)
    out.setdefault("interest_rate_pct", 7.25)
    out.setdefault("term_years", 30)
    out.setdefault("hold_years", 7)
    out.setdefault("rent_growth", 0.03)
    out.setdefault("expense_growth", 0.03)
    out.setdefault("appreciation", 0.03)
    out.setdefault("sale_cost_pct", 0.07)
    out.setdefault("use_exit_cap", False)
    out.setdefault("exit_cap_rate", 0.065)
    out.setdefault("defaults", {})
    return out
