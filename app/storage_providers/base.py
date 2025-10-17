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
    # Similarity detection options
    similarity_threshold: float = 1.0  # 1.0 = exact match, 0.95 = 95% similar, etc.
    enable_similarity_detection: bool = False
    enable_perceptual_hash: bool = True
    enable_content_similarity: bool = True
    enable_image_similarity: bool = True
    enable_filename_similarity: bool = False


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
    def make_shortcut(self, source_file: dict, target_file: dict) -> bool:
        """
        Deletes the target file if it exists and creates a shortcut to the source file.

        Args:
            source_file: The file to create a shortcut for
            target_file: The location where the shortcut should be created

        Returns:
            True if successful, False otherwise
        """

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

    def _find_duplicates_similar(self, all_files: List[dict], filters: ScanFilterOptions, exact_groups) -> dict:
        """Run SimilarityDetector on provided file entries and return similar groups."""
        logger.info("Using similarity detection with threshold: %s", filters.similarity_threshold)

        # Remove all but one file from each exact group from all_files
        exact_file_paths = set()
        for group in exact_groups.values():
            # Keep the first file, remove the rest
            for file_info in group[1:]:
                exact_file_paths.add(file_info['path'])
        filtered_files = [f for f in all_files if f['path'] not in exact_file_paths]

        similarity_config = SimilarityConfig(
            threshold=filters.similarity_threshold,
            enable_perceptual_hash=filters.enable_perceptual_hash,
            enable_content_similarity=filters.enable_content_similarity,
            enable_image_similarity=filters.enable_image_similarity,
            enable_filename_similarity=filters.enable_filename_similarity
        )
        detector = SimilarityDetector(similarity_config)
        # SimilarityDetector expects entries with 'path' key
        return detector.find_similar_files(filtered_files)

    def _merge_exact_and_similar(self, exact_groups: dict, similar_groups: dict) -> dict:
        """Merge exact and similar duplicate groups into a single dictionary."""
        merged = {}
        idx = 1

        # Add exact groups first
        for group in exact_groups.values():
            merged[f"group_{idx}"] = group
            idx += 1

        # Add similar groups next
        for group in similar_groups.values():
            merged[f"group_{idx}"] = group
            idx += 1

        if not merged:
            raise NoDuplicateException("No duplicate files found in the selected folder.")

        return merged
