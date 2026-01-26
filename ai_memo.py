import requests
from typing import Optional, Dict, Any

def generate_investment_memo(seed: Dict[str, Any], api_key: Optional[str], model: str = "gpt-4.1-mini") -> Optional[str]:
    if not api_key:
        return None

    sys = "You are a senior real estate acquisitions analyst. Write a concise investor memo."
    user = {"task": "Create an investment memo from the underwriting data. Use bullets. Include risks + mitigations.", "data": seed}

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role":"system","content":sys},{"role":"user","content":str(user)}], "temperature": 0.2, "max_tokens": 600},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        j = r.json()
        return j["choices"][0]["message"]["content"]
    except Exception:
        return None
