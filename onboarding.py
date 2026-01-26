import streamlit as st
from templates import BUILTIN_TEMPLATES, normalize_template
from storage import upsert_template

def needs_onboarding() -> bool:
    return not st.session_state.get("onboarded", False)

def run_onboarding(workspace_id: int, user_id: int):
    st.markdown('<div class="card shimmer">', unsafe_allow_html=True)
    st.markdown("## Quick setup (60 seconds)")
    st.caption("This saves a default template so underwriting is fast and consistent.")

    step = st.session_state.get("onboarding_step", 1)

    if step == 1:
        st.markdown("### 1) Choose your strategy")
        style = st.radio("Primary strategy", ["Long-Term Rental (LTR)", "BRRRR", "Short-Term Rental (STR)"], horizontal=True)
        st.session_state.onboarding_style = style
        if st.button("Next", type="primary"):
            st.session_state.onboarding_step = 2
            st.rerun()

    elif step == 2:
        st.markdown("### 2) Pick a default template")
        options = list(BUILTIN_TEMPLATES.keys())
        default = st.session_state.get("onboarding_style", "Long-Term Rental (LTR)")
        idx = options.index(default) if default in options else 0
        choice = st.selectbox("Default template", options, index=idx)
        st.session_state.onboarding_template = choice
        st.caption("You can customize templates later.")
        if st.button("Next", type="primary"):
            st.session_state.onboarding_step = 3
            st.rerun()

    elif step == 3:
        st.markdown("### 3) Save default template")
        name = st.text_input("Template name", value=f"My Default - {st.session_state.get('onboarding_template','LTR')}")
        base = normalize_template(BUILTIN_TEMPLATES.get(st.session_state.get("onboarding_template","Long-Term Rental (LTR)")))
        if st.button("Save & Finish", type="primary"):
            upsert_template(name, base, workspace_id=workspace_id, user_id=user_id)
            st.session_state.onboarded = True
            st.session_state.onboarding_step = 1
            st.success("Setup complete. Paste a listing link to grade your first deal.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
