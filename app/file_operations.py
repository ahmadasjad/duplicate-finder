"""Module for file operations."""

import os
import hashlib

def get_file_hash(file_path):
    """Compute the hash of a file."""
    hash_obj = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def is_file_shortcut(file_path, file):
    """Check if a file is a shortcut or symlink."""
    return (
        os.path.islink(file_path)
        or file.lower().endswith('.lnk')
        # or file.lower().endswith('.desktop')
    )

def is_file_hidden(file_path, file):
    """Check if a file is hidden."""
    if os.name != 'nt':  # Unix-like systems
        return file.startswith('.')

    # Windows systems
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
        return attrs != -1 and bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN = 2
    except (OSError, AttributeError):
        return False

def is_file_for_system(file_path, file):
    """Check if a file is a system file."""
    if os.name == 'nt' and os.path.isfile(file_path):
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
            return attrs != -1 and bool(attrs & 0x4)  # FILE_ATTRIBUTE_SYSTEM = 0x4
        except (OSError, AttributeError):
            return False
    return False

def delete_selected_files(selected_files):
    """Delete selected duplicate files."""
    for file in selected_files:
        os.remove(file)
