"""Google OAuth2 authentication for ATLAS - Calendar and Gmail access."""

import json
import os
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger("atlas.integrations.google_auth")


class GoogleAuth:
    """Handle Google OAuth2 authentication for API access."""

    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    def __init__(
        self,
        credentials_file: str = None,
        token_file: str = None,
        scopes: List[str] = None,
    ):
        """Initialize Google authentication.

        Args:
            credentials_file: Path to OAuth credentials JSON from Google Console
            token_file: Path to store/load access tokens
            scopes: List of API scopes to request
        """
        config_dir = Path.home() / ".config" / "atlas"
        config_dir.mkdir(parents=True, exist_ok=True)

        self.credentials_file = Path(credentials_file or config_dir / "google_credentials.json")
        self.token_file = Path(token_file or config_dir / "google_tokens.json")
        self.scopes = scopes or self.DEFAULT_SCOPES

        self._credentials = None

    def is_configured(self) -> bool:
        """Check if Google credentials are configured.

        Returns:
            True if credentials file exists
        """
        return self.credentials_file.exists()

    def is_authenticated(self) -> bool:
        """Check if we have valid tokens.

        Returns:
            True if authenticated with valid tokens
        """
        if not self.token_file.exists():
            return False

        try:
            creds = self._load_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False

    def _load_credentials(self):
        """Load credentials from token file.

        Returns:
            Google Credentials object or None
        """
        if self._credentials:
            return self._credentials

        if not self.token_file.exists():
            return None

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            self._credentials = Credentials.from_authorized_user_file(
                str(self.token_file),
                self.scopes,
            )

            # Refresh if expired
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(Request())
                self._save_credentials()

            return self._credentials

        except ImportError:
            logger.error("google-auth not installed. Run: pip install google-auth google-auth-oauthlib")
            return None
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def _save_credentials(self):
        """Save credentials to token file."""
        if not self._credentials:
            return

        token_data = {
            "token": self._credentials.token,
            "refresh_token": self._credentials.refresh_token,
            "token_uri": self._credentials.token_uri,
            "client_id": self._credentials.client_id,
            "client_secret": self._credentials.client_secret,
            "scopes": list(self._credentials.scopes) if self._credentials.scopes else self.scopes,
        }

        self.token_file.write_text(json.dumps(token_data, indent=2))
        # Secure the file
        os.chmod(self.token_file, 0o600)

    def authenticate_interactive(self) -> bool:
        """Run interactive OAuth flow.

        This opens a browser for the user to authenticate.

        Returns:
            True if authentication successful
        """
        if not self.is_configured():
            logger.error(f"Credentials file not found: {self.credentials_file}")
            logger.info("Download OAuth credentials from Google Cloud Console")
            return False

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                self.scopes,
            )

            # Run local server for OAuth callback
            self._credentials = flow.run_local_server(
                port=0,
                success_message="Authentication successful! You may close this window.",
            )

            self._save_credentials()
            logger.info("Google authentication successful")
            return True

        except ImportError:
            logger.error("google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def get_credentials(self):
        """Get valid credentials, refreshing if needed.

        Returns:
            Google Credentials object or None
        """
        creds = self._load_credentials()

        if not creds:
            logger.warning("No valid credentials. Run authentication first.")
            return None

        return creds

    def build_service(self, api_name: str, api_version: str):
        """Build a Google API service client.

        Args:
            api_name: API name (e.g., 'calendar', 'gmail')
            api_version: API version (e.g., 'v3', 'v1')

        Returns:
            Google API service object or None
        """
        creds = self.get_credentials()
        if not creds:
            return None

        try:
            from googleapiclient.discovery import build

            return build(api_name, api_version, credentials=creds)

        except ImportError:
            logger.error("google-api-python-client not installed. Run: pip install google-api-python-client")
            return None
        except Exception as e:
            logger.error(f"Failed to build {api_name} service: {e}")
            return None

    def revoke(self) -> bool:
        """Revoke current tokens.

        Returns:
            True if successful
        """
        try:
            import requests

            creds = self._load_credentials()
            if creds and creds.token:
                requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": creds.token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )

            # Remove token file
            if self.token_file.exists():
                self.token_file.unlink()

            self._credentials = None
            logger.info("Google tokens revoked")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke tokens: {e}")
            return False


def setup_google_auth(scopes: List[str] = None) -> bool:
    """Interactive setup for Google authentication.

    Args:
        scopes: API scopes to request

    Returns:
        True if setup successful
    """
    print("\n=== Google Authentication Setup ===\n")

    auth = GoogleAuth(scopes=scopes)

    if not auth.is_configured():
        print("No credentials file found.")
        print("\nTo set up Google integration:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Calendar API and Gmail API")
        print("4. Go to 'APIs & Services' > 'Credentials'")
        print("5. Create OAuth 2.0 Client ID (Desktop app)")
        print("6. Download the JSON file")
        print(f"7. Save it as: {auth.credentials_file}")
        print("\nThen run this setup again.")
        return False

    if auth.is_authenticated():
        print("Already authenticated!")
        response = input("Re-authenticate? (y/N): ").strip().lower()
        if response != "y":
            return True

    print("\nOpening browser for authentication...")
    print("Please sign in with your Google account.\n")

    return auth.authenticate_interactive()
