"""
Storage Provider Factory

This module provides a factory pattern for creating storage provider instances.
"""

from typing import Dict, Optional, Type
from .base import BaseStorageProvider
from .local_filesystem import LocalFileSystemProvider
from .google_drive import GoogleDriveProvider
from .onedrive import OneDriveProvider
from .dropbox import DropboxProvider

PROVIDER_LOCAL = "Local File System"
PROVIDER_GOOGLE_DRIVE = "Google Drive"
PROVIDER_ONEDRIVE = "OneDrive"
PROVIDER_DROPBOX = "Dropbox"

class StorageProviderFactory:
    """Factory class for creating storage provider instances"""

    _providers: Dict[str, Type[BaseStorageProvider]] = {
        PROVIDER_LOCAL: LocalFileSystemProvider,
        PROVIDER_GOOGLE_DRIVE: GoogleDriveProvider,
        PROVIDER_ONEDRIVE: OneDriveProvider,
        PROVIDER_DROPBOX: DropboxProvider
    }

    @classmethod
    def create_provider(cls, provider_name: str) -> Optional[BaseStorageProvider]:
        """Create a storage provider instance by name"""
        # provider_class = cls._providers.get(provider_name)

        if provider_name == PROVIDER_LOCAL:
            # Local File System provider does not require authentication
            return LocalFileSystemProvider()
        elif provider_name == PROVIDER_GOOGLE_DRIVE:
            # Google Drive provider requires OAuth authentication
            # if not GoogleDriveProvider.is_authenticated():
            return GoogleDriveProvider()
        elif provider_name == PROVIDER_ONEDRIVE:
            # OneDrive provider requires OAuth authentication (Coming Soon)
            return OneDriveProvider()
        elif provider_name == PROVIDER_DROPBOX:
            # Dropbox provider requires OAuth authentication (Coming Soon)
            return DropboxProvider()
        return None

    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        """Get list of available provider names and their descriptions"""
        return {
            PROVIDER_LOCAL: "Scan files on the local file system or mounted volumes",
            PROVIDER_GOOGLE_DRIVE: "Scan files in Google Drive with OAuth authentication",
            PROVIDER_ONEDRIVE: "Scan files in Microsoft OneDrive (Coming Soon)",
            PROVIDER_DROPBOX: "Scan files in Dropbox (Coming Soon)"
        }

    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider is available"""
        return provider_name in cls._providers
