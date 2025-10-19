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

        # Performance optimization: Cache feature vectors to avoid recomputation
        self._feature_cache = {}
        self._optimization_threshold = 100  # Use optimized algorithm for large file sets

    def find_similar_files(self, files: List[dict]) -> Dict[str, List[dict]]:
        """
        Find similar files using configured similarity methods.

        Args:
            files: List of file dictionaries with 'path' key

        Returns:
            Dictionary mapping similarity group ID to list of similar files
        """
        import time
        start_time = time.time()

        logger.info("Starting similarity detection with %d files", len(files))
        logger.debug("Similarity configuration: %s", self.config)

        if self.config.threshold >= 1.0:
            # Use exact hash for 100% similarity
            result = self._find_exact_duplicates(files)
            elapsed = time.time() - start_time
            logger.info("Exact duplicate detection completed in %.2f seconds", elapsed)
            return result

        # Clear feature cache for new detection run
        self._feature_cache.clear()

        # Use optimized algorithm for large file sets
        if len(files) > self._optimization_threshold:
            logger.info("Using optimized similarity detection for %d files", len(files))
            result = self._find_similar_files_optimized(files)
        else:
            logger.info("Using standard similarity detection for %d files", len(files))
            result = self._find_similar_files_standard(files)

        elapsed = time.time() - start_time
        total_groups = len(result)
        total_files = sum(len(group) for group in result.values())
        logger.info("Similarity detection completed in %.2f seconds: %d groups, %d files",
                   elapsed, total_groups, total_files)

        return result

    def _find_similar_files_standard(self, files: List[dict]) -> Dict[str, List[dict]]:
        """Standard O(n²) similarity detection for small file sets."""
        import time
        start_time = time.time()

        similar_groups = {}
        processed_files = set()
        group_index = 1
        comparisons_made = 0

        for i, file1 in enumerate(files):
            if file1.get_id() in processed_files:
                continue

            # Start a new similarity group
            similar_files = [file1]
            processed_files.add(file1.get_id())

            # Compare with remaining files
            for file2 in files[i+1:]:
                if file2.get_id() in processed_files:
                    continue

                similarity_score = self.get_similarity_score(file1, file2)
                comparisons_made += 1
                if similarity_score >= self.config.threshold:
                    similar_files.append(file2)
                    processed_files.add(file2.get_id())

            # Only keep groups with more than one file
            if len(similar_files) > 1:
                similar_groups[f"group_{group_index}"] = similar_files
                group_index += 1

        elapsed = time.time() - start_time
        logger.debug("Standard detection: %d comparisons in %.3f seconds", comparisons_made, elapsed)

        return similar_groups

    def _find_similar_files_optimized(self, files: List[dict]) -> Dict[str, List[dict]]:
        """
        Optimized similarity detection using clustering and feature vector caching.
        Reduces O(n²) complexity by grouping files by type and using efficient comparisons.
        """
        logger.info("Starting optimized similarity detection")

        # Group files by type for more efficient comparison
        image_files = [f for f in files if f.is_image_file()]
        text_files = [f for f in files if f.is_text_file()]
        other_files = [f for f in files if not f.is_image_file() and not f.is_text_file()]

        logger.debug("File distribution - Images: %d, Text: %d, Other: %d",
                    len(image_files), len(text_files), len(other_files))

        similar_groups = {}
        group_index = 1

        # Process each file type group separately
        for file_group, group_name in [(image_files, "images"), (text_files, "text"), (other_files, "other")]:
            if len(file_group) < 2:
                continue

            logger.debug("Processing %s files: %d", group_name, len(file_group))

            # Use clustering for large groups
            if len(file_group) > self._optimization_threshold // 3:
                group_results = self._find_similar_clustered(file_group, group_name)
            else:
                group_results = self._find_similar_files_standard(file_group)

            # Merge results
            for group in group_results.values():
                if len(group) > 1:
                    similar_groups[f"group_{group_index}"] = group
                    group_index += 1

        return similar_groups

    def _find_similar_clustered(self, files: List[dict], file_type: str) -> Dict[str, List[dict]]:
        """
        Use clustering-based approach for large file sets.
        Groups files by features first, then compares within clusters.
        """
        logger.info("Using clustering for %d %s files", len(files), file_type)

        # Extract feature vectors for all files
        feature_vectors = []
        file_to_vector = {}

        for file in files:
            vector = self._get_feature_vector(file, file_type)
            if vector is not None:
                feature_vectors.append(vector)
                file_to_vector[file.get_id()] = vector

        if len(feature_vectors) < 2:
            return {}

        # Use simple clustering based on feature similarity
        clusters = self._cluster_by_features(files, file_to_vector, file_type)

        # Find similar files within each cluster
        similar_groups = {}
        cluster_index = 1

        for cluster_files in clusters:
            if len(cluster_files) < 2:
                continue

            # Use standard comparison within cluster (smaller n)
            cluster_results = self._find_similar_files_standard(cluster_files)

            for group in cluster_results.values():
                if len(group) > 1:
                    similar_groups[f"cluster_{cluster_index}"] = group
                    cluster_index += 1

        return similar_groups

    def _get_feature_vector(self, file: dict, file_type: str) -> Optional[List[float]]:
        """Extract feature vector for clustering based on file type."""
        cache_key = f"{file.get_id()}_{file_type}"

        if cache_key in self._feature_cache:
            return self._feature_cache[cache_key]

        try:
            if file_type == "images" and file.is_image_file():
                # Use perceptual hash as feature vector
                phash = self._calculate_perceptual_hash(file)
                if phash is not None:
                    # Convert hash to binary feature vector
                    vector = [(phash >> i) & 1 for i in range(64)]
                    self._feature_cache[cache_key] = vector
                    return vector

            elif file_type == "text" and file.is_text_file():
                # Use text content features
                content = file.get_content()
                if content:
                    text = content.decode('utf-8', errors='ignore')
                    # Simple features: length, line count, avg line length
                    lines = text.split('\n')
                    vector = [
                        len(text) / 10000.0,  # Normalized length
                        len(lines) / 100.0,   # Normalized line count
                        sum(len(line) for line in lines) / max(len(lines), 1) / 100.0  # Avg line length
                    ]
                    self._feature_cache[cache_key] = vector
                    return vector

            else:
                # For other files, use file size and name similarity as features
                content = file.get_content()
                size = len(content) if content else 0
                name = file.get_name(with_extension=False).lower()

                # Simple features based on size and name length
                vector = [
                    size / (1024 * 1024.0),  # Size in MB
                    len(name) / 50.0,        # Normalized name length
                    hash(name) % 100 / 100.0  # Simple hash-based feature
                ]
                self._feature_cache[cache_key] = vector
                return vector

        except Exception as e:
            logger.debug(f"Error extracting features for {file.get_id()}: {e}")

        return None

    def _cluster_by_features(self, files: List[dict], file_to_vector: Dict[str, List[float]], file_type: str) -> List[List[dict]]:
        """
        Simple clustering algorithm based on feature vector similarity.
        Uses hierarchical clustering for small sets, binning for large sets.
        """
        if len(files) <= 10:
            # For small sets, put all files in one cluster
            return [files]

        # For larger sets, use binning based on primary features
        clusters = {}

        for file in files:
            vector = file_to_vector.get(file.get_id())
            if vector is None:
                continue

            if file_type == "images":
                # Cluster images by perceptual hash similarity
                cluster_key = tuple(vector[:8])  # Use first 8 bits as cluster key
            elif file_type == "text":
                # Cluster text by size and line count
                size_bin = int(vector[0] * 10)  # Bin by size
                cluster_key = f"text_{size_bin}"
            else:
                # Cluster other files by size
                size_bin = int(vector[0] * 10)  # Bin by size in MB
                cluster_key = f"other_{size_bin}"

            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(file)

        # Return clusters with at least 2 files
        return [cluster for cluster in clusters.values() if len(cluster) >= 2]

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
        import time
        start_time = time.time()

        # Quick check: if files have same hash, they're identical
        if self._files_have_same_hash(file1, file2):
            logger.debug(f"Files identical by hash: {file1.get_id()} == {file2.get_id()}")
            return 1.0

        max_similarity = 0.0
        remaining_methods = self.config.methods.copy()

        # Try methods in order of computational efficiency
        for method in self._get_ordered_methods():
            if method not in remaining_methods:
                continue

            try:
                similarity = self._calculate_method_similarity(method, file1, file2)
                max_similarity = max(max_similarity, similarity)

                # Early exit if we found high similarity
                if max_similarity >= self.config.threshold:
                    logger.debug(f"Early exit at {method.value}: {max_similarity:.3f}")
                    break

                # Remove method from remaining list
                remaining_methods.remove(method)

            except Exception as e:
                logger.debug(f"Error calculating {method.value} similarity: {e}")
                remaining_methods.remove(method)
                continue

        elapsed = time.time() - start_time
        if elapsed > 0.1:  # Log slow comparisons
            logger.debug(f"Similarity calculation took {elapsed:.3f}s for {file1.get_id()} vs {file2.get_id()}")

        return max_similarity

    def _get_ordered_methods(self) -> List[SimilarityMethod]:
        """Return methods ordered by computational efficiency (fastest first)."""
        ordered_methods = [
            SimilarityMethod.FILENAME_FUZZY,      # Fast: string comparison
            SimilarityMethod.HASH_EXACT,          # Fast: hash comparison
            SimilarityMethod.HASH_PERCEPTUAL,     # Medium: image processing
            SimilarityMethod.CONTENT_TEXT,        # Medium: text processing
            SimilarityMethod.CONTENT_BINARY,      # Slow: binary comparison
            SimilarityMethod.IMAGE_STRUCTURAL,    # Slow: image processing
        ]

        # Filter to only include enabled methods
        return [m for m in ordered_methods if self._is_method_enabled(m)]

    def _is_method_enabled(self, method: SimilarityMethod) -> bool:
        """Check if a similarity method is enabled in the configuration."""
        if method not in self.config.methods:
            return False

        if method == SimilarityMethod.HASH_PERCEPTUAL:
            return self.config.enable_perceptual_hash
        elif method == SimilarityMethod.CONTENT_TEXT or method == SimilarityMethod.CONTENT_BINARY:
            return self.config.enable_content_similarity
        elif method == SimilarityMethod.IMAGE_STRUCTURAL:
            return self.config.enable_image_similarity
        elif method == SimilarityMethod.FILENAME_FUZZY:
            return self.config.enable_filename_similarity
        else:
            return True

    def _calculate_method_similarity(self, method: SimilarityMethod, file1: dict, file2: dict) -> float:
        """Calculate similarity using a specific method with caching."""
        cache_key = f"{method.value}_{file1.get_id()}_{file2.get_id()}"

        if cache_key in self._feature_cache:
            return self._feature_cache[cache_key]

        similarity = 0.0
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
        elif method == SimilarityMethod.HASH_EXACT:
            similarity = 1.0 if self._files_have_same_hash(file1, file2) else 0.0

        self._feature_cache[cache_key] = similarity
        return similarity

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
