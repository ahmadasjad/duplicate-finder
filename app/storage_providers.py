"""
Storage Providers Module

This module provides a unified interface for different storage providers.
The implementation has been moved to the storage_providers package for better organization.
"""

# Import all storage providers from the new package structure
from .storage_providers import (
    BaseStorageProvider,
    LocalFileSystemProvider,
    GoogleDriveProvider,
    OneDriveProvider,
    DropboxProvider,
    get_storage_providers,
    get_provider_info
)

# Keep backward compatibility
__all__ = [
    'BaseStorageProvider',
    'LocalFileSystemProvider',
    'GoogleDriveProvider', 
    'OneDriveProvider',
    'DropboxProvider',
    'get_storage_providers',
    'get_provider_info'
]
