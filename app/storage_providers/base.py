"""Base class for storage providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ScanFilterOptions:
    """Options for filtering files during a scan."""
    exclude_shortcuts: bool = True
    exclude_hidden: bool = True
    exclude_system: bool = True
    min_size_kb: int = 0
    max_size_kb: int = 0
    include_subfolders: bool = True


class BaseStorageProvider(ABC):
    """Base class for all storage providers"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the storage provider"""

    @abstractmethod
    def get_directory_input_widget(self):
        """Return the appropriate Streamlit widget for directory input"""

    @abstractmethod
    def scan_directory(self, directory: dict, filters: ScanFilterOptions) -> Dict[str, List[dict]]:
        """Scan directory and return duplicate file groups

        Args:
            directory: Directory to scan
            filters: ScanFilterOptions object containing filter settings

        Returns:
            Dictionary mapping hash to list of duplicate file paths
        """

    @abstractmethod
    def delete_files(self, files: List[dict]) -> bool:
        """Delete specified files"""

    @abstractmethod
    def get_file_info(self, file: dict) -> dict:
        """Get file information"""

    @abstractmethod
    def get_file_path(self, file: dict) -> str:
        """Get the formatted file path for display"""

    @abstractmethod
    def preview_file(self, file: dict):
        """Preview file content"""

    def get_scan_success_msg(self, duplicate_groups: int, duplicate_files: int) -> str:  # pylint: disable=unused-argument
        """Returns custom success message after scan completion

        Args:
            duplicate_groups: Number of duplicate groups found
            duplicate_files: Total number of duplicate files found

        Returns:
            A formatted success message string
        """
        return f"Found {duplicate_groups} groups of duplicates."
