"""Authentication module for YouTube access (cookies and OAuth)."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class AuthManager:
    """Manages authentication for YouTube access."""

    SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the authentication manager.

        Args:
            config_dir: Directory to store auth credentials. Defaults to ~/.ytpl_downloader
        """
        if config_dir is None:
            config_dir = Path.home() / '.ytpl_downloader'

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.cookies_file = self.config_dir / 'cookies.txt'
        self.oauth_token_file = self.config_dir / 'oauth_token.json'
        self.oauth_credentials_file = self.config_dir / 'client_secrets.json'

    def has_cookies(self) -> bool:
        """Check if cookies file exists."""
        return self.cookies_file.exists()

    def has_oauth(self) -> bool:
        """Check if OAuth token exists."""
        return self.oauth_token_file.exists()

    def get_cookies_path(self) -> Optional[str]:
        """Get path to cookies file if it exists."""
        if self.has_cookies():
            return str(self.cookies_file)
        return None

    def set_cookies_file(self, cookies_path: str) -> None:
        """
        Copy or set the cookies file.

        Args:
            cookies_path: Path to the cookies.txt file (Netscape format)
        """
        source = Path(cookies_path)
        if not source.exists():
            raise FileNotFoundError(f"Cookies file not found: {cookies_path}")

        # Copy to our config directory
        import shutil
        shutil.copy2(source, self.cookies_file)
        print(f"Cookies file set: {self.cookies_file}")

    def setup_oauth(self, client_secrets_path: Optional[str] = None) -> Credentials:
        """
        Set up OAuth authentication.

        Args:
            client_secrets_path: Path to client_secrets.json from Google Cloud Console.
                                If None, looks for it in config_dir.

        Returns:
            Google OAuth2 credentials
        """
        # Check if we need to copy client secrets
        if client_secrets_path:
            source = Path(client_secrets_path)
            if not source.exists():
                raise FileNotFoundError(f"Client secrets file not found: {client_secrets_path}")
            import shutil
            shutil.copy2(source, self.oauth_credentials_file)

        if not self.oauth_credentials_file.exists():
            raise FileNotFoundError(
                f"Client secrets file not found. Please download it from Google Cloud Console "
                f"and save it to: {self.oauth_credentials_file}"
            )

        creds = None

        # Check if we have a token file
        if self.oauth_token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.oauth_token_file), self.SCOPES)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.oauth_credentials_file), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.oauth_token_file, 'w') as token:
                token.write(creds.to_json())

        print(f"OAuth authenticated successfully. Token saved to: {self.oauth_token_file}")
        return creds

    def get_oauth_credentials(self) -> Optional[Credentials]:
        """Get existing OAuth credentials if available."""
        if not self.has_oauth():
            return None

        try:
            creds = Credentials.from_authorized_user_file(str(self.oauth_token_file), self.SCOPES)
            if creds and creds.valid:
                return creds
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.oauth_token_file, 'w') as token:
                    token.write(creds.to_json())
                return creds
        except Exception as e:
            print(f"Error loading OAuth credentials: {e}")
            return None

        return None

    def clear_cookies(self) -> None:
        """Remove cookies file."""
        if self.cookies_file.exists():
            self.cookies_file.unlink()
            print("Cookies file removed")

    def clear_oauth(self) -> None:
        """Remove OAuth token."""
        if self.oauth_token_file.exists():
            self.oauth_token_file.unlink()
            print("OAuth token removed")

    def get_ytdlp_params(self) -> Dict[str, Any]:
        """
        Get yt-dlp parameters with authentication if available.

        Returns:
            Dictionary of yt-dlp parameters
        """
        params = {}

        # Prefer cookies over OAuth for yt-dlp
        if self.has_cookies():
            params['cookiefile'] = str(self.cookies_file)
        # Note: yt-dlp doesn't directly use OAuth tokens, so cookies are the primary method

        return params

    def get_auth_status(self) -> Dict[str, bool]:
        """Get the status of available authentication methods."""
        return {
            'cookies': self.has_cookies(),
            'oauth': self.has_oauth(),
        }
