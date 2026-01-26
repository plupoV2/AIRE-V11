import streamlit as st

def render_landing():
    st.markdown('<div class="card hero shimmer">', unsafe_allow_html=True)
    st.markdown("""
# AIRE Terminal
**Paste any listing link. Get an investment-grade report in seconds.**

AIRE is a real estate underwriting terminal that turns messy listings into a clean, standardized decision:
**A–F grade, verdict, key metrics, risk flags, and exportable reports.**
""")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        st.button("Start Free Trial", type="primary", use_container_width=True, key="cta_start")
    with c2:
        st.button("Log in", use_container_width=True, key="cta_login")
    with c3:
        st.caption("Built for individual investors, teams, and funds. Batch screen deals. Save templates. Set alerts.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Why teams adopt AIRE")
    a,b,c = st.columns(3)
    with a:
        st.markdown('<div class="card shimmer">', unsafe_allow_html=True)
        st.markdown("**Instant clarity**\n\nNo spreadsheets. Paste → Grade → Decide.")
        st.markdown('</div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card shimmer">', unsafe_allow_html=True)
        st.markdown("**Standardized underwriting**\n\nOne scoring system across your organization.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="card shimmer">', unsafe_allow_html=True)
        st.markdown("**Shareable outputs**\n\nPDF reports, exports, and an API for workflows.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Pricing")
    p1,p2,p3 = st.columns(3)
    for col, title, bullets in [
        (p1, "Free", ["5 grades/day", "Batch 25 rows", "Reports + templates"]),
        (p2, "Pro", ["100 grades/day", "Batch 200 rows", "API access", "Alerts"]),
        (p3, "Team", ["500 grades/day", "Batch 500 rows", "API + team workflows", "Priority support"]),
    ]:
        with col:
            st.markdown('<div class="card shimmer">', unsafe_allow_html=True)
            st.markdown(f"**{title}**")
            for b in bullets:
                st.write("•", b)
            st.markdown('</div>', unsafe_allow_html=True)

    st.caption("Tip: For ads, send traffic to `/?landing=1` so people see this page first.")
