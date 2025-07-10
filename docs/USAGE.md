# Usage Guide

This guide explains how to use the Duplicate File Finder application effectively.

## Quick Start

1. **Select Storage Provider**:
   - Open the dropdown menu
   - Choose from:
     - Local Filesystem
     - Google Drive
     - OneDrive
     - Dropbox

2. **Configure Provider**:

   ### Local Filesystem
   - Enter the directory path you want to scan
   - Use the file browser to select folders
   - Supports both absolute and relative paths

   ### Cloud Providers (Google Drive, OneDrive, Dropbox)
   - Click "Authenticate" button
   - Complete the OAuth flow in your browser
   - Grant necessary permissions
   - Credentials are securely stored for future use

3. **Scan for Duplicates**:
   - Click the "Scan" button to start
   - Progress bar shows scanning status
   - Statistics shown:
     - Files scanned
     - Storage space used
     - Number of duplicates found

4. **Review Results**:
   - Duplicate files are grouped together
   - For each file, you can:
     - View file metadata (size, type, dates)
     - Preview content (images and PDFs)
     - See full file path
     - Check file permissions
   - Sort groups by:
     - Total size
     - Number of duplicates
     - File type
     - Creation date

5. **Managing Duplicates**:
   - Select files to remove
   - At least one file must remain in each group
   - Options for each group:
     - Keep newest
     - Keep oldest
     - Keep specific location
   - Batch operations available

## Safety Features

### Deletion Protection
- Cannot delete all copies of a file
- Confirmation required for deletions
- Files moved to trash instead of permanent deletion (where supported)

### Preview Capabilities
- Image preview with zoom
- PDF preview with page navigation
- File info and metadata display
- Last modified dates comparison

### Data Safety
- Read-only access by default
- Explicit confirmation for write operations
- Provider-specific safety features:
  - Google Drive: Uses trash
  - Local: Moves to system trash
  - Cloud: Provider-specific safety mechanisms

## Tips and Best Practices

1. **Scanning Strategy**:
   - Start with smaller directories
   - Use filters to focus on specific file types
   - Exclude system directories

2. **Performance Optimization**:
   - Use specific folders instead of root directories
   - Apply file size filters
   - Use file type filters

3. **Managing Large Results**:
   - Sort by size to handle large files first
   - Use the search function to find specific files
   - Export results for later review

4. **Cloud Provider Tips**:
   - Check quota before scanning
   - Be aware of API rate limits
   - Use cached results when available

## Troubleshooting

### Common Issues
1. **Access Denied**:
   - Check folder permissions
   - Verify provider authentication
   - Ensure sufficient access rights

2. **Scan Performance**:
   - Reduce scan scope
   - Check network connection
   - Monitor system resources

3. **Preview Issues**:
   - Verify file is not corrupted
   - Check file format support
   - Ensure sufficient memory

### Getting Help
- Check the logs in `logs/duplicate_finder.log`
- Review error messages in the UI
- Submit issues on GitHub with logs
