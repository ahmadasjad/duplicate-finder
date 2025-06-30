"""
Storage Providers Package

This package contains all storage provider implementations for the duplicate finder.
Each provider implements the BaseStorageProvider interface.
"""

from .base import BaseStorageProvider
from .local_filesystem import LocalFileSystemProvider
from .google_drive import GoogleDriveProvider
from .onedrive import OneDriveProvider
from .dropbox import DropboxProvider
from .factory import StorageProviderFactory

# Factory function to get storage providers
def get_storage_providers():
    """Get all available storage providers"""
    from app.config import STORAGE_PROVIDERS_CONFIG

    enabled_providers = {}

    # Use factory to create provider instances
    for name in StorageProviderFactory.get_available_providers().keys():
        if STORAGE_PROVIDERS_CONFIG.get(name, {}).get("enabled", False):
            provider = StorageProviderFactory.create_provider(name)
            if provider:
                enabled_providers[name] = provider

    return enabled_providers


def get_provider_info():
    """Get information about all storage providers"""
    from app.config import STORAGE_PROVIDERS_CONFIG
    return STORAGE_PROVIDERS_CONFIG


__all__ = [
    'BaseStorageProvider',
    'LocalFileSystemProvider',
    'GoogleDriveProvider',
    'OneDriveProvider',
    'DropboxProvider',
    'StorageProviderFactory',
    'get_storage_providers',
    'get_provider_info'
]
