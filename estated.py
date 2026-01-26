import requests
from typing import Optional, Dict, Any

def property_lookup(token: str, address: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get("https://api.estated.com/v4/property", params={"token": token, "address": address}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None
