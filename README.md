# Duplicate File Finder

A Streamlit-based application to find and manage duplicate files in a directory.

## Features
- Scan directories for duplicate files
- Preview files (images and PDFs)
- View detailed file metadata (name, path, size, extension, creation/modification dates)
- Safely delete duplicate files while preserving at least one copy
- Group duplicates for easy comparison

## Installation

### Manual Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/duplicate-finder.git
cd duplicate-finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Docker Installation

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

### Manual Run

To start the application:
```bash
streamlit run app/main.py
```

### Docker Run

To start the application using Docker:
```bash
docker-compose up
```

The application will open in your default web browser at `http://localhost:8501`

## Usage

1. Enter the directory path you want to scan in the input field
2. Click "Scan for Duplicates"
3. Review the duplicate file groups:
   - Each group shows previews and metadata for duplicate files
   - Select files to delete (at least one file must remain in each group)
4. Click "Delete Selected Files" to remove duplicates

## Requirements

- Python 3.8+
- Streamlit
- Pillow (for image previews)
- pdfplumber (for PDF previews)

## File Metadata

For each file, the application displays:
- File name
- Full path
- File extension
- File size (human-readable format)
- Creation date/time
- Last modification date/time

## Safety Features

- Prevents accidental deletion of all files in a group
- Shows previews before deletion
- Requires explicit confirmation for deletions

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## License

MIT License
