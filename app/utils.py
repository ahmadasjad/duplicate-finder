"""Utility functions for the application."""

import os
from datetime import datetime

def human_readable_size(size_in_bytes, upto_unit=None):
    """Convert bytes to a human-readable format, optionally up to a specified unit (e.g., 'MB')."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for unit in units:
        if upto_unit and unit == upto_unit:
            return f"{size_in_bytes:.2f} {unit}"
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} {units[-1]}"

def format_timestamp(timestamp):
    """Format timestamp to human-readable format."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_file_info(file_path):
    """
    Get details of a file (name, size, extension, timestamps).
    :param file_path: Path to the file
    :return: Dictionary with file details
    """
    stat = os.stat(file_path)
    return {
        "name": os.path.basename(file_path),
        "size": os.path.getsize(file_path),
        "extension": os.path.splitext(file_path)[-1].lower(),
        "created": format_timestamp(stat.st_ctime),
        "modified": format_timestamp(stat.st_mtime)
    }

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    if '.' in filename:
        return filename.rsplit('.', 1)[-1].lower()
    return ''

def format_iso_timestamp(timestamp: str, default: str = 'Unknown') -> str:
    """Format ISO timestamp to readable format"""
    if not timestamp:
        return default
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return timestamp
