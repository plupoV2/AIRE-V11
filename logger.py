import json
import datetime
from typing import Any, Dict

def log_event(event: str, **kwargs: Any) -> None:
    """Lightweight structured logging (stdout). Streamlit Cloud captures logs."""
    payload: Dict[str, Any] = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "event": event,
        **kwargs
    }
    print(json.dumps(payload, default=str))
