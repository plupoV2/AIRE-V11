from io import BytesIO
from typing import Dict, Any
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def _safe(v):
    return "" if v is None else str(v)

def build_report_pdf(report: Dict[str, Any]) -> bytes:
    """Create a clean one-page PDF investment report."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER

    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.75*inch, h-0.85*inch, "AIRE Investment Report")
    c.setFont("Helvetica", 10)
    c.drawString(0.75*inch, h-1.05*inch, f"Report ID: {_safe(report.get('report_id'))}")
    c.drawRightString(w-0.75*inch, h-1.05*inch, f"Confidence: {_safe(report.get('confidence'))}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, h-1.40*inch, _safe(report.get("address")))

    grade_display = report.get("grade_detail") or report.get("grade")
    c.setFont("Helvetica-Bold", 36)
    c.drawString(0.75*inch, h-2.05*inch, _safe(grade_display))
    c.setFont("Helvetica", 12)
    c.drawString(1.55*inch, h-1.95*inch, f"Score: {_safe(report.get('score'))}/100")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.55*inch, h-2.15*inch, _safe(report.get("verdict")))

    metrics = (
        report.get("metrics")
        or (report.get("payload") or {}).get("outputs", {}).get("metrics_summary")
        or {}
    )
    y = h-2.70*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "Key Metrics")
    y -= 0.18*inch
    c.setFont("Helvetica", 11)

    def line(k, v):
        nonlocal y
        c.drawString(0.85*inch, y, f"{k}: {v}")
        y -= 0.16*inch

    for key in ["cap_rate","cash_on_cash","dscr","irr","noi_monthly","payment_monthly","cashflow_monthly"]:
        if key in metrics:
            line(key.replace("_"," ").title(), _safe(metrics.get(key)))

    y -= 0.12*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "Flags")
    y -= 0.18*inch
    c.setFont("Helvetica", 11)
    flags = report.get("flags") or []
    if isinstance(flags, str):
        flags = [f.strip() for f in flags.split(";") if f.strip()]
    if not flags:
        line("•", "None")
    else:
        for f in flags[:10]:
            line("•", f)

    y -= 0.08*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "Grade Rationale")
    y -= 0.18*inch
    c.setFont("Helvetica", 10)
    rationale = report.get("rationale") or (report.get("payload") or {}).get("outputs", {}).get("rationale") or []
    if not rationale:
        line("•", "None")
    else:
        for r in list(rationale)[:8]:
            line("•", r)

    y -= 0.08*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "Data Provenance (Sources)")
    y -= 0.18*inch
    c.setFont("Helvetica", 9)
    prov = (report.get("payload") or {}).get("provenance") or {}
    for field, info in list(prov.items())[:6]:
        src = (info or {}).get("source","")
        conf = (info or {}).get("confidence","")
        c.drawString(0.85*inch, y, f"{field}: {src} (conf {conf})")
        y -= 0.14*inch

    c.setFont("Helvetica", 8)
    c.drawString(0.75*inch, 0.65*inch, "Not financial advice. Verify all figures; data may be incomplete or delayed.")
    c.showPage()
    c.save()
    return buf.getvalue()
