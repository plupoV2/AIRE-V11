# Ops Runbook (Starter)

## Environments
- Streamlit UI: app.py (Streamlit Cloud)
- API backend: api_server.py (Render/Fly/Railway) — recommended

## Monitoring
- Streamlit logs: "Manage app" → Logs
- API logs: hosting provider logs

## Incidents
1) Identify outage: UI failing vs API failing vs data provider failing
2) Check secrets: API keys present and valid
3) Reduce load: lower cache TTL, temporarily restrict batch size
4) Communicate: update status + email customers

## Data providers
- RentCast / Estated / ATTOM can rate-limit — handle gracefully.
