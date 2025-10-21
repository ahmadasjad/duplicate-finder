"""
Mount manager for Google Drive using rclone.

Responsibilities:
- mount_google_drive(): start rclone mount (background) and verify mount
- unmount_google_drive(): unmount and stop rclone process
- is_mounted(): check mountpoint
- get_mount_status(): return simple status dict

Notes:
- This implementation expects an rclone remote already configured (env GDRIVE_RCLONE_REMOTE).
- Mounting is only allowed if token.json exists (basic auth gate).
- Uses /tmp/rclone_gdrive.pid to persist the subprocess PID within the container lifetime.
"""
from __future__ import annotations

import os
import time
import shlex
import signal
import logging
import subprocess
from typing import Optional, Dict

from .google_utils import TOKEN_FILE

logger = logging.getLogger(__name__)

# Environment-configurable defaults
RCLONE_REMOTE = os.getenv("GDRIVE_RCLONE_REMOTE", "gdrive")
MOUNT_PATH = os.getenv("GDRIVE_MOUNT_PATH", "/mnt/gdrive")
VFS_CACHE_MODE = os.getenv("GDRIVE_VFS_CACHE_MODE", "writes")
VFS_CACHE_MAX_SIZE = os.getenv("GDRIVE_VFS_CACHE_MAX_SIZE", "1G")
VFS_READ_CHUNK_SIZE = os.getenv("GDRIVE_VFS_READ_CHUNK_SIZE", "128M")
DIR_CACHE_TIME = os.getenv("GDRIVE_DIR_CACHE_TIME", "5m")
POLL_INTERVAL = os.getenv("GDRIVE_POLL_INTERVAL", "15s")
ALLOW_OTHER = os.getenv("GDRIVE_ALLOW_OTHER", "true").lower() in ("1", "true", "yes")
READ_ONLY = os.getenv("GDRIVE_MOUNT_READONLY", "false").lower() in ("1", "true", "yes")
RCLONE_LOG = os.getenv("RCLONE_MOUNT_LOG", "/var/log/rclone-mount.log")
PID_FILE = os.getenv("RCLONE_PID_FILE", "/tmp/rclone_gdrive.pid")
RCLONE_BIN = os.getenv("RCLONE_BIN", "rclone")


def _pid_write(pid: int) -> None:
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
    except Exception as exc:
        logger.debug("Failed to write pid file: %s", exc)


def _pid_read() -> Optional[int]:
    try:
        if not os.path.exists(PID_FILE):
            return None
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _pid_clear() -> None:
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as exc:
        logger.debug("Failed to clear pid file: %s", exc)


def is_authenticated() -> bool:
    """Basic gate: require token file to exist before allowing mount."""
    try:
        return os.path.exists(TOKEN_FILE)
    except Exception:
        return False


def is_mounted(path: str = MOUNT_PATH) -> bool:
    """Check whether the given path is a FUSE mount."""
    try:
        # os.path.ismount works for typical mounts
        if os.path.ismount(path):
            return True
        # Fallback: attempt to stat the mountpoint and list it
        try:
            os.listdir(path)
            # If the mountpoint contains rclone-specific marker files, assume mounted
            return False  # default fallback - safer to return False
        except OSError:
            # If listing fails due to unmounted FUSE, treat as not mounted
            return False
    except Exception as exc:
        logger.debug("is_mounted check failed: %s", exc)
        return False


def _build_rclone_command(remote: str = RCLONE_REMOTE, mount_path: str = MOUNT_PATH) -> list[str]:
    """Construct the rclone mount command as a list for subprocess."""
    # Allow specifying explicit rclone config file via env var RCLONE_CONFIG_FILE
    rclone_config = os.getenv("RCLONE_CONFIG_FILE", os.path.expanduser("~/.config/rclone/rclone.conf"))

    flags = [
        "--vfs-cache-mode", VFS_CACHE_MODE,
        "--vfs-cache-max-size", VFS_CACHE_MAX_SIZE,
        "--vfs-read-chunk-size", VFS_READ_CHUNK_SIZE,
        "--dir-cache-time", DIR_CACHE_TIME,
        "--poll-interval", POLL_INTERVAL,
        "--log-file", RCLONE_LOG,
        "--log-level", "INFO",
    ]
    if ALLOW_OTHER:
        flags += ["--allow-other"]
    if READ_ONLY:
        flags += ["--read-only"]

    # If a config file exists, pass it explicitly to rclone to avoid relying on default locations
    cmd = [RCLONE_BIN]
    if rclone_config and os.path.exists(rclone_config):
        cmd += ["--config", rclone_config]
    cmd += ["mount", f"{remote}:", mount_path] + flags
    return cmd


