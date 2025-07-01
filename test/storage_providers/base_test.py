"""Tests for the base storage provider class."""

import pytest
from app.storage_providers.base import BaseStorageProvider, ScanFilterOptions


def test_scan_filter_options_defaults():
    """Test ScanFilterOptions default values"""
    options = ScanFilterOptions()
    assert options.exclude_shortcuts is True
    assert options.exclude_hidden is True
    assert options.exclude_system is True
    assert options.min_size_kb == 0
    assert options.max_size_kb == 0


def test_scan_filter_options_custom_values():
    """Test ScanFilterOptions with custom values"""
    options = ScanFilterOptions(
        exclude_shortcuts=False,
        exclude_hidden=False,
        exclude_system=False,
        min_size_kb=100,
        max_size_kb=1000
    )
    assert options.exclude_shortcuts is False
    assert options.exclude_hidden is False
    assert options.exclude_system is False
    assert options.min_size_kb == 100
    assert options.max_size_kb == 1000


class MockStorageProvider(BaseStorageProvider):
    """Mock storage provider for testing abstract base class"""
    def authenticate(self):
        return True

    def get_directory_input_widget(self):
        return "mock_widget"

    def scan_directory(self, directory, filters):
        return {"hash1": ["file1", "file2"]}

    def delete_files(self, files):
        return True

    def get_file_info(self, file):
        return {"size": 100, "modified": "2023-01-01"}

    def get_file_path(self, file):
        return f"/mock/path/{file}"

    def preview_file(self, file):
        return "mock_preview"


def test_base_storage_provider_abstract():
    """Test that BaseStorageProvider cannot be instantiated directly"""
    with pytest.raises(TypeError):
        BaseStorageProvider("test")


def test_mock_storage_provider_instantiation():
    """Test that a concrete implementation can be instantiated"""
    provider = MockStorageProvider("test")
    assert provider.name == "test"


def test_get_scan_success_msg():
    """Test the get_scan_success_msg method"""
    provider = MockStorageProvider("test")
    msg = provider.get_scan_success_msg(3, 7)
    assert msg == "Found 3 groups of duplicates."


def test_mock_provider_methods():
    """Test all abstract methods are implemented and return expected values"""
    provider = MockStorageProvider("test")

    assert provider.authenticate() is True
    assert provider.get_directory_input_widget() == "mock_widget"

    scan_result = provider.scan_directory("test_dir", ScanFilterOptions())
    assert isinstance(scan_result, dict)
    assert "hash1" in scan_result
    assert scan_result["hash1"] == ["file1", "file2"]

    assert provider.delete_files(["file1"]) is True

    file_info = provider.get_file_info("test.txt")
    assert isinstance(file_info, dict)
    assert "size" in file_info
    assert "modified" in file_info

    file_path = provider.get_file_path("test.txt")
    assert file_path == "/mock/path/test.txt"

    preview = provider.preview_file("test.txt")
    assert preview == "mock_preview"
