def human_readable_size(size_in_bytes):
    """Convert bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"

import os

def get_file_info(file_path):
    """
    Get details of a file (name, size, extension).
    :param file_path: Path to the file
    :return: Dictionary with file details
    """
    return {
        "name": os.path.basename(file_path),
        "size": os.path.getsize(file_path),
        "extension": os.path.splitext(file_path)[-1].lower()
    }
