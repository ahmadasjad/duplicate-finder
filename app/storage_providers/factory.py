"""
Storage Provider Factory

This module provides a factory pattern for creating storage provider instances.
"""

from typing import Dict, Optional
from .base import BaseStorageProvider
from .local_filesystem import LocalFileSystemProvider
from .google_drive import GoogleDriveProvider
from .onedrive import OneDriveProvider
from .dropbox import DropboxProvider


class StorageProviderFactory:
    """Factory class for creating storage provider instances"""
    
    _providers = {
        "Local File System": LocalFileSystemProvider,
        "Google Drive": GoogleDriveProvider,
        "OneDrive": OneDriveProvider,
        "Dropbox": DropboxProvider
    }
    
    @classmethod
    def create_provider(cls, provider_name: str) -> Optional[BaseStorageProvider]:
        """Create a storage provider instance by name"""
        provider_class = cls._providers.get(provider_name)
        if provider_class:
            return provider_class()
        return None
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        """Get list of available provider names and their descriptions"""
        return {
            "Local File System": "Scan files on the local file system or mounted volumes",
            "Google Drive": "Scan files in Google Drive (Coming Soon)",
            "OneDrive": "Scan files in Microsoft OneDrive (Coming Soon)",
            "Dropbox": "Scan files in Dropbox (Coming Soon)"
        }
    
    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider is available"""
        return provider_name in cls._providers
