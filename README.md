# Duplicate File Finder

A Streamlit-based application to find and manage duplicate files in a directory.

## Features
- Scan directories for duplicate files
- Preview files (images and PDFs)
- View detailed file metadata (name, path, size, extension, creation/modification dates)
- Safely delete duplicate files while preserving at least one copy
- Group duplicates for easy comparison

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
