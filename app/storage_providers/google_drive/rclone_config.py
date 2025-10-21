"""
Robust helper to generate an rclone config entry for a Google Drive remote.

Behavior:
- Writes config to path specified by RCLONE_CONFIG_FILE environment variable or
  defaults to ~/.config/rclone/rclone.conf.
- If the remote already exists in the config file, does nothing.
- Attempts to read client_id/client_secret from credentials.json and token.json
  (used by the existing Google auth flow) and writes a minimal, valid rclone
  config section for a Google Drive remote.
- Sets file permissions to 600 when creating the config file.

Notes:
- This is a best-effort helper. If your environment uses a different rclone
  config location, set RCLONE_CONFIG_FILE accordingly.
- Do NOT commit the generated config file to source control. Keep it in .gitignore.
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
        logger.debug("rclone_config: failed to read JSON %s: %s", path, exc)
        return None


def _remote_exists_in_config(path: str, remote_name: str) -> bool:
    try:
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Look for a section header like [remote_name]
        return f"[{remote_name}]" in content
    except Exception as exc:
        logger.debug("rclone_config: error checking config file: %s", exc)
        return False


def _write_config_atomic(path: str, content: str) -> bool:
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
        try:
            os.chmod(path, 0o600)
        except Exception:
            # Not critical, log and continue
            logger.debug("rclone_config: failed to chmod %s", path)
        return True
    except Exception as exc:
        logger.error("rclone_config: failed to write config to %s: %s", path, exc)
        return False


def ensure_rclone_remote(remote_name: str = DEFAULT_REMOTE_NAME) -> bool:
    """
    Ensure an rclone remote exists for `remote_name`. Returns True if the remote
    exists or was created successfully, False otherwise.
    """
    try:
        # If config exists and already contains the remote, attempt to update the token
        if _remote_exists_in_config(RCLONE_CONF_PATH, remote_name):
            logger.debug("rclone_config: remote '%s' already present in %s", remote_name, RCLONE_CONF_PATH)
            # If we have a fresh token, attempt to inject/update the token line in the existing config
            if token:
                try:
                    # Read existing config
                    with open(RCLONE_CONF_PATH, "r", encoding="utf-8") as f:
                        cfg = f.read()
                    # Locate the remote section
                    import re
                    pattern = rf"(?m)^\[{re.escape(remote_name)}\]\s*$"
                    m = re.search(pattern, cfg)
                    if m:
                        start = m.end()
                        # Find next section header after start
                        m2 = re.search(r"(?m)^\[.*\]\s*$", cfg[start:])
                        end = start + m2.start() if m2 else len(cfg)
                        section = cfg[start:end]
                        # Build normalized token blob (same logic used when creating new config)
                        try:
                            normalized = {}
                            access_value = token.get("access_token") or token.get("token") or token.get("accessToken")
                            if access_value:
                                normalized["access_token"] = access_value
                            if token.get("refresh_token"):
                                normalized["refresh_token"] = token.get("refresh_token")
                            if token.get("token_type"):
                                normalized["token_type"] = token.get("token_type")
                            if token.get("expiry"):
                                normalized["expiry"] = token.get("expiry")
                            if not normalized and isinstance(token, dict):
                                normalized = token
                            token_blob = json.dumps(normalized, separators=(",", ":"))
                            token_line = f"token = {token_blob}\n"
                        except Exception:
                            logger.debug("rclone_config: failed to serialize token for remote '%s' during update", remote_name)
                            return True
                        # Replace existing token line if present
                        if re.search(r"(?m)^\s*token\s*=", section):
                            section_new = re.sub(r"(?m)^\s*token\s*=.*(?:\r?\n)?", token_line, section)
                        else:
                            # Insert token line after client_secret if present, else after type line
                            m_client = re.search(r"(?m)^\s*client_secret\s*=.*(?:\r?\n)?", section)
                            if m_client:
                                insert_offset = m_client.end()
                            else:
                                m_type = re.search(r"(?m)^\s*type\s*=.*(?:\r?\n)?", section)
                                insert_offset = m_type.end() if m_type else 0
                            section_new = section[:insert_offset] + token_line + section[insert_offset:]
                        # Rebuild config and write atomically
                        new_cfg = cfg[:start] + section_new + cfg[end:]
                        _write_config_atomic(RCLONE_CONF_PATH, new_cfg)
                        logger.info("rclone_config: updated token for remote '%s' in %s", remote_name, RCLONE_CONF_PATH)
                        return True
                except Exception as exc:
                    logger.error("rclone_config: failed to update token for existing remote '%s': %s", remote_name, exc)
                    return True
            # No token to update, nothing more to do
            return True

        # Read credentials and token if available
        creds = _read_json(CREDENTIALS_FILE) if os.path.exists(CREDENTIALS_FILE) else None
        token = _read_json(TOKEN_FILE) if os.path.exists(TOKEN_FILE) else None

        if not creds and not token:
            logger.debug("rclone_config: no credentials or token available to create config for '%s'", remote_name)
            return False

        # Extract client id/secret if available
        client_id = None
        client_secret = None
        if creds:
            client_block = creds.get("installed") or creds.get("web") or {}
            client_id = client_block.get("client_id")
            client_secret = client_block.get("client_secret")

        # Build INI section for rclone
        lines = []
        lines.append(f"[{remote_name}]")
        lines.append("type = drive")
        if client_id:
            lines.append(f"client_id = {client_id}")
        if client_secret:
            lines.append(f"client_secret = {client_secret}")

        if token:
            try:
                # Normalize token to the structure rclone expects.
                # The app's token.json may use different keys (e.g. "token" instead of "access_token").
                # Build a minimal dict containing keys rclone understands: access_token, refresh_token, token_type, expiry.
                normalized = {}
                # Common possible access token keys from various flows
                access_value = token.get("access_token") or token.get("token") or token.get("accessToken")
                if access_value:
                    normalized["access_token"] = access_value
                # refresh token
                if token.get("refresh_token"):
                    normalized["refresh_token"] = token.get("refresh_token")
                # token type (optional)
                if token.get("token_type"):
                    normalized["token_type"] = token.get("token_type")
                # expiry (keep as-is if present)
                if token.get("expiry"):
                    normalized["expiry"] = token.get("expiry")
                # If we couldn't map any of the common fields, fall back to writing the original token dict
                if not normalized and isinstance(token, dict):
                    normalized = token
                # rclone expects token to be a JSON blob value (no extra quotes)
                token_blob = json.dumps(normalized, separators=(",", ":"))
                lines.append(f"token = {token_blob}")
            except Exception:
                logger.debug("rclone_config: failed to serialize token for remote '%s'", remote_name)

        # Minimal defaults to improve chance of working
        lines.append("team_drive =")
        content = "\n".join(lines) + "\n\n"

        # If a config file already exists, append to it; else create new file
        if os.path.exists(RCLONE_CONF_PATH):
            try:
                with open(RCLONE_CONF_PATH, "a", encoding="utf-8") as f:
                    f.write(content)
                logger.info("rclone_config: appended remote '%s' to %s", remote_name, RCLONE_CONF_PATH)
                return True
            except Exception as exc:
                logger.error("rclone_config: failed to append to %s: %s", RCLONE_CONF_PATH, exc)
                return False
        else:
            # Write atomically
            written = _write_config_atomic(RCLONE_CONF_PATH, content)
            if written:
                logger.info("rclone_config: created rclone config at %s with remote '%s'", RCLONE_CONF_PATH, remote_name)
            return written

    except Exception as exc:
        logger.exception("rclone_config: unexpected error ensuring remote '%s': %s", remote_name, exc)
        return False
