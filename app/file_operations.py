import os
import hashlib

def get_file_hash(file_path):
    """Compute the hash of a file."""
    hash_obj = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def is_file_shourtcut(file_path, file):
    """Check if a file is hidden."""
    return (
        os.path.islink(file_path) 
        or file.lower().endswith('.lnk')
        # or file.lower().endswith('.desktop')
    )
    
def is_file_hidden(file_path, file):
    # Check for Linux/Unix (files starting with a dot are hidden)
    if os.name != 'nt':  # Not Windows
        return file.startswith('.')
    else:  # Windows
        # Check for hidden attribute in Windows
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
        if attrs == -1:
            raise FileNotFoundError(f"{file_path} does not exist")
        return bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN = 2
    
def is_file_for_system(file_path, file):
    if os.name == 'nt' and os.path.isfile(file_path):
        import ctypes
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
            if attrs & 0x4:  # SYSTEM attribute
                return True
        except:
            pass
            
    return False

def scan_directory(directory, exclude_shortcuts=True, exclude_hidden=True, exclude_system=True, min_size_kb=0):
    """Scan directory and identify duplicates with optional filters.
    
    Args:
        directory: Path to directory to scan
        exclude_shortcuts: Whether to exclude shortcut files (.lnk on Windows, .desktop on Linux) and symbolic links
        exclude_hidden: Whether to exclude hidden files
        exclude_system: Whether to exclude system files
        min_size_kb: Minimum file size in KB to include
        
    Returns:
        Dictionary of duplicate file groups
    """
    file_dict = {}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip files based on filters
            if exclude_shortcuts and is_file_shourtcut(file_path, file):
                continue
                
            if exclude_hidden and is_file_hidden(file_path, file):
                continue
                
            if exclude_system and is_file_for_system(file_path, file):
                continue
                    
            # Check minimum size
            try:
                file_size = os.path.getsize(file_path) / 1024  # Convert to KB
                if file_size < min_size_kb:
                    continue
            except OSError:
                continue
                
            # Add to duplicates if it passes all filters
            file_hash = get_file_hash(file_path)
            if file_hash not in file_dict:
                file_dict[file_hash] = []
            file_dict[file_hash].append(file_path)
            
    return {k: v for k, v in file_dict.items() if len(v) > 1}

def delete_selected_files(selected_files):
    """Delete selected duplicate files."""
    for file in selected_files:
        os.remove(file)
