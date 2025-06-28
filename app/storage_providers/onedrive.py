from typing import Dict, List
from .base import BaseStorageProvider


class OneDriveProvider(BaseStorageProvider):
    """OneDrive storage provider (placeholder implementation)"""
    
    def __init__(self):
        super().__init__("OneDrive")
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with OneDrive API"""
        import streamlit as st
        st.info("OneDrive integration coming soon!")
        # TODO: Implement OneDrive API authentication
        return False
    
    def get_directory_input_widget(self):
        """Return widget for OneDrive folder selection"""
        import streamlit as st
        if not self.authenticated:
            if st.button("Authenticate with OneDrive"):
                self.authenticate()
            return None
        else:
            return st.selectbox("Select OneDrive folder:", ["Root", "Documents", "Pictures"])
    
    def scan_directory(self, directory: str, exclude_shortcuts: bool = True, 
                      exclude_hidden: bool = True, exclude_system: bool = True,
                      min_size_kb: int = 0, max_size_kb: int = 0) -> Dict[str, List[str]]:
        """Scan OneDrive directory (placeholder)"""
        import streamlit as st
        st.warning("OneDrive scanning not yet implemented")
        return {}
    
    def delete_files(self, file_paths: List[str]) -> bool:
        """Delete files from OneDrive (placeholder)"""
        return False
    
    def get_file_info(self, file_path: str) -> dict:
        """Get OneDrive file info (placeholder)"""
        return {}
    
    def preview_file(self, file_path: str):
        """Preview OneDrive file (placeholder)"""
        import streamlit as st
        st.info("OneDrive file preview coming soon!")
