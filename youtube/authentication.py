"""
AutoTube AI - YouTube Google OAuth 2.0 Authentication Service
Implements official Google OAuth 2.0 flow with token caching, dynamic free-port binding,
and manual URL/code fallback to prevent Windows socket conflicts.
"""

import os
import json
import socket
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from core.config import config
from services.logger import log_info, log_error, log_warning

# YouTube Data API v3 upload and management scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly"
]

STATE_FILE = config.base_dir / ".oauth_state.json"


def get_free_port() -> int:
    """Finds a free dynamic port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class YouTubeAuthenticator:
    def __init__(
        self,
        client_secret_path: Optional[Path] = None,
        token_path: Optional[Path] = None
    ):
        self.client_secret_path = client_secret_path or config.client_secret_path
        self.token_path = token_path or config.token_path

    def is_configured(self) -> bool:
        """Returns True if client_secret.json is provided or in st.secrets."""
        if self.client_secret_path.exists() and self.client_secret_path.stat().st_size > 10:
            return True
        try:
            import streamlit as st
            if "client_secret" in st.secrets:
                val = st.secrets["client_secret"]
                content = val if isinstance(val, str) else json.dumps(dict(val))
                with open(self.client_secret_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
        except Exception:
            pass
        return False

    def is_authenticated(self) -> bool:
        """Returns True if valid or refreshable credentials exist."""
        creds = self.get_credentials()
        return creds is not None and (creds.valid or creds.refresh_token is not None)

    def get_credentials(self) -> Optional[Credentials]:
        """Loads cached credentials from token.json and refreshes them if expired."""
        if not self.token_path.exists():
            try:
                import streamlit as st
                if "youtube_token" in st.secrets:
                    val = st.secrets["youtube_token"]
                    content = val if isinstance(val, str) else json.dumps(dict(val))
                    with open(self.token_path, "w", encoding="utf-8") as f:
                        f.write(content)
            except Exception:
                pass

        if not self.token_path.exists():
            return None

        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                log_info("YouTubeAuth", "Refreshing expired OAuth access token...")
                creds.refresh(Request())
                with open(self.token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                log_info("YouTubeAuth", "Token refreshed and saved successfully.")
            return creds
        except Exception as e:
            log_error("YouTubeAuth", f"Failed to load or refresh token: {e}")
            return None

    def start_local_auth_flow(self, port: Optional[int] = None) -> Tuple[bool, str]:
        """
        Runs the official Google OAuth local server flow.
        Uses host='localhost' matching the client_secret redirect_uri.
        """
        if not self.is_configured():
            return False, f"Missing Google OAuth client credentials at: {self.client_secret_path.name}"

        # Try standard ports that Google Desktop client supports
        candidate_ports = [port] if port else [8080, 8090, 8088, 0]
        last_error = None

        for p in candidate_ports:
            try:
                log_info("YouTubeAuth", f"Attempting OAuth local server on localhost:{p}...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secret_path),
                    scopes=SCOPES
                )
                creds = flow.run_local_server(
                    host="localhost",
                    port=p,
                    prompt="consent",
                    open_browser=True,
                    success_message="AutoTube AI YouTube Authentication Successful! You can close this window now."
                )
                with open(self.token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

                log_info("YouTubeAuth", "OAuth credentials authorized and saved to token.json.")
                return True, "YouTube channel connected successfully!"
            except OSError as oe:
                last_error = oe
                log_warning("YouTubeAuth", f"Port {p} failed ({oe}), trying next port...")
                continue
            except Exception as e:
                log_error("YouTubeAuth", f"OAuth flow failed: {e}")
                return False, f"OAuth authorization failed: {e}"

        return False, f"Could not bind to any local port: {last_error}"

    def generate_manual_auth_url(self, login_hint: str = "dexoxye@gmail.com") -> Tuple[str, str]:
        """
        Generates a direct Google OAuth authorization URL for manual browser completion.
        Persists state and PKCE verifier for exchange.
        """
        redirect_uri = "http://localhost:8080/"
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_path),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        auth_url, state = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            login_hint=login_hint
        )
        state_data = {
            "code_verifier": getattr(flow, "code_verifier", None),
            "state": state,
            "redirect_uri": redirect_uri
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f)
        
        return auth_url, state

    def exchange_code_for_token(self, code_or_url: str) -> Tuple[bool, str]:
        """
        Exchanges an authorization code or full redirect URL for access and refresh tokens.
        """
        if not STATE_FILE.exists():
            return False, "Authorization session expired. Please click 'Generate Login Link' first."

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state_data = json.load(f)

        raw = code_or_url.strip()
        code = raw
        if "code=" in raw:
            parsed = urllib.parse.urlparse(raw)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                code = params["code"][0]

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_path),
            scopes=SCOPES,
            redirect_uri=state_data.get("redirect_uri", "http://localhost:8080/"),
            state=state_data.get("state")
        )
        if state_data.get("code_verifier"):
            flow.code_verifier = state_data["code_verifier"]

        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            if STATE_FILE.exists():
                try:
                    STATE_FILE.unlink()
                except Exception:
                    pass
            log_info("YouTubeAuth", "Token exchanged and saved successfully.")
            return True, "YouTube channel connected successfully!"
        except Exception as e:
            log_error("YouTubeAuth", f"Token exchange failed: {e}")
            return False, f"Token exchange error: {e}"

    def get_youtube_service(self) -> Optional[Resource]:
        """Builds and returns the authenticated YouTube Data API v3 service resource."""
        creds = self.get_credentials()
        if not creds:
            log_warning("YouTubeAuth", "No valid credentials found. Cannot build YouTube service.")
            return None

        try:
            service = build("youtube", "v3", credentials=creds, cache_discovery=False)
            return service
        except Exception as e:
            log_error("YouTubeAuth", f"Failed to build YouTube service: {e}")
            return None

    def get_channel_info(self) -> Optional[dict]:
        """Retrieves details of the authenticated user's YouTube channel."""
        service = self.get_youtube_service()
        if not service:
            return None
        try:
            response = service.channels().list(mine=True, part="snippet,statistics").execute()
            items = response.get("items", [])
            if items:
                ch = items[0]
                return {
                    "id": ch.get("id"),
                    "title": ch.get("snippet", {}).get("title"),
                    "description": ch.get("snippet", {}).get("description"),
                    "subscriber_count": ch.get("statistics", {}).get("subscriberCount", "0"),
                    "video_count": ch.get("statistics", {}).get("videoCount", "0"),
                    "view_count": ch.get("statistics", {}).get("viewCount", "0"),
                    "thumbnail": ch.get("snippet", {}).get("thumbnails", {}).get("default", {}).get("url")
                }
            return {
                "id": "No channel created yet",
                "title": "Channel Not Created Yet",
                "description": "Please visit youtube.com/create_channel to name your channel.",
                "subscriber_count": "0",
                "video_count": "0",
                "view_count": "0",
                "thumbnail": None,
                "needs_creation": True
            }
        except Exception as e:
            log_error("YouTubeAuth", f"Failed to fetch channel info: {e}")
            return None
