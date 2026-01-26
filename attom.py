import requests
from typing import Optional, Dict, Any

BASE = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"

def _headers(api_key: str) -> dict:
    return {"apikey": api_key, "Accept": "application/json"}

def property_detail(api_key: str, address: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"{BASE}/property/detail", headers=_headers(api_key), params={"address": address}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None
