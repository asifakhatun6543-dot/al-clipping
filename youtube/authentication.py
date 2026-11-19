"""
AutoTube AI - YouTube Google OAuth 2.0 Authentication Service
Implements official Google OAuth 2.0 flow with token caching and automatic refresh.
"""

import os
import json
from pathlib import Path
from typing import Optional, Tuple
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


class YouTubeAuthenticator:
    def __init__(
        self,
        client_secret_path: Optional[Path] = None,
        token_path: Optional[Path] = None
    ):
        self.client_secret_path = client_secret_path or config.client_secret_path
        self.token_path = token_path or config.token_path

    def is_configured(self) -> bool:
        """Returns True if client_secret.json is provided."""
        return self.client_secret_path.exists() and self.client_secret_path.stat().st_size > 10

    def is_authenticated(self) -> bool:
        """Returns True if valid or refreshable credentials exist."""
        creds = self.get_credentials()
        return creds is not None and (creds.valid or creds.refresh_token is not None)

    def get_credentials(self) -> Optional[Credentials]:
        """Loads cached credentials from token.json and refreshes them if expired."""
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

    def start_local_auth_flow(self, port: int = 8088) -> Tuple[bool, str]:
        """
        Runs the local browser authorization flow for Google OAuth.
        Generates and saves token.json upon approval.
        """
        if not self.is_configured():
            return False, f"Missing Google OAuth client credentials at: {self.client_secret_path.name}"

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secret_path),
                scopes=SCOPES
            )
            # Run local webserver to handle redirect
            creds = flow.run_local_server(
                port=port,
                prompt="consent",
                success_message="AutoTube AI YouTube Authentication Successful! You can close this window now."
            )
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

            log_info("YouTubeAuth", "OAuth credentials authorized and saved to token.json.")
            return True, "YouTube channel connected successfully!"
        except Exception as e:
            log_error("YouTubeAuth", f"OAuth flow failed: {e}")
            return False, f"OAuth authorization failed: {e}"

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
            return None
        except Exception as e:
            log_error("YouTubeAuth", f"Failed to fetch channel info: {e}")
            return None
