"""Dropbox storage provider implementation."""

from typing import Dict, List
import streamlit as st
from .base import BaseStorageProvider, ScanFilterOptions


class DropboxProvider(BaseStorageProvider):
    """Dropbox storage provider (placeholder implementation)"""

    def __init__(self):
        super().__init__("Dropbox")
        self.authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with Dropbox API"""
        st.info("Dropbox integration coming soon!")
        # TODO: Implement Dropbox API authentication
        return False

    def get_directory_input_widget(self):
        """Return widget for Dropbox folder selection"""
        if not self.authenticated:
            if st.button("Authenticate with Dropbox"):
                self.authenticate()
            return None
        return st.selectbox("Select Dropbox folder:", ["Root", "Apps", "Shared"])

    def scan_directory(self, directory: dict, filters: ScanFilterOptions) -> Dict[str, List[dict]]:
        """Scan Dropbox directory (placeholder)"""
        st.warning("Dropbox scanning not yet implemented")
        return {}

    def delete_files(self, files: List[dict]) -> bool:
        """Delete files from Dropbox (placeholder)"""
        return False

    def get_file_info(self, file: dict) -> dict:
        """Get Dropbox file info (placeholder)"""
        return {}

    def preview_file(self, file: dict):
        """Preview Dropbox file (placeholder)"""
        st.info("Dropbox file preview coming soon!")

    def get_file_path(self, file: dict) -> str:
        """Get formatted file path for display"""
        return f"dropbox://{file}"

    def make_shortcut(self, source_file: dict, target_file: dict) -> bool:
        """Create a shortcut to source file at target location (Not implemented for Dropbox)"""
        st.error("Shortcut creation is not yet implemented for Dropbox")
        return False
