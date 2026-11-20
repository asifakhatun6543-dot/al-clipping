"""
AutoTube AI - YouTube Data API v3 & OAuth Settings
Official Google OAuth 2.0 configuration, channel diagnostics, and publishing policies
"""

from pathlib import Path
import streamlit as st
from core.config import config
from youtube.authentication import YouTubeAuthenticator
from database.db import get_setting, set_setting
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("📺 YouTube Channel & OAuth Settings")
st.caption("Secure Google OAuth 2.0 authorization for YouTube Data API v3 integration.")

auth = YouTubeAuthenticator()
is_configured = auth.is_configured()
is_authenticated = auth.is_authenticated()

# Status Banner
if is_authenticated:
    st.success("✅ Google Account Authorized (`dexoxye@gmail.com`) & YouTube API Connected!")
    ch_info = auth.get_channel_info()
    if ch_info:
        if ch_info.get("needs_creation"):
            st.warning("⚠️ Aapke is Google account par abhi tak YouTube Channel create nahi hua hai. Shorts upload karne ke liye 5 second mein apna channel create karein:")
            st.link_button("👉 Click Here to Create YouTube Channel", "https://www.youtube.com/create_channel", type="primary")
        else:
            c1, c2 = st.columns([2, 8])
            with c1:
                if ch_info.get("thumbnail"):
                    st.image(ch_info["thumbnail"], width=100)
            with c2:
                st.markdown(f"### {ch_info.get('title')}")
                st.caption(f"Channel ID: `{ch_info.get('id')}` | Subscribers: **{ch_info.get('subscriber_count')}** | Uploads: **{ch_info.get('video_count')}**")
elif is_configured:
    st.warning("⚠️ Client Secret verified! Connect your channel below to enable automatic YouTube Shorts uploads.")
else:
    st.error("❌ Google OAuth Client Credentials (`client_secret.json`) missing.")

st.markdown("---")

col_setup, col_guide = st.columns([6, 6])

with col_setup:
    st.subheader("🔑 Step 1: OAuth Credentials Status")
    if is_configured:
        st.success("✅ `client_secret.json` is installed and verified!")
        st.caption(f"Location: `{config.client_secret_path}`")
    else:
        st.info("Upload your OAuth 2.0 Client Secret JSON file below:")
        uploaded_secret = st.file_uploader("Upload client_secret.json:", type=["json"])
        if uploaded_secret is not None:
            if st.button("Save client_secret.json", key="btn_save_secret"):
                with open(config.client_secret_path, "wb") as f:
                    f.write(uploaded_secret.getbuffer())
                st.success("Client secrets saved successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("🔐 Step 2: Authorize YouTube Channel (`dexoxye@gmail.com`)")

    # Offer two seamless methods
    auth_tab1, auth_tab2 = st.tabs(["⚡ Method 1: Automatic Browser Login", "🔗 Method 2: Direct Google Link (Recommended)"])

    with auth_tab1:
        st.write("Starts a local listener on an open port and automatically opens your browser:")
        if st.button("🚀 Launch Automatic Login", type="primary", key="btn_auto_oauth", disabled=not is_configured):
            with st.spinner("Starting local listener and opening Google login..."):
                success, msg = auth.start_local_auth_flow()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with auth_tab2:
        st.write("Use this if your browser or firewall blocks local redirects:")
        email_hint = st.text_input("Google Account Email:", value="dexoxye@gmail.com")
        
        if st.button("Generate Google Authorization Link", key="btn_gen_link", disabled=not is_configured):
            auth_url, state = auth.generate_manual_auth_url(login_hint=email_hint.strip())
            st.session_state["manual_auth_url"] = auth_url

        if "manual_auth_url" in st.session_state:
            st.markdown(f"""
            **1. Click the link below to open Google's authorization page in a new tab:**  
            👉 [**Click Here to Authorize AutoTube on Google**]({st.session_state['manual_auth_url']})
            """)
            st.markdown("**2. Sign in, click 'Continue' / 'Allow', and copy the full URL from your browser's address bar or the code.**")
            
            code_input = st.text_input("3. Paste the Redirected URL or Authorization Code here:", key="manual_code_input")
            if st.button("✅ Complete Authorization & Connect Channel", type="primary", key="btn_submit_code"):
                if code_input.strip():
                    with st.spinner("Exchanging code for YouTube upload tokens..."):
                        success, msg = auth.exchange_code_for_token(code_input.strip())
                        if success:
                            st.success(msg)
                            st.session_state.pop("manual_auth_url", None)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.warning("Please paste the URL or code before clicking Complete.")

    st.markdown("---")
    st.subheader("⚙️ Publishing Defaults")
    current_privacy = get_setting("default_privacy", config.default_privacy)
    new_privacy = st.selectbox("Default Shorts Privacy Status:", ["private", "unlisted", "public"], index=["private", "unlisted", "public"].index(current_privacy))
    if new_privacy != current_privacy:
        set_setting("default_privacy", new_privacy)
        st.success(f"Default privacy updated to: {new_privacy}")

with col_guide:
    st.subheader("📖 Zero-Cost Google Cloud Setup Guide")
    st.markdown(
        """
        Your project details:
        - **Project ID:** `ferrous-gate-515213-i8`
        - **Account:** `dexoxye@gmail.com`
        
        **Important Google Cloud Console Checklist for `dexoxye@gmail.com`:**
        1. In [Google Cloud Console](https://console.cloud.google.com/):
           - Ensure **YouTube Data API v3** is **Enabled**.
        2. In **OAuth consent screen**:
           - User Type: **External**
           - Under **Test Users**, make sure `dexoxye@gmail.com` is added! (If not added, Google shows a 403 access_denied warning).
        3. When signing in, if Google says *"Google hasn't verified this app"*:
           - Click **Advanced** > **Go to AutoTube AI (unsafe)** > Click **Continue**.
        """
    )
