# Storage Providers Package

This package contains all storage provider implementations for the Duplicate File Finder application. Each provider implements a common interface defined by the `BaseStorageProvider` class.

## Directory Structure

```
storage_providers/
├── __init__.py          # Package initialization and factory functions
├── base.py              # Base storage provider abstract class
├── factory.py           # Factory pattern for creating provider instances
├── local_filesystem.py  # Local file system provider implementation
├── google_drive.py      # Google Drive provider (placeholder)
├── onedrive.py          # OneDrive provider (placeholder)
└── dropbox.py           # Dropbox provider (placeholder)
```

## Architecture

### Base Provider (`base.py`)
- Abstract base class that defines the interface all providers must implement
- Includes methods for authentication, directory input, scanning, file operations, etc.

### Factory Pattern (`factory.py`)
- `StorageProviderFactory` class for creating provider instances
- Provides available providers list and validation
- Enables easy addition of new providers

### Individual Providers
Each provider file contains a single class that implements the `BaseStorageProvider` interface:

- **LocalFileSystemProvider**: Handles local file system and Docker-mounted volumes
- **GoogleDriveProvider**: Placeholder for Google Drive integration
- **OneDriveProvider**: Placeholder for Microsoft OneDrive integration
- **DropboxProvider**: Placeholder for Dropbox integration

## Adding New Providers

To add a new storage provider:

1. Create a new file (e.g., `aws_s3.py`)
2. Implement the `BaseStorageProvider` interface
3. Add the provider to the factory in `factory.py`
4. Update the configuration in `app/config.py`
5. Import in `__init__.py`

## Usage

```python
from app.storage_providers import get_storage_providers, StorageProviderFactory

# Get all enabled providers
providers = get_storage_providers()

# Create a specific provider
provider = StorageProviderFactory.create_provider("Local File System")

# Check if provider is available
available = StorageProviderFactory.is_provider_available("Google Drive")
```

## Provider Interface

All providers must implement these methods:

- `authenticate()`: Handle provider-specific authentication
- `get_directory_input_widget()`: Return Streamlit widget for directory selection
- `scan_directory()`: Scan and return duplicate file groups
- `delete_files()`: Delete specified files
- `get_file_info()`: Get file metadata
- `preview_file()`: Display file preview in Streamlit

## Configuration

Provider availability is controlled by the `STORAGE_PROVIDERS_CONFIG` in `app/config.py`. Each provider can be enabled/disabled and configured with provider-specific settings.
