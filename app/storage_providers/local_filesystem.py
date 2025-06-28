import os
import hashlib
from typing import Dict, List
from .base import BaseStorageProvider


class LocalFileSystemProvider(BaseStorageProvider):
    """Local file system storage provider"""
    
    def __init__(self):
        super().__init__("Local File System")
    
    def authenticate(self) -> bool:
        """No authentication needed for local file system"""
        return True
    
    def get_directory_input_widget(self):
        """Return text input for local directory path"""
        import streamlit as st
        
        # Show available mount points for Docker users
        st.info("🐳 **Docker Mode Detected**")
        st.markdown("**Available directories to scan:**")
        st.markdown("- `/app/debug/` - Sample debug files")
        st.markdown("- `/app/test_data/` - Test data directory")
        st.markdown("- `/host_home/` - Host home directory (read-only)")
        st.markdown("- `/host_test_data/` - Host test data directory (read-only)")
        st.markdown("- Or enter any other mounted path")
        
        # Provide default directory suggestions
        default_dirs = [
            "/app/debug",
            "/app/test_data", 
            "/host_home",
            "/host_test_data"
        ]
        
        col1, col2 = st.columns([3, 1])
        with col1:
            directory = st.text_input("Enter directory path:", value="/app/test_data")
        with col2:
            if st.button("Browse", help="Quick select common directories"):
                selected = st.selectbox("Quick select:", default_dirs, key="dir_select")
                if selected:
                    st.session_state.directory_input = selected
                    st.rerun()
        
        return directory
    
    def get_file_hash(self, file_path: str) -> str:
        """Compute the hash of a file."""
        hash_obj = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except (OSError, IOError):
            return None
    
    def is_file_shortcut(self, file_path: str, file: str) -> bool:
        """Check if a file is a shortcut or symlink."""
        return (
            os.path.islink(file_path) 
            or file.lower().endswith('.lnk')
        )
    
    def is_file_hidden(self, file_path: str, file: str) -> bool:
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
    
    def is_file_for_system(self, file_path: str, file: str) -> bool:
        """Check if a file is a system file."""
        if os.name == 'nt' and os.path.isfile(file_path):
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(file_path)
                return attrs != -1 and bool(attrs & 0x4)  # FILE_ATTRIBUTE_SYSTEM = 0x4
            except (OSError, AttributeError):
                return False
        return False
    
    def scan_directory(self, directory: str, exclude_shortcuts: bool = True, 
                      exclude_hidden: bool = True, exclude_system: bool = True,
                      min_size_kb: int = 0, max_size_kb: int = 0) -> Dict[str, List[str]]:
        """Scan directory and identify duplicates with optional filters."""
        if not directory or not os.path.exists(directory):
            return {}
        
        file_dict = {}
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip files based on filters
                if exclude_shortcuts and self.is_file_shortcut(file_path, file):
                    continue
                    
                if exclude_hidden and self.is_file_hidden(file_path, file):
                    continue
                    
                if exclude_system and self.is_file_for_system(file_path, file):
                    continue
                
                # Check file size
                try:
                    file_size = os.path.getsize(file_path) / 1024  # Convert to KB
                    if file_size < min_size_kb:
                        continue
                    if max_size_kb > 0 and file_size > max_size_kb:
                        continue
                except OSError:
                    continue
                
                # Add to duplicates if it passes all filters
                file_hash = self.get_file_hash(file_path)
                if file_hash:
                    if file_hash not in file_dict:
                        file_dict[file_hash] = []
                    file_dict[file_hash].append(file_path)
        
        return {k: v for k, v in file_dict.items() if len(v) > 1}
    
    def delete_files(self, file_paths: List[str]) -> bool:
        """Delete selected files"""
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """Get file information"""
        from app.utils import get_file_info
        return get_file_info(file_path)
    
    def preview_file(self, file_path: str):
        """Preview file content"""
        from app.preview import preview_file_inline
        preview_file_inline(file_path)
