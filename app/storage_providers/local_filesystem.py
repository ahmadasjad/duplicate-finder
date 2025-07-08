"""Local filesystem storage provider implementation."""

import os
import hashlib
import logging
from typing import Dict, List, Union
import streamlit as st

from app.file_operations import is_file_shortcut, is_file_hidden, is_file_for_system
from app.utils import get_file_info
from app.preview import preview_file_inline
from .base import BaseStorageProvider, ScanFilterOptions

logger = logging.getLogger(__name__)


class LocalFileSystemProvider(BaseStorageProvider):
    """Local file system storage provider"""

    def __init__(self):
        super().__init__("Local File System")

    def authenticate(self) -> bool:
        """No authentication needed for local file system"""
        return True

    def get_directory_input_widget(self) -> Dict:
        """Return text input for local directory path"""

        # Detect if running in Docker container
        is_docker = self._is_running_in_docker()

        if is_docker:
            # Show available mount points for Docker users
            st.info("🐳 **Docker Mode Detected**")
            st.markdown("**Available directories to scan:**")
            st.markdown("- `/app/app/debug/` - Sample debug files")
            st.markdown("- `/app/app/test_data/` - Test data directory")
            st.markdown("- `/host_home/` - Host home directory (read-only)")
            st.markdown("- `/host_test_data/` - Host test data directory (read-only)")
            st.markdown("- Or enter any other mounted path")

            # Provide default directory suggestions for Docker
            default_dirs = [
                "/app/app/debug",
                "/app/app/test_data",
                # "/host_home",
                "/host_test_data"
            ]
            default_index = 3
        else:
            # Show local system directory suggestions
            st.info("💻 **Local Mode**")
            st.markdown("**Common directories to scan:**")
            home_dir = os.path.expanduser("~")
            st.markdown(f"- `{home_dir}` - Home directory")
            st.markdown(f"- `{home_dir}/Documents` - Documents folder")
            st.markdown(f"- `{home_dir}/Downloads` - Downloads folder")
            st.markdown(f"- `{home_dir}/Pictures` - Pictures folder")
            st.markdown("- Or enter any other directory path")

            # Provide default directory suggestions for local
            default_dirs = [
                home_dir,
                os.path.join(home_dir, "Documents"),
                os.path.join(home_dir, "Downloads"),
                os.path.join(home_dir, "Pictures"),
                os.path.join(home_dir, "Desktop")
            ]
            # Filter out directories that don't exist
            default_dirs = [d for d in default_dirs if os.path.exists(d)]
            default_index = 0

        if default_index >= len(default_dirs):
            default_index = 0
        directory = st.selectbox(
            "Enter directory path:", options=default_dirs,
            accept_new_options=True, index=default_index
            )
        return {'path': directory, }
        # return directory

    def _is_running_in_docker(self) -> bool:
        """Detect if the application is running inside a Docker container"""
        try:
            # Method 1: Check for .dockerenv file
            if os.path.exists('/.dockerenv'):
                return True

            # Method 2: Check cgroup for docker
            with open('/proc/1/cgroup', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'docker' in content or 'containerd' in content:
                    return True

            # Method 3: Check if running as PID 1 (common in containers)
            # and some Docker-specific environment variables exist
            if os.getpid() == 1 and any(
                env_var in os.environ for env_var in ['HOSTNAME', 'container']
            ):
                return True

        except (FileNotFoundError, OSError, PermissionError):
            # If we can't access these files, fall back to environment check
            pass

        # Method 4: Check for Docker-specific environment variables
        docker_env_vars = ['DOCKER_CONTAINER', 'KUBERNETES_SERVICE_HOST']
        if any(var in os.environ for var in docker_env_vars):
            return True

        # Method 5: Check if we're in the /app directory (common Docker pattern)
        if os.getcwd() == '/app' and os.path.exists('/app/requirements.txt'):
            return True

        return False

    def get_file_hash(self, file_path: str) -> Union[str, None]:
        """Compute the hash of a file."""
        hash_obj = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except (OSError, IOError):
            return None

    def scan_directory(self, directory: dict, filters: ScanFilterOptions) -> Dict[str, List[dict]]:
        """Scans directory and identify duplicates with optional filters."""
        folder_path = directory.get('path', '')
        if not folder_path or not os.path.exists(folder_path):
            return {}

        file_dict: dict[str, list[dict]] = {}
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)

                # Skip files based on filters
                if filters.exclude_shortcuts and is_file_shortcut(file_path, file):
                    continue
                if filters.exclude_hidden and is_file_hidden(file_path, file):
                    continue
                if filters.exclude_system and is_file_for_system(file_path, file):
                    continue

                # Check file size
                try:
                    file_size = os.path.getsize(file_path) / 1024  # Convert to KB
                    if file_size < filters.min_size_kb:
                        continue
                    if filters.max_size_kb > 0 and file_size > filters.max_size_kb:
                        continue
                except OSError:
                    continue

                # Add to duplicates if it passes all filters
                file_hash = self.get_file_hash(file_path)
                if file_hash:
                    if file_hash not in file_dict:
                        file_dict[file_hash] = []
                    file_dict[file_hash].append({'path': file_path, 'id': file_path})

        return {k: v for k, v in file_dict.items() if len(v) > 1}

    def delete_files(self, files: List[dict]) -> bool:
        """Delete selected files"""
        try:
            for file in files:
                file_path = file['path']
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except OSError:
            return False

    def get_file_info(self, file: dict) -> dict:
        """Get file information"""
        file_path = file['path']
        logger.info("Getting file info for: %s", file_path)
        logger.info(file)
        return get_file_info(file_path)

    def preview_file(self, file: dict) -> None:
        """Preview file content"""
        file_path = file['path']
        preview_file_inline(file_path)

    def get_file_path(self, file: dict) -> str:
        """Get the formatted file path for display"""
        file_path = file['path']
        return os.path.abspath(file_path)

    def make_shortcut(self, source_file: dict, target_file: dict) -> bool:
        """Create a shortcut to source file at target location"""
        try:
            source_path = source_file['path']
            target_path = target_file['path']

            # If running in Docker, convert to relative path from target to source
            if self._is_running_in_docker():
                # Calculate the relative path from target's directory to source file
                target_dir = os.path.dirname(target_path)
                source_path = os.path.relpath(source_path, target_dir)
                logger.info("Docker detected - Using relative path from target dir:")
                logger.info("Target directory: %s", target_dir)
                logger.info("Relative source path: %s", source_path)

            # Delete target file first
            if os.path.exists(target_path):
                os.remove(target_path)

            # Create shortcut based on OS
            if os.name == 'nt':  # Windows
                import winshell
                with winshell.shortcut(target_path + '.lnk') as shortcut:
                    shortcut.path = source_path
                    shortcut.working_directory = os.path.dirname(target_path)
            else:  # Unix/Linux
                os.symlink(source_path, target_path)

            return True
        except Exception as e:
            logger.error("Failed to create shortcut: %s", str(e))
            return False
