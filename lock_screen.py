import streamlit as st

def render_lock(reason: str = ""):
    st.markdown('<div class="card hero shimmer">', unsafe_allow_html=True)
    st.markdown("## 🔒 Subscription required")
    if reason:
        st.write(reason)
    st.write("Your workspace subscription is not active. To continue, re-activate your plan in **Billing**.")
    st.info("If you're the developer demoing to investors, enable **Developer mode** in the sidebar.")
    st.markdown('</div>', unsafe_allow_html=True)
