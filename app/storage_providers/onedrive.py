"""OneDrive storage provider implementation."""

from typing import Dict, List
import streamlit as st

from .base import BaseStorageProvider, ScanFilterOptions


class OneDriveProvider(BaseStorageProvider):
    """OneDrive storage provider (placeholder implementation)"""

    def __init__(self):
        super().__init__("OneDrive")
        self.authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with OneDrive API"""
        st.info("OneDrive integration coming soon!")
        # TODO: Implement OneDrive API authentication
        return False

    def get_directory_input_widget(self):
        """Return widget for OneDrive folder selection"""
        if not self.authenticated:
            if st.button("Authenticate with OneDrive"):
                self.authenticate()
            return None
        return st.selectbox("Select OneDrive folder:", ["Root", "Documents", "Pictures"])

    def scan_directory(self, directory: dict, filters: ScanFilterOptions) -> Dict[str, List[dict]]:
        """Scan OneDrive directory (placeholder)"""
        st.warning("OneDrive scanning not yet implemented")
        return {}

    def delete_files(self, files: List[dict]) -> bool:
        """Delete files from OneDrive (placeholder)"""
        return False

    def get_file_info(self, file: dict) -> dict:
        """Get OneDrive file info (placeholder)"""
        return {}

    def preview_file(self, file: dict):
        """Preview OneDrive file (placeholder)"""
        st.info("OneDrive file preview coming soon!")

    def get_file_path(self, file: dict) -> str:
        """Get formatted file path for display"""
        return f"onedrive://{file}"

    def make_shortcut(self, source_file: dict, target_file: dict) -> bool:
        """Create a shortcut to source file at target location (Not implemented for OneDrive)"""
        st.error("Shortcut creation is not yet implemented for OneDrive")
        return False
