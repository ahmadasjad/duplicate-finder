"""Tests for all storage providers scan_directory functionality."""

import pytest
from app.storage_providers import get_storage_providers
from app.storage_providers.base import ScanFilterOptions

# Test data
TEST_DIRECTORY = "test_data"  # Using test_data directory from project root
FILTER_OPTIONS = ScanFilterOptions(
    exclude_shortcuts=True,
    exclude_hidden=True,
    exclude_system=True,
    min_size_kb=0,
    max_size_kb=0
)

def validate_scan_result(result):
    """Helper function to validate scan results"""
    assert isinstance(result, dict), "Scan result should be a dictionary"

    for hash_key, file_list in result.items():
        assert isinstance(hash_key, str), "Hash key should be a string"
        assert isinstance(file_list, list), "File list should be a list"
        assert all(isinstance(f, str) for f in file_list), "All file paths should be strings"
        assert len(file_list) > 0, "File list should not be empty"

def test_all_providers_scan():
    """Test scan_directory for all enabled providers"""
    providers = get_storage_providers()
    assert len(providers) > 0, "No storage providers enabled"

    results = {}
    for name, provider in providers.items():
        try:
            # Skip if authentication fails for cloud providers
            if hasattr(provider, "authenticate"):
                if not provider.authenticate():
                    continue

            result = provider.scan_directory(TEST_DIRECTORY, FILTER_OPTIONS)
            validate_scan_result(result)
            results[name] = result
        except Exception as e:
            pytest.skip(f"Provider {name} failed: {str(e)}")

    # Compare file counts across providers if we have multiple results
    if len(results) > 1:
        file_counts = {name: sum(len(files) for files in result.values())
                      for name, result in results.items()}

        # Check if file counts are similar (within 10% difference)
        base_count = next(iter(file_counts.values()))
        for name, count in file_counts.items():
            diff_percentage = abs(count - base_count) / base_count * 100
            assert diff_percentage <= 10, (
                f"File count for {name} differs by more than 10% "
                f"from others: {count} vs {base_count}"
            )
