"""
Configuration settings for different storage providers
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
def load_config():
    load_dotenv()

# Initialize config
load_config()

# Storage provider configurations
STORAGE_PROVIDERS_CONFIG = {
    "Local File System": {
        "enabled": True,
        "requires_auth": False,
        "description": "Scan files on your local computer",
        "features": ["full_preview", "deletion", "advanced_filters"]
    },
    "Google Drive": {
        "enabled": True,  # Enable to show in dropdown
        "requires_auth": True,
        "description": "Scan files in your Google Drive",
        "features": ["basic_preview", "deletion"],
        "auth_scopes": ["https://www.googleapis.com/auth/drive.readonly"]
    },
    "OneDrive": {
        "enabled": False,  # Disabled: Implementation not complete (Coming Soon)
        "requires_auth": True,
        "description": "Scan files in your OneDrive (Coming Soon)",
        "features": ["basic_preview", "deletion"],
        "auth_scopes": ["Files.ReadWrite.All"]
    },
    "Dropbox": {
        "enabled": False,  # Disabled: Implementation not complete (Coming Soon)
        "requires_auth": True,
        "description": "Scan files in your Dropbox (Coming Soon)",
        "features": ["basic_preview", "deletion"]
    }
}

# File type configurations
SUPPORTED_PREVIEW_TYPES = {
    "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"],
    "documents": [".pdf", ".txt", ".md"],
    "videos": [".mp4", ".avi", ".mov", ".mkv"],  # For future implementation
    "audio": [".mp3", ".wav", ".flac"]  # For future implementation
}

# Maximum file sizes for preview (in MB)
MAX_PREVIEW_SIZE = {
    "images": 50,
    "documents": 100,
    "videos": 500,
    "audio": 100
}

# Environment variables with defaults
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO") # INFO, DEBUG, WARNING, ERROR, CRITICAL

# Google Drive related runtime defaults (can be overridden via environment variables)
# - GDRIVE_SCAN_MEDIA_PREFETCH_PROGRESS_PORTION: fraction of overall progress bar
#   allocated to media prefetch stage during a scan (float between 0.0 and 1.0)
# - GDRIVE_DEFAULT_MEDIA_CONCURRENCY: default concurrency for media downloads
def _get_float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

def _get_int_env(name: str, default: int) -> int:
    try:
        val = int(os.getenv(name, str(default)))
        return max(1, val)
    except Exception:
        return default

# Fraction (0.0 - 1.0) of overall progress reserved for media prefetch during scans
GDRIVE_SCAN_MEDIA_PREFETCH_PROGRESS_PORTION = _get_float_env(
    "GDRIVE_SCAN_MEDIA_PREFETCH_PROGRESS_PORTION",
    0.2,
)

# Default concurrency for media fetches (prefetch / thumbnail downloads) for Google Drive
GDRIVE_DEFAULT_MEDIA_CONCURRENCY = _get_int_env(
    "GDRIVE_DEFAULT_MEDIA_CONCURRENCY",
    16,
)

# Memory management settings for Google Drive prefetch operations
GDRIVE_PREFETCH_BATCH_SIZE = _get_int_env(
    "GDRIVE_PREFETCH_BATCH_SIZE",
    10,  # Process 10 files at a time by default
)

GDRIVE_PREFETCH_MAX_MEMORY_MB = _get_int_env(
    "GDRIVE_PREFETCH_MAX_MEMORY_MB",
    500,  # 500MB maximum memory usage by default
)
