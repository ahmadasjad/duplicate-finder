# Duplicate File Finder

A Streamlit-based application to find and manage duplicate files across multiple storage providers including local filesystem, Google Drive, OneDrive, and Dropbox.

## Features
- **Multi-Provider Support**: Scan files from local filesystem and cloud storage providers
- **Modular Architecture**: Extensible storage provider system with factory pattern
- **File Preview**: View images and PDFs directly in the app
- **Detailed Metadata**: File name, path, size, extension, creation/modification dates
- **Safe Deletion**: Prevents accidental deletion of all files in a group
- **Docker Support**: Easy deployment with Docker Compose
- **Provider Selection**: Dropdown interface to choose between storage providers

## Storage Providers

The application supports multiple storage providers through a modular architecture:

- **Local Filesystem**: Scan directories on your local machine or mounted drives
- **Google Drive**: Scan files in your Google Drive (authentication required)
- **OneDrive**: Scan files in your Microsoft OneDrive (authentication required)  
- **Dropbox**: Scan files in your Dropbox (authentication required)

Each provider is implemented as a separate module with a common interface, making it easy to add new providers.

## Installation

### Google Colab Installation

1. **Get your ngrok auth token**
   - Create an account at https://ngrok.com/
   - Get your auth token from the dashboard
   - In Google Colab, go to `Tools` → `Secrets` → `Add a new secret`
   - Add a secret named `NGROCK_TOKEN` with your ngrok token as the value

2. **Open the Colab Notebook**
   - Open [duplicate_finder.ipynb](duplicate_finder.ipynb) in Google Colab

3. **Run the Setup Cells**
   - The notebook will:
     - Install required dependencies
     - Clone the repository
     - Set up ngrok authentication
     - Launch the Streamlit app

4. **Access the Application**
   - After running the notebook, you'll see a public URL in the output
   - Click the URL to access the running application

### Manual Installation

For development or custom deployments:

1. Clone this repository:
```bash
git clone https://github.com/yourusername/duplicate-finder.git
cd duplicate-finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app/main.py
```

### Docker Installation (Recommended)

The easiest way to run the application is using Docker Compose:

1. Clone this repository:
```bash
git clone https://github.com/yourusername/duplicate-finder.git
cd duplicate-finder
```

2. Use the provided startup script:
```bash
./start-docker.sh
```

Or manually with Docker Compose:
```bash
docker-compose up --build
```

3. Access the application at `http://localhost:8501`

**Docker Volume Mounts:**
- Your home directory is mounted as `/host_home` (read-only)
- The `test_data` directory is mounted as `/host_test_data` (read-only)
- Additional directories can be added to the `docker-compose.yml` volumes section

### Manual Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/duplicate-finder.git
cd duplicate-finder
```

2. Build the Docker image:
```bash
docker-compose build
```

## Running the Application

### Using Docker (Recommended)

The Docker setup provides an isolated environment with all dependencies:

```bash
# Quick start
./start-docker.sh

# Or manually
docker-compose up --build
```

Access the application at `http://localhost:8501`

### Manual Run

To start the application locally:
```bash
streamlit run app/main.py
```

## Usage

1. **Select Storage Provider**: Choose from the dropdown (Local Filesystem, Google Drive, OneDrive, Dropbox)
2. **Configure Provider**: 
   - For Local Filesystem: Enter directory path to scan
   - For Cloud Providers: Complete authentication flow (if required)
3. **Scan for Duplicates**: Click the scan button to find duplicate files
4. **Review Results**: 
   - View duplicate file groups with previews and metadata
   - Select files to delete (at least one file must remain per group)
5. **Delete Files**: Click "Delete Selected Files" to remove duplicates safely

## Architecture

### Storage Provider System

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

### Adding New Providers

To add a new storage provider:

1. Create a new file in `app/storage_providers/`
2. Inherit from `BaseStorageProvider`
3. Implement required methods: `connect()`, `list_files()`, `delete_file()`
4. Add to the factory in `factory.py`
5. Update UI dropdown in `app/ui.py`

## Requirements

- Python 3.8+
- Streamlit
- Pillow (for image previews)
- pdfplumber (for PDF previews)
- Docker & Docker Compose (for containerized deployment)

## Docker Configuration

The Docker setup includes:

- **Volume Mounts**: Access to host directories for scanning
  - `~/.:/host_home:ro` - Your home directory (read-only)
  - `./test_data:/host_test_data:ro` - Test data directory (read-only)
- **Port Mapping**: `8501:8501` for Streamlit access
- **Environment**: Optimized Python and Streamlit configuration

**Customizing Mounts:**
Edit `docker-compose.yml` to add more directories:
```yaml
volumes:
  - .:/app
  - ~/.:/host_home:ro
  - ./test_data:/host_test_data:ro
  - /path/to/your/data:/host_data:ro  # Add custom paths
```

## File Metadata

For each file, the application displays:
- File name and full path
- File extension and MIME type
- File size (human-readable format)
- Creation and modification timestamps
- Provider-specific metadata (when available)

## Safety Features

- **Deletion Protection**: Prevents removing all files in a duplicate group
- **Preview Before Action**: Visual confirmation of files before deletion
- **Explicit Confirmation**: Requires user confirmation for destructive operations
- **Read-Only Mounts**: Docker volumes mounted read-only by default for safety
- **Provider Isolation**: Each storage provider operates independently

## Development

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
