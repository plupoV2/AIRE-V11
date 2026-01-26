import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional

@dataclass
class ResolvedLink:
    raw_url: str
    domain: str
    address_guess: Optional[str] = None
    notes: str = ""

def _domain(url: str) -> str:
    try:
        u = urllib.parse.urlparse(url.strip())
        host = (u.netloc or "").lower().replace("www.", "")
        return host
    except Exception:
        return ""

def _path(url: str) -> str:
    try:
        return urllib.parse.urlparse(url.strip()).path
    except Exception:
        return ""

def _cleanup_address(s: str) -> str:
    s = urllib.parse.unquote(s or "")
    s = s.replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def guess_address_from_url(url: str) -> ResolvedLink:
    d = _domain(url)
    p = _path(url)
    addr = None
    notes = ""

    if "zillow.com" in d:
        m = re.search(r"/homedetails/([^/]+)/", p)
        if m:
            addr = _cleanup_address(m.group(1))
            notes = "Guessed address from Zillow URL path (no scraping)."
        else:
            notes = "Could not parse address from Zillow URL path. Paste address manually."
    elif "redfin.com" in d:
        m = re.search(r"/[A-Z]{2}/[^/]+/([^/]+)/home/", p)
        if m:
            addr = _cleanup_address(m.group(1))
            notes = "Guessed address from Redfin URL path (no scraping)."
        else:
            notes = "Could not parse address from Redfin URL path. Paste address manually."
    elif "realtor.com" in d:
        m = re.search(r"/realestateandhomes-detail/([^/]+)", p)
        if m:
            cand = m.group(1).replace("_", " ")
            addr = _cleanup_address(cand)
            notes = "Guessed address from Realtor.com URL path (no scraping)."
        else:
            notes = "Could not parse address from Realtor.com URL path. Paste address manually."
    else:
        notes = "Unknown domain. If we can't parse an address, paste it manually."

    return ResolvedLink(raw_url=url, domain=d, address_guess=addr, notes=notes)

def looks_like_url(s: str) -> bool:
    s = (s or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")
