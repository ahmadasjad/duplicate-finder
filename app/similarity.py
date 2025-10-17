"""Module for similarity-based duplicate detection."""

import os
import hashlib
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import difflib
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class SimilarityMethod(Enum):
    """Available similarity detection methods."""
    HASH_EXACT = "hash_exact"
    HASH_PERCEPTUAL = "hash_perceptual"
    CONTENT_TEXT = "content_text"
    CONTENT_BINARY = "content_binary"
    IMAGE_STRUCTURAL = "image_structural"
    FILENAME_FUZZY = "filename_fuzzy"


@dataclass
class SimilarityConfig:
    """Configuration for similarity detection."""
    threshold: float = 1.0  # 1.0 = 100% (exact), 0.95 = 95%, etc.
    methods: List[SimilarityMethod] = None
    enable_perceptual_hash: bool = True
    enable_content_similarity: bool = True
    enable_image_similarity: bool = True
    enable_filename_similarity: bool = False

    def __post_init__(self):
        if self.methods is None:
            self.methods = [
                SimilarityMethod.HASH_EXACT,
                SimilarityMethod.HASH_PERCEPTUAL,
                SimilarityMethod.CONTENT_TEXT,
                SimilarityMethod.IMAGE_STRUCTURAL
            ]


class SimilarityDetector:
    """Detects similar files using various algorithms."""

    def __init__(self, config: SimilarityConfig):
        self.config = config
        self._image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        self._text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}

        from app.storage_providers.google_drive.cache_manager import DriveCache
        self.cache_manager = DriveCache()

    def find_similar_files(self, files: List[dict]) -> Dict[str, List[dict]]:
        """
        Find similar files using configured similarity methods.

        Args:
            files: List of file dictionaries with 'path' key

        Returns:
            Dictionary mapping similarity group ID to list of similar files
        """
        logger.info("Starting similarity detection with %d files", len(files))
        logger.debug("Similarity configuration: %s", self.config)
        if self.config.threshold >= 1.0:
            # Use exact hash for 100% similarity
            return self._find_exact_duplicates(files)

        similar_groups = {}
        processed_files = set()

        for i, file1 in enumerate(files):
            if file1.get_id() in processed_files:
                continue

            # Start a new similarity group
            group_id = f"group_{i}"
            similar_files = [file1]
            processed_files.add(file1.get_id())

            # Compare with remaining files
            for file2 in files[i+1:]:
                if file2.get_id() in processed_files:
                    continue

                similarity_score = self.get_similarity_score(file1, file2)
                if similarity_score >= self.config.threshold:
                    similar_files.append(file2)
                    processed_files.add(file2.get_id())

            # Only keep groups with more than one file
            if len(similar_files) > 1:
                similar_groups[group_id] = similar_files

        return similar_groups

    def get_similarity_score(self, file1: dict, file2: dict) -> float:
        """
        Get the cached similarity score between two files, if available.

        Returns:
            Float similarity score or 0.0 if not found
        """

        existing_score = self.cache_manager.get_similarity_score(file1.get_id(), file2.get_id())
        if existing_score is not None:
            return float(existing_score)

        similarity_score = self._calculate_similarity(file1, file2)
        self.cache_manager.cache_similarity_score(file1.get_id(), file2.get_id(), similarity_score)

        return similarity_score

    def _find_exact_duplicates(self, files: List[dict]) -> Dict[str, List[dict]]:
        """Find exact duplicates using MD5 hash."""
        file_dict = {}

        for file in files:
            file_hash = file.get_file_hash()
            if file_hash:
                if file_hash not in file_dict:
                    file_dict[file_hash] = []
                file_dict[file_hash].append(file)

        return {k: v for k, v in file_dict.items() if len(v) > 1}

    def _calculate_similarity(self, file1: dict, file2: dict) -> float:
        """
        Calculate similarity score between two files.

        Returns:
            Float between 0.0 and 1.0 representing similarity
        """

        # Quick check: if files have same hash, they're identical
        if self._files_have_same_hash(file1, file2):
            return 1.0

        max_similarity = 0.0

        # Try different similarity methods
        for method in self.config.methods:
            try:
                if method == SimilarityMethod.HASH_PERCEPTUAL and self.config.enable_perceptual_hash:
                    similarity = self._perceptual_hash_similarity(file1, file2)
                elif method == SimilarityMethod.CONTENT_TEXT and self.config.enable_content_similarity:
                    similarity = self._text_content_similarity(file1, file2)
                elif method == SimilarityMethod.CONTENT_BINARY and self.config.enable_content_similarity:
                    similarity = self._binary_content_similarity(file1, file2)
                elif method == SimilarityMethod.IMAGE_STRUCTURAL and self.config.enable_image_similarity:
                    similarity = self._image_structural_similarity(file1, file2)
                elif method == SimilarityMethod.FILENAME_FUZZY and self.config.enable_filename_similarity:
                    similarity = self._filename_similarity(file1, file2)
                else:
                    continue

                max_similarity = max(max_similarity, similarity)

                # Early exit if we found high similarity
                if max_similarity >= self.config.threshold:
                    break

            except Exception as e:
                logger.debug(f"Error calculating {method.value} similarity: {e}")
                continue

        return max_similarity

    def _files_have_same_hash(self, file1: dict, file2: dict) -> bool:
        """Check if two files have the same MD5 hash."""
        hash1 = file1.get_file_hash()
        hash2 = file2.get_file_hash()
        return hash1 and hash2 and hash1 == hash2

    def _perceptual_hash_similarity(self, file1: dict, file2: dict) -> float:
        """Calculate similarity using perceptual hashing for images."""

        if not file1.is_image_file() or not file2.is_image_file():
            return 0.0

        try:
            hash1 = self._calculate_perceptual_hash(file1)
            hash2 = self._calculate_perceptual_hash(file2)

            if hash1 is None or hash2 is None:
                return 0.0

            # Calculate Hamming distance
            hamming_distance = bin(hash1 ^ hash2).count('1')
            # Convert to similarity (0-1 scale)
            similarity = 1.0 - (hamming_distance / 64.0)  # 64 bits in hash
            return max(0.0, similarity)

        except Exception as e:
            logger.debug(f"Error calculating perceptual hash similarity: {e}")
            return 0.0

    def _calculate_perceptual_hash(self, image_file: dict) -> Optional[int]:
        """Calculate perceptual hash of an image."""
        image_path = image_file.get_path()
        try:
            img = image_file.get_image()

            # Resize to 8x8
            img = cv2.resize(img, (8, 8))

            # Calculate average
            avg = img.mean()

            # Create hash
            hash_value = 0
            for i in range(8):
                for j in range(8):
                    if img[i, j] > avg:
                        hash_value |= (1 << (i * 8 + j))

            return hash_value

        except Exception as e:
            logger.debug(f"Error calculating perceptual hash for {image_path}: {e}")
            return None

    def _text_content_similarity(self, file1: dict, file2: dict) -> float:
        """Calculate similarity for text files using difflib."""
        if not file1.is_text_file() or not file2.is_text_file():
            return 0.0

        try:
            content1_bytes = file1.get_content() or b""
            content2_bytes = file2.get_content() or b""
            content1 = content1_bytes.decode('utf-8', errors='ignore')
            content2 = content2_bytes.decode('utf-8', errors='ignore')

            # Use difflib to calculate similarity
            similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
            return similarity

        except Exception as e:
            logger.debug(f"Error calculating text similarity: {e}")
            return 0.0

    def _binary_content_similarity(self, file1: dict, file2: dict) -> float:
        """Calculate similarity for binary files using byte comparison."""
        try:
            content1 = file1.get_content() or b""
            content2 = file2.get_content() or b""

            # Simple byte-by-byte comparison
            if len(content1) != len(content2):
                # For different sizes, calculate overlap
                min_len = min(len(content1), len(content2))
                max_len = max(len(content1), len(content2))

                if max_len == 0:
                    return 1.0

                # Compare only the overlapping part
                matches = sum(1 for i in range(min_len) if content1[i] == content2[i])
                similarity = matches / max_len
            else:
                # Same size - direct comparison
                matches = sum(1 for a, b in zip(content1, content2) if a == b)
                similarity = matches / len(content1) if content1 else 1.0

            return similarity

        except Exception as e:
            logger.debug(f"Error calculating binary similarity: {e}")
            return 0.0

    def _image_structural_similarity(self, file1: dict, file2: dict) -> float:
        """Calculate structural similarity for images using SSIM."""

        if not file1.is_image_file() or not file2.is_image_file():
            return 0.0

        try:
            # Load images
            img1 = file1.get_image()
            img2 = file2.get_image()

            if img1 is None or img2 is None:
                return 0.0

            # Resize to same dimensions for comparison
            height = min(img1.shape[0], img2.shape[0])
            width = min(img1.shape[1], img2.shape[1])

            img1 = cv2.resize(img1, (width, height))
            img2 = cv2.resize(img2, (width, height))

            # Calculate SSIM
            # Simple SSIM implementation (for full SSIM, we'd need scikit-image)
            # For now, use normalized cross-correlation as approximation
            img1_norm = img1.astype(np.float64) / 255.0
            img2_norm = img2.astype(np.float64) / 255.0

            # Calculate normalized cross-correlation
            correlation = np.corrcoef(img1_norm.flatten(), img2_norm.flatten())[0, 1]

            # Handle NaN values
            if np.isnan(correlation):
                correlation = 0.0

            # Convert to 0-1 range (correlation can be negative)
            similarity = (correlation + 1.0) / 2.0
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.debug(f"Error calculating image structural similarity: {e}")
            return 0.0

    def _filename_similarity(self, file1: dict, file2: dict) -> float:
        """Calculate similarity based on filename."""
        name1 = file1.get_name(with_extension=False).lower()
        name2 = file2.get_name(with_extension=False).lower()

        similarity = difflib.SequenceMatcher(None, name1, name2).ratio()
        return similarity

    def get_similarity_explanation(self, file1: dict, file2: dict) -> str:
        """Get explanation of why two files are considered similar."""
        explanations = []

        if self._files_have_same_hash(file1, file2):
            explanations.append("Identical content (same hash)")
            return "; ".join(explanations)

        for method in self.config.methods:
            try:
                if method == SimilarityMethod.HASH_PERCEPTUAL and self.config.enable_perceptual_hash:
                    similarity = self._perceptual_hash_similarity(file1, file2)
                    if similarity >= self.config.threshold:
                        explanations.append(f"Visual similarity: {similarity:.1%}")

                elif method == SimilarityMethod.CONTENT_TEXT and self.config.enable_content_similarity:
                    similarity = self._text_content_similarity(file1, file2)
                    if similarity >= self.config.threshold:
                        explanations.append(f"Text content similarity: {similarity:.1%}")

                elif method == SimilarityMethod.IMAGE_STRUCTURAL and self.config.enable_image_similarity:
                    similarity = self._image_structural_similarity(file1, file2)
                    if similarity >= self.config.threshold:
                        explanations.append(f"Image structure similarity: {similarity:.1%}")

                elif method == SimilarityMethod.FILENAME_FUZZY and self.config.enable_filename_similarity:
                    similarity = self._filename_similarity(file1, file2)
                    if similarity >= self.config.threshold:
                        explanations.append(f"Filename similarity: {similarity:.1%}")

            except Exception:
                continue

        return "; ".join(explanations) if explanations else "Unknown similarity"
