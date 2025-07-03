"""
Configuration settings for different storage providers
"""
import os
import logging

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
        "enabled": True,  # Enable to show in dropdown
        "requires_auth": True,
        "description": "Scan files in your OneDrive",
        "features": ["basic_preview", "deletion"],
        "auth_scopes": ["Files.ReadWrite.All"]
    },
    "Dropbox": {
        "enabled": True,  # Enable to show in dropdown
        "requires_auth": True,
        "description": "Scan files in your Dropbox",
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

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.DEBUG).upper()   # Set to "INFO" or "ERROR" in production
