EXCHANGE_UI_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root{
  --bg0:#070A13;
  --bg1:#0B0F19;
  --panel:#0F1629;
  --panel2:#0B1224;
  --border:rgba(255,255,255,.10);
  --text:#EAF0FF;
  --muted:#A7B0C2;
  --accent:#7C3AED;
  --accent2:#22D3EE;
  --good:#22C55E;
  --warn:#F59E0B;
  --bad:#EF4444;
  --shadow:rgba(0,0,0,.55);
}

html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 600px at 10% -10%, rgba(124,58,237,.35), transparent 60%),
              radial-gradient(900px 500px at 90% 0%, rgba(34,211,238,.22), transparent 55%),
              linear-gradient(180deg, var(--bg0), var(--bg1)) !important;
  color: var(--text) !important;
}
*{font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial !important;}
a{color: var(--accent2) !important; text-decoration:none;}
a:hover{text-decoration:underline;}
hr{border-color: var(--border) !important;}

section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(15,22,41,.97), rgba(11,18,36,.94)) !important;
  border-right: 1px solid var(--border) !important;
}

label{color: var(--muted) !important; font-weight: 700 !important; letter-spacing: .01em;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li{color: var(--text) !important;}
[data-testid="stMarkdownContainer"] small{color: var(--muted) !important;}

.stButton > button{
  border-radius: 14px !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  background: linear-gradient(90deg, rgba(124,58,237,.95), rgba(34,211,238,.85)) !important;
  color: #06101B !important;
  font-weight: 900 !important;
  padding: 0.78rem 1rem !important;
  box-shadow: 0 18px 50px rgba(0,0,0,.45) !important;
}
.stButton > button:hover{filter:brightness(1.07); transform: translateY(-1px);}
.stButton > button:active{transform: translateY(0px);}

.stTextInput > div > div, .stTextArea > div > div, .stNumberInput > div > div, .stSelectbox > div > div{
  background: rgba(15,22,41,.74) !important;
  border: 1px solid rgba(255,255,255,.12) !important;
  border-radius: 14px !important;
  color: var(--text) !important;
}
.stTextInput input, .stTextArea textarea{color: var(--text) !important;}

.card{
  background: linear-gradient(180deg, rgba(15,22,41,.80), rgba(11,18,36,.72));
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 22px 70px rgba(0,0,0,.45);
}
.subcard{
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 16px;
  padding: 14px;
}
.tablewrap{
  background: rgba(255,255,255,.03);
  border: 1px solid rgba(255,255,255,.10);
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
  border:1px solid rgba(255,255,255,.10);
  background: rgba(15,22,41,.62);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 55px rgba(0,0,0,.40);
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
  border:1px solid rgba(255,255,255,.14);
  background: rgba(255,255,255,.06);
  color: var(--text);
  font-weight:900;
  font-size:12px;
}
.pillbtn{
  display:inline-flex;
  align-items:center;
  padding:8px 12px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.14);
  background: rgba(255,255,255,.06);
  color: var(--text) !important;
  font-weight:800;
  font-size:12px;
}
.pillbtn:hover{background: rgba(255,255,255,.10);}
.hero h1{font-size:40px; line-height:1.05; margin:0; letter-spacing:-0.03em;}
.hero p{margin-top:10px; color: var(--muted) !important; font-size:14.5px; line-height:1.5; max-width:72ch;}
.kpis{display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin-top:14px;}
.kpi{background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.10); border-radius:16px; padding:14px;}
.kpi .label{color: var(--muted); font-weight:900; font-size:12px; text-transform:uppercase; letter-spacing:.08em;}
.kpi .value{font-size:22px; font-weight:900; margin-top:4px;}
.kpi .hint{color: var(--muted); font-size:12px; margin-top:6px;}

.biggrade{font-size:46px; font-weight:900; letter-spacing:-0.04em; margin:0;}
.gradepill{
  display:inline-flex; align-items:center; gap:10px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.14);
  background: rgba(255,255,255,.06);
  font-weight: 900;
}

.dotlive{width:10px;height:10px;border-radius:999px;background: var(--good); box-shadow:0 0 16px rgba(34,197,94,.35); animation:pulse 1.4s infinite;}
.dotwarn{width:10px;height:10px;border-radius:999px;background: var(--warn); box-shadow:0 0 16px rgba(245,158,11,.30); animation:pulse 1.4s infinite;}
.dotbad{width:10px;height:10px;border-radius:999px;background: var(--bad); box-shadow:0 0 16px rgba(239,68,68,.28); animation:pulse 1.4s infinite;}
@keyframes pulse{0%{transform:scale(.85);opacity:.6;}50%{transform:scale(1.18);opacity:1;}100%{transform:scale(.85);opacity:.6;}}

div[role="radiogroup"] > label{padding:8px 10px !important; border-radius:12px !important;}
div[role="radiogroup"] > label:hover{background: rgba(255,255,255,.06) !important;}
</style>
"""
