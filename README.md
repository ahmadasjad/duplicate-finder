# Duplicate File Finder

A Streamlit-based application to find and manage duplicate files across multiple storage providers including local filesystem, Google Drive, OneDrive, and Dropbox.

## Table of Contents
- [Features](#features)
  - [Safety Features](#safety-features)
- [Storage Providers](#storage-providers)
  - [Provider Features](#provider-features)
- [Installation](#installation)
- [Usage](#usage)
- [Requirements](#requirements)
- [File Metadata](#file-metadata)
- [Development](#development)
  - [Architecture](#architecture)
    - [Adding New Providers](#adding-new-providers)
  - [Project Structure](#project-structure)
  - [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

## Features
- **Multi-Provider Support**: Scan files from local filesystem and cloud storage providers
- **Modular Architecture**: Extensible storage provider system with factory pattern
- **File Preview**: View images and PDFs directly in the app
- **Detailed Metadata**: File name, path, size, extension, creation/modification dates
- **Docker Support**: Easy deployment with Docker Compose
- **Provider Selection**: Dropdown interface to choose between storage providers

### Safety Features
- **Deletion Protection**: Prevents removing all files in a duplicate group
- **Preview Before Action**: Visual confirmation of files before deletion
- **Explicit Confirmation**: Requires user confirmation for destructive operations
- **Read-Only Mounts**: Docker volumes mounted read-only by default for safety
- **Provider Isolation**: Each storage provider operates independently

## Storage Providers

The application supports multiple storage providers through a modular architecture:

- **Local Filesystem**: Scan directories on your local machine or mounted drives
- **Google Drive**: Scan files in your Google Drive (authentication required)
- **OneDrive**: Scan files in your Microsoft OneDrive (authentication required)
- **Dropbox**: Scan files in your Dropbox (authentication required)

Each provider is implemented as a separate module with a common interface, making it easy to add new providers.

### Provider Features

#### Google Drive Integration
- Browser-based OAuth2 authentication
- File metadata caching for faster rescans
- Support for Team Drives and shared folders
- Safe file operations (moves to trash instead of permanent deletion)
- See [Google Drive Setup Guide](docs/GOOGLE_DRIVE_SETUP.md) for detailed instructions

## Installation

For detailed installation instructions, including Google Colab, Docker, and manual installation methods, please see the [Installation Guide](docs/INSTALLATION.md).

Available installation methods:
- Google Colab (quick start with no local setup)
- Docker (recommended for most users)
- Manual installation (for development)

## Usage

For detailed usage instructions, including best practices, troubleshooting, and advanced features, please see the [Usage Guide](docs/USAGE.md).

Quick start:
1. Select a storage provider (Local Filesystem, Google Drive, OneDrive, Dropbox)
2. Configure access and scan settings
3. Review and manage duplicate files with built-in safety features
4. Preview and verify files before any actions
5. Safely remove unnecessary duplicates

## Requirements

- Python 3.8+
- Streamlit
- Pillow (for image previews)
- pdfplumber (for PDF previews)
- Docker & Docker Compose (for containerized deployment)



## File Metadata

For each file, the application displays:
- File name and full path
- File extension and MIME type
- File size (human-readable format)
- Creation and modification timestamps
- Provider-specific metadata (when available)

## Development

### Architecture

The application uses a modular storage provider architecture:

```
app/storage_providers/
├── __init__.py          # Package initialization
├── base.py              # BaseStorageProvider abstract class
├── factory.py           # StorageProviderFactory for provider management
├── local_filesystem.py  # Local file system implementation
├── google_drive.py      # Google Drive implementation (placeholder)
├── onedrive.py          # OneDrive implementation (placeholder)
├── dropbox.py           # Dropbox implementation (placeholder)
└── README.md            # Provider architecture documentation
```

**Key Components:**
- **BaseStorageProvider**: Abstract base class defining the common interface
- **StorageProviderFactory**: Factory pattern for creating and managing providers
- **Provider Implementations**: Each cloud service has its own dedicated module
- **Legacy Compatibility**: The main `storage_providers.py` imports from the new structure

#### Adding New Providers

To add a new storage provider:

1. Create a new file in `app/storage_providers/`
2. Inherit from `BaseStorageProvider`
3. Implement required methods: `connect()`, `list_files()`, `delete_file()`
4. Add to the factory in `factory.py`
5. Update UI dropdown in `app/ui.py`

### Project Structure
```
duplicate-finder/
├── app/                     # Main application code
│   ├── storage_providers/   # Modular provider system
│   ├── main.py             # Streamlit entry point
│   ├── ui.py               # User interface components
│   ├── file_operations.py  # File handling utilities
│   └── utils.py            # Helper functions
├── test_data/              # Sample files for testing
├── docker-compose.yml      # Docker configuration
├── Dockerfile              # Container build instructions
├── requirements.txt        # Python dependencies
└── start-docker.sh         # Quick start script
```

### Running Tests
```bash
# Manual testing with sample data
cd test_data
# Create some duplicate files for testing

# Run the app and test provider functionality
streamlit run app/main.py
```

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## License

MIT License