def mount_google_drive(timeout: int = 30) -> bool:
    """
    Attempt to mount the configured rclone remote to MOUNT_PATH.

    Returns True if mounted successfully, False otherwise.
    """
    logger.info("Attempting to mount Google Drive remote '%s' at '%s'", RCLONE_REMOTE, MOUNT_PATH)

    if not is_authenticated():
        logger.error("Mount prevented: Google Drive authentication required (missing token).")
        return False

    # Basic check: ensure token.json contains a refresh_token; rclone needs it for long-lived mounts
    try:
        import json
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r", encoding="utf-8") as tf:
                token_obj = json.load(tf)
            if token_obj and not token_obj.get("refresh_token"):
                logger.error(
                    "Mount prevented: token.json does not contain a refresh_token. "
                    "Re-authenticate via the web flow in the app to obtain a refresh token "
                    "or run `rclone config reconnect %s:` inside the container after initial auth.",
                    RCLONE_REMOTE,
                )
                return False
    except Exception as exc:
        logger.debug("Could not inspect token file for refresh_token: %s", exc)

    # Ensure rclone remote config exists (best-effort)
    try:
        from .rclone_config import ensure_rclone_remote
    except Exception:
        ensure_rclone_remote = None

    if ensure_rclone_remote:
        try:
            ok = ensure_rclone_remote(RCLONE_REMOTE)
            if not ok:
                logger.warning("rclone config not created for remote '%s'. Mount will likely fail.", RCLONE_REMOTE)
        except Exception as exc:
            logger.debug("Error ensuring rclone config: %s", exc)
    else:
        logger.debug('ensure_rclone_remote is not available')

    if is_mounted(MOUNT_PATH):
        logger.info("Mount point already mounted: %s", MOUNT_PATH)
        return True

    # Ensure mount path exists
    try:
        os.makedirs(MOUNT_PATH, exist_ok=True)
    except Exception as exc:
        logger.error("Failed to create mount path %s: %s", MOUNT_PATH, exc)
        return False

    cmd = _build_rclone_command()
    logger.debug("rclone command: %s", " ".join(shlex.quote(p) for p in cmd))

    try:
        # Start rclone as background process and capture stderr to log file for diagnostics
        with open(RCLONE_LOG, "a+") as logf:
            proc = subprocess.Popen(cmd, stdout=logf, stderr=logf, start_new_session=True)
        _pid_write(proc.pid)
        logger.info("Started rclone process with pid %s", proc.pid)

        # Wait briefly for mount to appear
        start = time.time()
        while time.time() - start < timeout:
            if is_mounted(MOUNT_PATH):
                logger.info("Mount successful: %s", MOUNT_PATH)
                return True
            time.sleep(0.5)

        logger.warning("Mount did not appear within timeout (%ds). Check %s for logs.", timeout, RCLONE_LOG)
        return False

    except FileNotFoundError:
        logger.error("rclone binary not found. Make sure rclone is installed and available in PATH.")
        return False
    except Exception as exc:
        logger.exception("Failed to start rclone mount: %s", exc)
        return False


def unmount_google_drive(force: bool = False) -> bool:
    """
    Unmount the configured mount path and stop the rclone process if running.

    Returns True if unmount succeeded or was not mounted.
    """
    logger.info("Attempting to unmount Google Drive at %s", MOUNT_PATH)
    pid = _pid_read()

    # Try fusermount/umount first
    try:
        if is_mounted(MOUNT_PATH):
            # prefer fusermount -u
            try:
                subprocess.run(["fusermount", "-u", MOUNT_PATH], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # Fallback to umount
                try:
                    subprocess.run(["umount", MOUNT_PATH], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    logger.debug("Unmount commands failed: %s", e)
                    if not force:
                        return False
        else:
            logger.info("Mount path not mounted: %s", MOUNT_PATH)
    except Exception as exc:
        logger.debug("Error during unmount attempt: %s", exc)

    # If we have a recorded pid, try to terminate it
    if pid:
        try:
            logger.debug("Killing rclone process pid %s", pid)
            os.kill(pid, signal.SIGTERM)
            # Give process time to exit
            time.sleep(1)
            try:
                os.kill(pid, 0)
                # still exists
                logger.debug("Process still alive after SIGTERM, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)
            except OSError:
                # process gone
                pass
        except Exception as exc:
            logger.debug("Failed to kill rclone process %s: %s", pid, exc)

    _pid_clear()
    logger.info("Unmount sequence completed for %s", MOUNT_PATH)
    return True


def get_mount_status() -> Dict[str, object]:
    """Return a small status dictionary about mount."""
    status = {
        "mount_path": MOUNT_PATH,
        "remote": RCLONE_REMOTE,
        "mounted": is_mounted(MOUNT_PATH),
        "pid": _pid_read(),
        "auth_present": is_authenticated(),
        "log_file": RCLONE_LOG,
    }
    return status
