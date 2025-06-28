from abc import ABC, abstractmethod
from typing import Dict, List


class BaseStorageProvider(ABC):
    """Base class for all storage providers"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the storage provider"""
        pass
    
    @abstractmethod
    def get_directory_input_widget(self):
        """Return the appropriate Streamlit widget for directory input"""
        pass
    
    @abstractmethod
    def scan_directory(self, directory: str, exclude_shortcuts: bool = True, 
                      exclude_hidden: bool = True, exclude_system: bool = True,
                      min_size_kb: int = 0, max_size_kb: int = 0) -> Dict[str, List[str]]:
        """Scan directory and return duplicate file groups"""
        pass
    
    @abstractmethod
    def delete_files(self, file_paths: List[str]) -> bool:
        """Delete specified files"""
        pass
    
    @abstractmethod
    def get_file_info(self, file_path: str) -> dict:
        """Get file information"""
        pass
    
    @abstractmethod
    def preview_file(self, file_path: str):
        """Preview file content"""
        pass
