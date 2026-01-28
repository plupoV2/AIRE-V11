from dataclasses import dataclass
import streamlit as st

@dataclass(frozen=True)
class AppConfig:
    rentcast_apikey: str = ""
    estated_token: str = ""
    attom_apikey: str = ""
    openai_api_key: str = ""
    sendgrid_api_key: str = ""
    alert_email_to: str = ""

    # Optional access control for B2B demos / private deployments
    access_key: str = ""  # if set, users must enter this to use the app

    # Safety / performance
    api_timeout_sec: int = 15
    cache_ttl_sec: int = 3600

    # Stripe (live billing)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro: str = ""
    stripe_price_id_team: str = ""
    stripe_success_url: str = ""
    stripe_cancel_url: str = ""
    stripe_portal_return_url: str = ""
    stripe_portal_configuration_id: str = ""  # optional

    # Developer mode (demo access)
    dev_bypass_key: str = ""      # optional; if set, enables demo bypass via key
    dev_admin_emails: str = ""    # comma-separated emails that always have dev mode

def _secret(s, key: str, default):
    try:
        return s.get(key, default)
    except Exception:
        return default

def load_config() -> AppConfig:
    try:
        s = st.secrets
    except Exception:
        s = {}
    return AppConfig(
        rentcast_apikey=_secret(s, "RENTCAST_APIKEY",""),
        estated_token=_secret(s, "ESTATED_TOKEN",""),
        attom_apikey=_secret(s, "ATTOM_APIKEY",""),
        openai_api_key=_secret(s, "OPENAI_API_KEY",""),
        sendgrid_api_key=_secret(s, "SENDGRID_API_KEY",""),
        alert_email_to=_secret(s, "ALERT_EMAIL_TO",""),
        access_key=_secret(s, "APP_ACCESS_KEY",""),
        api_timeout_sec=int(_secret(s, "API_TIMEOUT_SEC", 15)),
        cache_ttl_sec=int(_secret(s, "CACHE_TTL_SEC", 3600)),

        stripe_secret_key=_secret(s, "STRIPE_SECRET_KEY",""),
        stripe_webhook_secret=_secret(s, "STRIPE_WEBHOOK_SECRET",""),
        stripe_price_id_pro=_secret(s, "STRIPE_PRICE_ID_PRO",""),
        stripe_price_id_team=_secret(s, "STRIPE_PRICE_ID_TEAM",""),
        stripe_success_url=_secret(s, "STRIPE_SUCCESS_URL",""),
        stripe_cancel_url=_secret(s, "STRIPE_CANCEL_URL",""),
        stripe_portal_return_url=_secret(s, "STRIPE_PORTAL_RETURN_URL",""),
        stripe_portal_configuration_id=_secret(s, "STRIPE_PORTAL_CONFIGURATION_ID",""),

        dev_bypass_key=_secret(s, "DEV_BYPASS_KEY",""),
        dev_admin_emails=_secret(s, "DEV_ADMIN_EMAILS",""),
    )

def validate_config(cfg: AppConfig) -> list[str]:
    issues = []
    if cfg.sendgrid_api_key and not cfg.alert_email_to:
        issues.append("SENDGRID_API_KEY is set but ALERT_EMAIL_TO is missing.")
    if cfg.stripe_secret_key and not cfg.stripe_webhook_secret:
        issues.append("STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is missing (required for live enforcement).")
    return issues
