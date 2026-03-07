"""Simple authentication for ATLAS Web Dashboard."""

import logging
import os
import secrets
import hashlib
from typing import Optional
from pathlib import Path

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger("atlas.web.auth")


# Security instance
security = HTTPBasic(auto_error=False)

# Credentials storage
_credentials: Optional[dict] = None


def get_credentials_file() -> Path:
    """Get path to credentials file."""
    return Path.home() / ".config" / "atlas" / "auth.txt"


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """Hash a password."""
    return hashlib.sha256(password.encode()).hexdigest()


def setup_auth(username: str = "atlas", password: Optional[str] = None) -> dict:
    """Set up authentication credentials.

    Args:
        username: Username (default: atlas)
        password: Password (generates one if not provided)

    Returns:
        Dict with username and password
    """
    if password is None:
        password = generate_password()

    creds_file = get_credentials_file()
    creds_file.parent.mkdir(parents=True, exist_ok=True)

    # Store username and hashed password
    with open(creds_file, 'w') as f:
        f.write(f"{username}\n{hash_password(password)}\n")

    # Set restrictive permissions
    os.chmod(creds_file, 0o600)

    # Return plaintext for user to save
    return {"username": username, "password": password}


def load_credentials() -> Optional[dict]:
    """Load credentials from file."""
    global _credentials

    if _credentials is not None:
        return _credentials

    creds_file = get_credentials_file()
    if not creds_file.exists():
        return None

    try:
        with open(creds_file) as f:
            lines = f.read().strip().split('\n')
            if len(lines) >= 2:
                _credentials = {
                    "username": lines[0],
                    "password_hash": lines[1],
                }
                return _credentials
    except (IOError, OSError) as e:
        logger.warning(f"Failed to load credentials file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading credentials: {e}")

    return None


def verify_credentials(credentials: HTTPBasicCredentials) -> bool:
    """Verify username and password."""
    stored = load_credentials()
    if not stored:
        return True  # No auth configured, allow access

    if credentials is None:
        return False

    # Check username
    username_correct = secrets.compare_digest(
        credentials.username.encode(),
        stored["username"].encode()
    )

    # Check password hash
    password_hash = hash_password(credentials.password)
    password_correct = secrets.compare_digest(
        password_hash.encode(),
        stored["password_hash"].encode()
    )

    return username_correct and password_correct


def is_auth_enabled() -> bool:
    """Check if authentication is configured."""
    return load_credentials() is not None


async def require_auth(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
):
    """Dependency to require authentication.

    If auth is not configured, allows access.
    If auth is configured, requires valid credentials.
    """
    # Skip auth check for static files and websocket
    if request.url.path.startswith('/static') or request.url.path == '/ws':
        return True

    # If no auth configured, allow access
    if not is_auth_enabled():
        return True

    # Verify credentials
    if not verify_credentials(credentials):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm='ATLAS Dashboard'"},
        )

    return True


def get_auth_status() -> dict:
    """Get current auth status for display."""
    creds = load_credentials()
    return {
        "enabled": creds is not None,
        "username": creds["username"] if creds else None,
    }
