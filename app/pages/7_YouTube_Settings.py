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
    st.success("✅ YouTube Account Authorized & Ready for Automatic Publishing")
    ch_info = auth.get_channel_info()
    if ch_info:
        c1, c2 = st.columns([2, 8])
        with c1:
            if ch_info.get("thumbnail"):
                st.image(ch_info["thumbnail"], width=100)
        with c2:
            st.markdown(f"### {ch_info.get('title')}")
            st.caption(f"Channel ID: `{ch_info.get('id')}` | Subscribers: **{ch_info.get('subscriber_count')}** | Uploads: **{ch_info.get('video_count')}**")
elif is_configured:
    st.warning("⚠️ Client Secret provided, but OAuth token not yet authorized. Click 'Connect YouTube Account' below.")
else:
    st.error("❌ Google OAuth Client Credentials (`client_secret.json`) missing.")

st.markdown("---")

# OAuth Setup & Upload Form
col_setup, col_guide = st.columns([6, 6])

with col_setup:
    st.subheader("🔑 Step 1: Upload `client_secret.json`")
    uploaded_secret = st.file_uploader("Upload your OAuth 2.0 Client Secret JSON file:", type=["json"])
    if uploaded_secret is not None:
        if st.button("Save client_secret.json", key="btn_save_secret"):
            with open(config.client_secret_path, "wb") as f:
                f.write(uploaded_secret.getbuffer())
            st.success("Client secrets saved successfully! Now proceed to Step 2.")
            st.rerun()

    st.subheader("🔐 Step 2: Authorize YouTube Channel")
    st.write("This opens a local Google login window to securely approve YouTube upload permission.")
    if st.button("🚀 Connect YouTube Account (Run OAuth)", type="primary", disabled=not is_configured):
        with st.spinner("Waiting for Google authorization in browser..."):
            success, msg = auth.start_local_auth_flow()
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

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
        To obtain your free **client_secret.json**:
        1. Go to **[Google Cloud Console](https://console.cloud.google.com/)** (100% Free).
        2. Create a new project called `AutoTube-AI`.
        3. Navigate to **APIs & Services** > **Library** and search for **YouTube Data API v3**. Click **Enable**.
        4. Go to **APIs & Services** > **OAuth consent screen**:
           - Choose **External**.
           - Fill in App Name (`AutoTube AI`) and your email.
           - Under **Test Users**, add your YouTube account email.
        5. Go to **Credentials** > **Create Credentials** > **OAuth client ID**:
           - Application type: **Desktop app**.
           - Name: `AutoTube Desktop Client`.
           - Click **Create**.
        6. Click **Download JSON**, rename it to `client_secret.json`, and upload it on this page.
        
        *Quota notice: YouTube provides 10,000 free quota units per day (sufficient for ~6 Shorts uploads per day).*
        """
    )
