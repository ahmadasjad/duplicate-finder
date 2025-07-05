"""Custom exceptions for storage provider operations.

This module contains exceptions for all storage providers, including:
- NoFileFoundException: When a requested file cannot be found
- NoDuplicateException: When no duplicates are found during scanning
"""

class NoFileFoundException(Exception):
    """Raised when a requested file cannot be found."""

class NoDuplicateException(Exception):
    """Raised when no duplicates are found during scanning."""
