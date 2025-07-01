"""Google Drive storage provider implementation."""

import io
import os
import logging
from typing import Dict, List
import re
import requests
import streamlit as st
from PIL import Image

from .google_utils import extract_file_id_and_name, get_enriched_file_info, CREDENTIALS_FILE
from ..base import BaseStorageProvider, ScanFilterOptions
from ...utils import human_readable_size
from .authenticator import GoogleAuthenticator

logger = logging.getLogger(__name__)


class GoogleDriveProvider(BaseStorageProvider, GoogleAuthenticator):
    """Google Drive storage provider with OAuth2 authentication"""


    def __init__(self):
        BaseStorageProvider.__init__(self, "Google Drive")
        GoogleAuthenticator.__init__(self)
        self.folder_id_to_path = {}  # Cache for folder ID to path mapping
        self.folder_path_to_id = {}  # Cache for folder path to ID mapping

    def authenticate(self) -> bool:
        return self.google_service.authenticate()

    def get_folder_id_from_path(self, folder_path: str):
        folder_path = folder_path.strip().strip('/')

        try:
            return self.folder_path_to_id[folder_path]
        except KeyError:
            pass

        parent_id = 'root'  # Start from "My Drive"
        if folder_path == 'My Drive' or folder_path == 'root':
            self.folder_path_to_id[folder_path] = parent_id
            self.folder_id_to_path[parent_id] = folder_path
            return parent_id

        if folder_path.startswith('My Drive'):
            folder_path = folder_path[9:] # Delete "My Drive/" prefix
        parts = folder_path.split('/')

        current_path = parts[0] if parts else 'My Drive'
        self.folder_path_to_id[current_path] = parent_id
        self.folder_id_to_path[parent_id] = current_path
        for part in parts:
            query = f"'{parent_id}' in parents and name = '{part}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.google_service.get_file_service().list(q=query, spaces='drive', fields="files(id, name)").execute()
            items = results.get('files', [])
            if not items:
                raise FileNotFoundError(f"Folder '{part}' not found in path.")
            parent_id = items[0]['id']  # Go one level deeper
            # Build up the current path as we go
            # if current_path:
            current_path = f"{current_path}/{part}"
            # else:
            #     current_path = part
            self.folder_path_to_id[current_path] = parent_id
            self.folder_id_to_path[parent_id] = current_path

        return parent_id

    def get_folder_path_from_id(self, folder_id):
        """Get folder path from Google Drive folder ID"""
        try:
            return self.folder_id_to_path[folder_id]
        except KeyError:
            pass

        path_parts = []
        ids_to_cache = []
        current_id = folder_id
        hit_cached_path_parts = []

        while True:
            try:
                cached_path = self.folder_id_to_path[current_id]
                hit_cached_path_parts = cached_path.split('/')
                break
            except KeyError:
                pass

            file = self.google_service.get_file_service().get(fileId=current_id, fields='*').execute()
            ids_to_cache.append((current_id, file['name']))
            path_parts.append(file['name'])

            try:
                current_id = file['parents'][0]
            except (KeyError, IndexError):
                break  # Reached root

        path_parts.reverse()

        # Add the cached path if any
        if hit_cached_path_parts:
            path_parts = hit_cached_path_parts + path_parts

        # Add "My Drive" if needed
        if path_parts and path_parts[0] != 'My Drive':
            path_parts.insert(0, 'My Drive')

        full_path = '/'.join(path_parts)

        # Cache all resolved folder IDs
        for i, (fid, _) in enumerate(reversed(ids_to_cache)):
            sub_path = '/'.join(path_parts[:len(path_parts) - i])
            self.folder_id_to_path[fid] = sub_path

        # Also cache the requested folder_id directly (redundant safety)
        self.folder_id_to_path[folder_id] = full_path

        return full_path

    def _check_dependencies(self):
        """Check for required Google Drive dependencies and credentials file."""
        # if not os.path.exists('credentials.json'):
        if not os.path.exists(CREDENTIALS_FILE):
            st.error("📋 **Setup Required**")
            st.markdown("""
            **To enable Google Drive integration:**

            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select existing one
            3. Enable the Google Drive API
            4. Create OAuth 2.0 credentials (Desktop application)
            5. Download the credentials JSON file
            6. Rename it to `credentials.json` and place it in the project root

            **Note:** This is a development setup. Production deployments should use proper credential management.
            """)
            return False
        return True

    def _handle_folder_selection(self, folders):
        """Handle folder selection UI and return folder info or None."""
        folder_options = [("root", "My Drive")]
        for folder in folders:
            display_name = f"{folder['name']}"
            folder_options.append((folder['id'], display_name))
        if folder_options:
            selected_folder = st.selectbox(
                "Select Google Drive folder to scan:",
                folder_options,
                help="Choose a folder to scan for duplicate files",
                accept_new_options=True,
                format_func=lambda x: f"{x[1]}" if isinstance(x, tuple) else x
            )
            logger.debug("Selected folder raw: %s", selected_folder)
            if isinstance(selected_folder, tuple):
                folder_id = selected_folder[0]
            else:
                folder_id = self.get_folder_id_from_path(selected_folder)
            include_subfolders = st.checkbox(
                "🔄 Include subfolders (recursive scan)",
                value=True,
                help="Scan all subfolders within the selected folder"
            )
            logger.debug("Selected folder ID: %s, Include subfolders: %s", folder_id, include_subfolders)
            return {
                'folder_id': folder_id,
                'recursive': include_subfolders
            }
        else:
            st.info("No accessible folders found in Google Drive")
            return {
                'folder_id': "root",
                'recursive': True
            }

    def get_directory_input_widget(self):
        """Return widget for Google Drive folder selection"""
        if not self._check_dependencies():
            return None
        # if not self.authenticated:
        if not self.google_service.is_user_authenticated():
            if self._handle_authentication_flow():
                return None
            return None
        user_info = self._get_user_info()
        if user_info:
            st.success(f"✅ Connected to Google Drive as **{user_info['name']}** ({user_info['email']})")
        else:
            st.success("✅ Connected to Google Drive")
        try:
            # folders = self._get_folders()
            folders, _ = self.google_service.get_folders(parent_folder_id='root', per_page=50)
            folders = [{"name": f"My Drive/{folder['name']}", "id": folder['id']} for folder in folders]
            return self._handle_folder_selection(folders)
        except Exception as e:
            st.error(f"Error accessing Google Drive: {e}")
            return None

    def _collect_files(self, folder_id, recursive, status_el):
        """Collect all files from the specified folder (recursively if needed)"""
        all_files = []
        if recursive:
            status_el.text("Discovering folders and files recursively...")
            all_files = self.google_service.get_files_recursive(
                parent_folder_id=folder_id,
            )
        else:
            status_el.text("Fetching file list from Google Drive...")
            page_token = None
            while True:
                files, page_token = self.google_service.get_files(
                    parent_folder_id=folder_id,
                    page_token=page_token,
                )
                all_files.extend(files)
                if not page_token:
                    break
        return all_files

    def _apply_file_filters(self, file_info, filters: ScanFilterOptions):
        """Apply filters to a file and return skip reason if any, else None"""
        file_name = file_info.get('name', '')
        file_size_bytes = int(file_info.get('size', 0))
        file_size_kb = file_size_bytes / 1024
        if filters.exclude_hidden and file_name.startswith('.'):
            return "hidden file"
        if file_size_kb < filters.min_size_kb:
            return f"too small ({file_size_kb:.1f} KB < {filters.min_size_kb} KB)"
        if filters.max_size_kb > 0 and file_size_kb > filters.max_size_kb:
            return f"too large ({file_size_kb:.1f} KB > {filters.max_size_kb} KB)"
        return None

    def _process_file(self, file_info, file_dict, skipped_no_hash):
        """Process a single file: calculate hash, group, and update counters"""
        file_name = file_info.get('name', '')
        file_size_bytes = int(file_info.get('size', 0))
        file_hash = file_info.get('md5Checksum')
        if not file_hash:
            file_hash = f"fallback_{file_name}_{file_size_bytes}"
            skipped_no_hash += 1
        file_id = file_info.get('webViewLink', file_info.get('id', ''))
        if file_hash not in file_dict:
            file_dict[file_hash] = []
        file_data ={
            'path': file_id,
            'name': file_name,
            'size': file_size_bytes,
            'id': file_info.get('id', ''),
            'mimeType': file_info.get('mimeType', ''),
            'webViewLink': file_info.get('webViewLink', ''),
            'has_md5': bool(file_info.get('md5Checksum')),
            'md5_hash': file_info.get('md5Checksum', 'fallback')
        }
        file_data.update(file_info)
        file_dict[file_hash].append(file_data)
        return skipped_no_hash

    def _show_scan_summary(self, total_files, processed_files, skipped_no_hash, skipped_filters, duplicates, file_dict):
        """Log and display scan summary"""
        logger.info("📊 **Scan Summary:**")
        logger.info("- Total files found: %d", total_files)
        logger.info("- Files processed: %d", processed_files)
        logger.info("- Files skipped (no MD5): %d", skipped_no_hash)
        logger.info("- Files skipped (filters): %d", skipped_filters)
        logger.info("- Duplicate groups found: %d", len(duplicates))
        if processed_files > 0:
            logger.info("**All processed files with hashes:**")
            for hash_key, files in file_dict.items():
                hash_display = hash_key[:16] + "..." if len(hash_key) > 16 else hash_key
                logger.debug("**Hash %s:** %d file(s)", hash_display, len(files))
                for file in files:
                    md5_display = file['md5_hash'][:8] + "..." if file['md5_hash'] != 'fallback' and len(file['md5_hash']) > 8 else file['md5_hash']
                    logger.debug("  - %s (%s bytes, MD5: %s)", file['name'], file['size'], md5_display)
        if duplicates:
            for i, (hash_key, files) in enumerate(list(duplicates.items())[:3]):
                logger.info("**Group %d:** %d files", i+1, len(files))
                for file in files:
                    hash_type = "MD5" if file.get('has_md5') else "Name+Size"
                    logger.debug("  - %s (%s)", file['name'], hash_type)

            if len(duplicates) > 3:
                logger.info("... and %d more groups", len(duplicates) - 3)

    def scan_directory(self, directory: str, filters: ScanFilterOptions) -> Dict[str, List[str]]:
        """Scan Google Drive directory for duplicates"""

        # if not self.authenticated or not self.service:
        if not self.google_service.is_user_authenticated():
            st.error("Not authenticated with Google Drive")
            return {}

        # Handle both old string format and new dict format
        if isinstance(directory, dict):
            folder_id = directory.get('folder_id', 'root')
            recursive = directory.get('recursive', False)
        else:
            folder_id = directory
            recursive = False

        # Create a placeholder for status messages that will be reused
        status_placeholder = st.empty()

        # Initial status message
        status_placeholder.info("🔍 Scanning Google Drive for duplicates...")

        if recursive:
            status_placeholder.info("🔄 Recursive mode: Scanning all subfolders...")

        # Progress tracking
        progress_bar = st.progress(0)
        status_el = st.empty()

        try:
            file_dict = {}
            processed_files = 0
            skipped_no_hash = 0
            skipped_filters = 0

            # Get all files from the specified folder and subfolders
            all_files = self._collect_files(folder_id, recursive, status_el)
            total_files = len(all_files)
            status_el.text(f"Found {total_files} files. Analyzing for duplicates...")

            if total_files == 0:
                st.info("No files found in the selected folder")
                return {}

            # Show processing status
            status_placeholder.info(f"🔍 Processing {total_files} files from Google Drive...")

            # logger.info("**First few files found:**")
            # for i, file_info in enumerate(all_files[:5]):
            #     file_name = file_info.get('name', 'Unknown')
            #     file_size = int(file_info.get('size', 0))
            #     has_md5 = bool(file_info.get('md5Checksum'))
            #     md5_hash = file_info.get('md5Checksum', 'None')[:8] + "..." if file_info.get('md5Checksum') else 'None'
            #     folder_path = file_info.get('folder_path', 'Unknown')
            #     logger.debug(f"  %s. %s (%s bytes, MD5: %s, Has MD5: %s) - Path: %s", i+1,file_name, file_size, md5_hash, has_md5, folder_path)

            for i, file_info in enumerate(all_files):
                try:
                    # Update progress
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)
                    status_el.text(f"Processing file {i + 1}/{total_files}: {file_info['name']}")

                    # Apply filters
                    skip_reason = self._apply_file_filters(
                        file_info,
                        filters
                    )
                    if skip_reason:
                        skipped_filters += 1
                        continue

                    skipped_no_hash = self._process_file(file_info, file_dict, skipped_no_hash)
                    processed_files += 1

                except Exception as e:
                    # Skip files that cause errors
                    st.write(f"Error processing {file_info.get('name', 'unknown')}: {e}")
                    continue

            # Filter to only return groups with duplicates
            duplicates = {k: v for k, v in file_dict.items() if len(v) > 1}

            # Clean up progress indicators
            progress_bar.empty()
            status_el.empty()
            status_placeholder.empty()

            # Show scan summary
            self._show_scan_summary(total_files, processed_files, skipped_no_hash, skipped_filters, duplicates, file_dict)

            if duplicates:
                status_placeholder.empty()  # Clear the status message after showing success

                # Show some details about the duplicates found
                for i, (hash_key, files) in enumerate(list(duplicates.items())[:3]):  # Show first 3 groups
                    logger.info("**Group %d:** %d files", i+1, len(files))
                    for file in files:
                        hash_type = "MD5" if file.get('has_md5') else "Name+Size"
                        logger.debug("  - %s (%s)", file['name'], hash_type)

                if len(duplicates) > 3:
                    logger.info("... and %d more groups", len(duplicates) - 3)
            else:
                st.info("No duplicate files found in the selected folder.")

                # Suggest checking subfolders if only one file found
                if total_files == 1:
                    status_placeholder.warning("⚠️ **Only 1 file found!** Possible reasons:")
                    st.write("- Duplicate files might be in subfolders (this scan only checks the selected folder)")
                    st.write("- Files might have been filtered out")
                    st.write("- Try scanning the 'Root Folder' to include all accessible files")

            return duplicates

        except Exception as e:
            progress_bar.empty()
            status_el.empty()
            status_placeholder.empty()
            st.error(f"Error scanning Google Drive: {e}")
            return {}

    def delete_files(self, files: List[str]) -> bool:
        """Delete files from Google Drive"""
        # if not self.authenticated or not self.service:
        if not self.google_service.is_user_authenticated():
            st.error("Not authenticated with Google Drive")
            return False

        try:
            success_count = 0
            total_count = len(files)

            for file_path in files:
                file_id, file_name = extract_file_id_and_name(file_path)
                if file_id and self._delete_single_file(file_id, file_name):
                    success_count += 1

            return self._process_deletion_results(success_count, total_count)

        except Exception as e:
            st.error(f"Error during file deletion: {e}")
            return False

    def _delete_single_file(self, file_id: str, file_name: str) -> bool:
        """Delete/Trash a single file from Google Drive"""
        try:
            # Move file to trash instead of permanent deletion
            self.google_service.get_file_service().update(
                fileId=file_id,
                body={'trashed': True}
            ).execute()
            st.success(f"✅ Moved '{file_name}' to trash")
            return True
        except Exception as e:
            st.error(f"❌ Failed to delete '{file_name}': {e}")
            return False

    def _process_deletion_results(self, success_count: int, total_count: int) -> bool:
        """Process and display the results of batch deletion"""
        if success_count == total_count:
            st.success(f"Successfully moved {success_count} files to trash")
            return True
        if success_count > 0:
            st.warning(f"Moved {success_count}/{total_count} files to trash")
            return True
        return False

    def get_scan_success_msg(self, duplicate_groups: int, duplicate_files: int) -> str:
        """Return custom success message for Google Drive scan completion"""
        return f"✅ Scan complete! Found {duplicate_groups} groups containing {duplicate_files} duplicate files."

    def get_file_info(self, file: str) -> dict:
        """
        Get Google Drive file info
        base has type as str, but Google Drive files are dicts
        so we need to handle both cases.
        """
        if isinstance(file, dict):
            return get_enriched_file_info(file)

        if isinstance(file, str):
            raise ValueError("Expected file param as a dictionary, got string path instead.")

        # Fallback for string paths
        return {
            'name': 'Unknown',
            'size': 0,
            'size_formatted': human_readable_size(0),
            'extension': '',
            'path': file,
            'mime_type': '',
            'created': 'Unknown',
            'modified': 'Unknown',
            'source': 'Google Drive'
        }

    def preview_file(self, file: str):
        """Preview Google Drive file - only handles preview content, no layout"""
        if not isinstance(file, dict):
            st.info("File preview not available for this Google Drive file")
            return

        file_info = file
        file_name = file_info.get('name', 'Unknown')
        file_id = file_info.get('id', '')
        mime_type = file_info.get('mimeType', '')

        # Handle different file types
        if mime_type.startswith('image/'):
            self._preview_image(file_id, file_name)
        elif mime_type == 'application/pdf':
            self._preview_pdf(file_id)
        else:
            st.info("📁 'Open in Google Drive'")

    def get_file_extra_info(self, file_path: str) -> dict:
        """Get Google Drive specific extra information for UI display"""
        if isinstance(file_path, dict):
            file_info = file_path
            web_link = file_info.get('webViewLink', '')
            file_id = file_info.get('id', '')
            mime_type = file_info.get('mimeType', '')

            extra_info = {
                'web_link': web_link,
                'file_id': file_id,
                'mime_type': mime_type,
                'links': []
            }

            # Add Google Drive link
            if web_link:
                extra_info['links'].append({
                    'text': '🔗 Open in Google Drive',
                    'url': web_link
                })

            # Additional viewing options for images
            if file_id and mime_type.startswith('image/'):
                # Direct download link
                download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                extra_info['links'].append({
                    'text': '📥 Download Image',
                    'url': download_url
                })

                # Preview link
                preview_url = f"https://drive.google.com/file/d/{file_id}/view"
                extra_info['links'].append({
                    'text': '👁️ Preview in New Tab',
                    'url': preview_url
                })

            return extra_info

        return {'links': []}

    def get_file_path(self, file: str) -> str:
        """Get formatted file path for Google Drive files"""
        if isinstance(file, dict):
            folder_path = self.get_folder_path_from_id(file.get('parents')[0])
            return f"/{folder_path}/{file.get('name', 'Unknown')}"
        # Fallback for string paths
        return str(file)

    def _preview_image(self, file_id: str, file_name: str) -> bool:
        """Handle image file preview with multiple fallback options"""
        if not file_id:
            st.info("📋 Click the links above to view this image in Google Drive")
            return False

        # Try direct download first
        preview_success = self._handle_image_download(file_id, file_name)

        # If direct download failed, try thumbnail
        if not preview_success:
            preview_success = self._try_thumbnail_preview(file_id, file_name)

        # If both methods failed, show fallback options
        if not preview_success:
            self._show_image_fallback_options()

        return preview_success

    def _create_image_thumbnail(self, image_data: bytes, file_name: str) -> bool:
        """Create and display a square thumbnail from image data"""
        try:
            image = Image.open(io.BytesIO(image_data))

            # Create a square thumbnail
            thumbnail_size = (250, 250)
            width, height = image.size

            # Crop to square if needed
            if width != height:
                min_dimension = min(width, height)
                left = (width - min_dimension) // 2
                top = (height - min_dimension) // 2
                right = left + min_dimension
                bottom = top + min_dimension
                image = image.crop((left, top, right, bottom))

            # Create thumbnail
            image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Save thumbnail
            thumbnail_buffer = io.BytesIO()
            format_type = image.format if image.format else 'PNG'
            image.save(thumbnail_buffer, format=format_type)

            # Display
            st.image(thumbnail_buffer.getvalue(), width=250)
            return True

        except Exception as e:
            # Fallback to basic display if thumbnail creation fails
            st.image(image_data, caption=f"Preview of {file_name}", width=250)
            st.warning(f"⚠️ Could not create thumbnail: {e}")
            return True

    def _handle_image_download(self, file_id: str, file_name: str) -> bool:
        """Download and display image from Google Drive"""
        try:
            file_content = self.google_service.get_file_service().get_media(fileId=file_id).execute()
            return self._create_image_thumbnail(file_content, file_name)
        except Exception:
            return False

    def _try_thumbnail_preview(self, file_id: str, file_name: str) -> bool:
        """Try to display image using Google Drive thumbnail API"""
        try:
            st.info("🔄 Trying thumbnail preview...")
            thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w250"

            response = requests.head(thumbnail_url)
            if response.status_code == 200:
                st.image(thumbnail_url, caption=f"Preview of {file_name}", width=250)
                st.caption("📌 Thumbnail preview")
                return True
            return False
        except Exception:
            return False

    def _show_image_fallback_options(self):
        """Show fallback options when image preview fails"""
        st.info("🖼️ **Image Preview Options:**")
        st.write("• Click 'Open in Google Drive' to view the full image")
        st.write("• Click 'Preview in New Tab' for a larger view")
        st.write("• Click 'Download Image' to save locally")

    def _preview_pdf(self, file_id: str):
        """Handle PDF file preview"""
        if file_id:
            pdf_embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
            st.markdown(f"**📖 [View PDF]({pdf_embed_url})**")
