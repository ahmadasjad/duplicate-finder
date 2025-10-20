"""
Helper to generate an rclone config entry for Google Drive using existing credentials.

This module provides a convenience function `ensure_rclone_remote()` which attempts to read
existing credentials/token (from google_utils' TOKEN_FILE and CREDENTIALS_FILE) and writes
a minimal rclone config to `~/.config/rclone/rclone.conf` (or the path specified by env
RCLONE_CONFIG_FILE). It avoids exposing secrets in logs.

Notes:
- rclone supports several auth flows. This helper assumes the token.json produced by
  `google-auth-oauthlib` is compatible and attempts to populate an rclone `remote` using
  `type = drive` with client_id/client_secret if available.
- This helper is best-effort; users may need to run `rclone config` manually if edge cases occur.
"""
from __future__ import annotations

import json
import os
import logging
from typing import Optional

from .google_utils import CREDENTIALS_FILE, TOKEN_FILE

logger = logging.getLogger(__name__)

RCLONE_CONF_PATH = os.getenv("RCLONE_CONFIG_FILE", os.path.expanduser("~/.config/rclone/rclone.conf"))
DEFAULT_REMOTE_NAME = os.getenv("GDRIVE_RCLONE_REMOTE", "gdrive")


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.debug("Failed to read JSON from %s: %s", path, exc)
        return None


def ensure_rclone_remote(remote_name: str = DEFAULT_REMOTE_NAME) -> bool:
    """
    Ensure an rclone remote exists by writing a config file entry based on existing credentials.

    Returns True if a config file was created or already existed, False on failure.
    """
    # If config already exists and contains the remote, return True
    if os.path.exists(RCLONE_CONF_PATH):
        try:
            with open(RCLONE_CONF_PATH, "r", encoding="utf-8") as f:
                if f"https[{remote_name}]" in f.read() or f"[{remote_name}]" in f.read():
                    logger.debug("rclone config already contains remote %s", remote_name)
                    return True
        except Exception:
            pass

    # Read credentials.json and token.json if available
    creds = _read_json(CREDENTIALS_FILE) if os.path.exists(CREDENTIALS_FILE) else None
    token = _read_json(TOKEN_FILE) if os.path.exists(TOKEN_FILE) else None

    if not creds and not token:
        logger.debug("No credentials or token found to create rclone config")
        return False

    # Attempt to extract client_id/client_secret
    client_id = None
    client_secret = None
    try:
        if creds:
            # Credentials file format has "installed" or "web"
            client_info = creds.get("installed") or creds.get("web") or {}
            client_id = client_info.get("client_id")
            client_secret = client_info.get("client_secret")
    except Exception:
        pass

    # Build minimal rclone config entry
    lines = []
    lines.append(f"[{remote_name}]")
    lines.append("type = drive")
    if client_id:
        lines.append(f"client_id = {client_id}")
    if client_secret:
        lines.append(f"client_secret = {client_secret}")

    # If token has refresh_token, include it (rclone supports token json with access_token/refresh_token)
    if token:
        try:
            # rclone expects a JSON blob in token field
            token_blob = json.dumps(token)
            lines.append(f"token = {token_blob}")
        except Exception:
            logger.debug("Could not serialize token for rclone config")

    # Ensure directory exists
    try:
        os.makedirs(os.path.dirname(RCLONE_CONF_PATH), exist_ok=True)
        # Append or create the config file
        with open(RCLONE_CONF_PATH, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")
        logger.info("Wrote rclone config for remote '%s' to %s", remote_name, RCLONE_CONF_PATH)
        return True
    except Exception as exc:
        logger.error("Failed to write rclone config: %s", exc)
        return False
