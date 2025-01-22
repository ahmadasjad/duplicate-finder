import os
import hashlib

def get_file_hash(file_path):
    """Compute the hash of a file."""
    hash_obj = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def scan_directory(directory):
    """Scan directory and identify duplicates."""
    file_dict = {}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_hash = get_file_hash(file_path)
            if file_hash not in file_dict:
                file_dict[file_hash] = []
            file_dict[file_hash].append(file_path)
    return {k: v for k, v in file_dict.items() if len(v) > 1}

def delete_selected_files(selected_files):
    """Delete selected duplicate files."""
    for file in selected_files:
        os.remove(file)
