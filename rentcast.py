import requests
from typing import Optional, Dict, Any

BASE = "https://api.rentcast.io/v1"

def _headers(api_key: str) -> dict:
    return {"X-Api-Key": api_key}

def value_avm(api_key: str, address: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"{BASE}/avm/value", headers=_headers(api_key), params={"address": address}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def rent_avm(api_key: str, address: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"{BASE}/avm/rent/long-term", headers=_headers(api_key), params={"address": address}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def property_record(api_key: str, address: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"{BASE}/properties", headers=_headers(api_key), params={"address": address}, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else None
    except Exception:
        return None
