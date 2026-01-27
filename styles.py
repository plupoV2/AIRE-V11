EXCHANGE_UI_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root{
  --bg0:#f4f7fb;
  --bg1:#eef3fb;
  --panel:#ffffff;
  --panel2:#f7f9fc;
  --border:rgba(23,34,59,.12);
  --text:#1a2438;
  --muted:#667089;
  --accent:#3f7ddb;
  --accent2:#6aa9ff;
  --good:#18a957;
  --warn:#f59e0b;
  --bad:#ef4444;
  --shadow:rgba(32,56,93,.18);
}

html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 700px at 10% 0%, rgba(63,125,219,.10), transparent 60%),
              radial-gradient(900px 600px at 90% 10%, rgba(106,169,255,.12), transparent 55%),
              linear-gradient(180deg, var(--bg0), var(--bg1)) !important;
  color: var(--text) !important;
}
*{font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial !important;}
a{color: var(--accent2) !important; text-decoration:none;}
a:hover{text-decoration:underline;}
hr{border-color: var(--border) !important;}

section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(245,248,252,.98)) !important;
  border-right: 1px solid rgba(23,34,59,.08) !important;
}

label{color: var(--muted) !important; font-weight: 700 !important; letter-spacing: .01em;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li{color: var(--text) !important;}
[data-testid="stMarkdownContainer"] small{color: var(--muted) !important;}

.stButton > button{
  border-radius: 999px !important;
  border: 1px solid rgba(63,125,219,.20) !important;
  background: linear-gradient(90deg, #3f7ddb, #6aa9ff) !important;
  color: #ffffff !important;
  font-weight: 800 !important;
  padding: 0.78rem 1.1rem !important;
  box-shadow: 0 18px 50px rgba(63,125,219,.25) !important;
}
.stButton > button:hover{filter:brightness(1.07); transform: translateY(-1px);}
.stButton > button:active{transform: translateY(0px);}

.stTextInput > div > div, .stTextArea > div > div, .stNumberInput > div > div, .stSelectbox > div > div{
  background: #ffffff !important;
  border: 1px solid rgba(23,34,59,.14) !important;
  border-radius: 14px !important;
  color: var(--text) !important;
  box-shadow: inset 0 1px 2px rgba(16,24,40,.04);
}
.stTextInput input, .stTextArea textarea{color: var(--text) !important;}

.card{
  background: #ffffff;
  border: 1px solid rgba(23,34,59,.10);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 22px 60px rgba(32,56,93,.12);
}
.subcard{
  background: #f8fafc;
  border: 1px solid rgba(23,34,59,.08);
  border-radius: 16px;
  padding: 14px;
}
.tablewrap{
  background: #ffffff;
  border: 1px solid rgba(23,34,59,.08);
  border-radius: 16px;
  padding: 10px;
}
.navbar{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  padding:14px 16px;
  border-radius:18px;
  border:1px solid rgba(23,34,59,.10);
  background: rgba(255,255,255,.9);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 55px rgba(32,56,93,.12);
  margin: 6px 0 16px 0;
}
.brand{
  display:flex;
  align-items:center;
  gap:10px;
  font-weight:900;
  letter-spacing:-0.02em;
  font-size:18px;
}
.brand .dot{
  width:10px;height:10px;border-radius:999px;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  box-shadow: 0 0 22px rgba(34,211,238,.35);
}
.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(23,34,59,.12);
  background: rgba(63,125,219,.08);
  color: var(--text);
  font-weight:900;
  font-size:12px;
}
.pillbtn{
  display:inline-flex;
  align-items:center;
  padding:8px 12px;
  border-radius:999px;
  border:1px solid rgba(23,34,59,.12);
  background: #ffffff;
  color: var(--text) !important;
  font-weight:800;
  font-size:12px;
}
.pillbtn:hover{background: rgba(63,125,219,.10);}
.hero h1{font-size:40px; line-height:1.05; margin:0; letter-spacing:-0.03em;}
.hero p{margin-top:10px; color: var(--muted) !important; font-size:14.5px; line-height:1.5; max-width:72ch;}
.kpis{display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin-top:14px;}
.kpi{background: #ffffff; border:1px solid rgba(23,34,59,.10); border-radius:16px; padding:14px; box-shadow: 0 10px 22px rgba(32,56,93,.08);}
.kpi .label{color: var(--muted); font-weight:900; font-size:12px; text-transform:uppercase; letter-spacing:.08em;}
.kpi .value{font-size:22px; font-weight:900; margin-top:4px;}
.kpi .hint{color: var(--muted); font-size:12px; margin-top:6px;}

.biggrade{font-size:46px; font-weight:900; letter-spacing:-0.04em; margin:0;}
.gradepill{
  display:inline-flex; align-items:center; gap:10px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(23,34,59,.12);
  background: rgba(63,125,219,.10);
  font-weight: 900;
}
.gradehero{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:14px;
  padding:14px 16px;
  border-radius:18px;
  border:1px solid rgba(23,34,59,.12);
  background: linear-gradient(135deg, rgba(63,125,219,.12), rgba(106,169,255,.10));
  box-shadow: inset 0 0 0 1px rgba(23,34,59,.04);
}
.gradehero .gradecopy{display:flex; flex-direction:column; gap:6px;}
.gradehero .gradelabel{font-size:12px; letter-spacing:.14em; text-transform:uppercase; color: var(--muted);}
.gradehero .gradevalue{font-size:46px; font-weight:900; letter-spacing:-0.04em;}
.gradehero .gradeverdict{font-weight:900; opacity:.85;}
.badge-soft{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid rgba(23,34,59,.12);
  background: rgba(63,125,219,.10);
  font-weight:800;
  font-size:12px;
}
.report-grid{
  display:grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap:12px;
}
.report-card{
  background: #ffffff;
  border:1px solid rgba(23,34,59,.10);
  border-radius:16px;
  padding:12px 14px;
  box-shadow: 0 10px 24px rgba(32,56,93,.08);
}
.report-card h4{margin:0 0 6px 0; font-size:14px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted);}
.metric-list{display:flex; flex-direction:column; gap:6px; font-weight:600;}
.metric-list span{color: var(--text);}
.metric-list small{color: var(--muted);}
.bullet-list{display:flex; flex-direction:column; gap:6px;}
.bullet-list div{padding:6px 8px; border-radius:10px; background: rgba(63,125,219,.06); border:1px solid rgba(23,34,59,.08);}
.scoreblend{display:flex; gap:10px; flex-wrap:wrap;}
.scoreblend .pill{
  padding:6px 10px;
  border-radius:12px;
  border:1px solid rgba(23,34,59,.12);
  background: rgba(63,125,219,.08);
  font-weight:800;
  font-size:12px;
}

.dotlive{width:10px;height:10px;border-radius:999px;background: var(--good); box-shadow:0 0 16px rgba(34,197,94,.35); animation:pulse 1.4s infinite;}
.dotwarn{width:10px;height:10px;border-radius:999px;background: var(--warn); box-shadow:0 0 16px rgba(245,158,11,.30); animation:pulse 1.4s infinite;}
.dotbad{width:10px;height:10px;border-radius:999px;background: var(--bad); box-shadow:0 0 16px rgba(239,68,68,.28); animation:pulse 1.4s infinite;}
@keyframes pulse{0%{transform:scale(.85);opacity:.6;}50%{transform:scale(1.18);opacity:1;}100%{transform:scale(.85);opacity:.6;}}

div[role="radiogroup"] > label{padding:8px 10px !important; border-radius:12px !important;}
div[role="radiogroup"] > label:hover{background: rgba(255,255,255,.06) !important;}
</style>
"""
