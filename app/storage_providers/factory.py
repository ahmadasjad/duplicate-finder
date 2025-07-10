"""
Storage Provider Factory

This module provides a factory pattern for creating storage provider instances.
"""
import logging
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

logger = logging.getLogger(__name__)

class StorageProviderFactory:
    """Factory class for creating storage provider instances"""

    @classmethod
    def create_provider(cls, provider_name: str) -> Optional[BaseStorageProvider]:
        """Create a storage provider instance by name"""

        if provider_name == PROVIDER_LOCAL:
            # Local File System provider does not require authentication
            logger.debug("Creating Local File System provider instance")
            return LocalFileSystemProvider()
        elif provider_name == PROVIDER_GOOGLE_DRIVE:
            # Google Drive provider requires OAuth authentication
            logger.debug("Creating Google Drive provider instance")
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
