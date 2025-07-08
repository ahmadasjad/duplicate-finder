"""Google Drive storage provider implementation."""

import os
import logging
import time
from typing import Dict, List

import requests
import streamlit as st

from .google_utils import extract_file_id_and_name, get_enriched_file_info, CREDENTIALS_FILE
from ..base import BaseStorageProvider, ScanFilterOptions
from ..exceptions import NoDuplicateException, NoFileFoundException
from ...utils import get_thumbnail_from_image_data
from .authenticator import GoogleAuthenticator

logger = logging.getLogger(__name__)


def log_scan_summary(*,total_files, processed_files, skipped_no_hash, skipped_filters, duplicates, file_dict):
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

        # # Show some details about the duplicates found
        # for i, (hash_key, files) in enumerate(list(duplicates.items())[:3]):  # Show first 3 groups
        #     logger.info("**Group %d:** %d files", i+1, len(files))
        #     for file in files:
        #         hash_type = "MD5" if file.get('has_md5') else "Name+Size"
        #         logger.debug("  - %s (%s)", file['name'], hash_type)

        # if len(duplicates) > 3:
        #     logger.info("... and %d more groups", len(duplicates) - 3)


class GoogleDriveProvider(BaseStorageProvider, GoogleAuthenticator):
    """Google Drive storage provider with OAuth2 authentication"""

    def __init__(self):
        BaseStorageProvider.__init__(self, "Google Drive")
        GoogleAuthenticator.__init__(self)

    def authenticate(self) -> bool:
        return self.google_service.authenticate()
        """Simple authentication check."""
        logger.debug("Checking Google Drive authentication")

    def _check_dependencies(self):
        """Check for required Google Drive dependencies and credentials file."""
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
                folder_id = self.google_service.get_folder_id_from_path(selected_folder)
            logger.debug("Selected folder ID: %s", folder_id)
            return {
                'folder_id': folder_id,
            }

        st.info("No accessible folders found in Google Drive")
        return {
            'folder_id': "root",
        }

    def get_directory_input_widget(self):
        """Return widget for Google Drive folder selection"""
        if not self._check_dependencies():
            return None

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
            import asyncio
            folders, _ = asyncio.run(self.google_service.get_folders(parent_folder_id='root', per_page=50))
            folders = [{"name": f"My Drive/{folder['name']}", "id": folder['id']} for folder in folders]
            return self._handle_folder_selection(folders)
        except Exception as e:
            st.error("Error accessing Google Drive")
            logger.exception(e)
            return None

    async def _collect_files(self, folder_id, recursive, status_el):
        """Collect all files from the specified folder (recursively if needed)"""
        all_files = []
        if recursive:
            status_el.text("Discovering folders and files recursively...")
            all_files = await self.google_service.get_files_recursive(
                parent_folder_id=folder_id,
            )
        else:
            status_el.text("Fetching file list from Google Drive...")
            page_token = None
            while True:
                files, page_token = await self.google_service.get_files(
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

    def group_by_hash(self, file_info, file_dict, skipped_no_hash):
        """Process a single file: calculate hash, group, and update counters"""
        file_name = file_info.get('name', '')
        file_size_bytes = int(file_info.get('size', 0))
        file_hash = file_info.get('md5Checksum')
        if not file_hash:
            file_hash = f"fallback_{file_name}_{file_size_bytes}"
            skipped_no_hash += 1

        if file_hash not in file_dict:
            file_dict[file_hash] = []
        file_data ={
            'url': file_info.get('webViewLink', ''),
            'has_md5': bool(file_info.get('md5Checksum')),
            'md5_hash': file_info.get('md5Checksum', file_hash)
        }
        file_data.update(file_info)
        file_dict[file_hash].append(file_data)

        return skipped_no_hash

    def find_duplicates(self, all_files: list[dict], filters: ScanFilterOptions, progress_bar) -> Dict:
        file_dict: dict[str, list[dict]] = {}
        skipped_no_hash = 0
        skipped_filters = 0
        total_files = len(all_files)

        for i, file_info in enumerate(all_files):
            try:
                # Update progress
                if i%5 == 0:  # Update progress at every 5 files
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)

                # Apply filters
                skip_reason = self._apply_file_filters(
                    file_info,
                    filters
                )
                if skip_reason:
                    skipped_filters += 1
                    continue

                skipped_no_hash = self.group_by_hash(file_info, file_dict, skipped_no_hash)

            except Exception as e:
                # Skip files that cause errors
                st.write(f"Error processing {file_info.get('name', 'unknown')}: {e}")
                continue

        # Filter to only return groups with duplicates
        duplicates = {k: v for k, v in file_dict.items() if len(v) > 1}
        return duplicates

    def scan_directory(self, directory: dict, filters: ScanFilterOptions) -> Dict[str, List[dict]]:
        """Scan Google Drive directory for duplicates"""

        if not self.google_service.is_user_authenticated():
            st.error("Not authenticated with Google Drive")
            return {}

        # Handle both old string format and new dict format
        recursive = filters.include_subfolders
        if isinstance(directory, dict):
            folder_id = directory.get('folder_id', 'root')
            # recursive = directory.get('recursive', False)
        else:
            folder_id = directory
            # recursive = False

        # Create a placeholder for status messages that will be reused
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        status_el = st.empty()

        # Initial status message
        status_placeholder.info("🔍 Scanning Google Drive for duplicates...")

        try:
            # Get all files from the specified folder and subfolders
            import asyncio
            start_time = time.time()
            all_files = asyncio.run(self._collect_files(folder_id, recursive, status_el))
            total_files = len(all_files)
            elapsed_time = time.time() - start_time
            logger.debug("Collected %d files in %.2f seconds", total_files, elapsed_time)

            if total_files == 0:
                raise NoFileFoundException("No files found in the selected folder")

            status_el.empty()  # Clear the initial status message

            # Show processing status
            status_placeholder.info(f"Found {total_files} files. Analyzing for duplicates...")

            duplicates = self.find_duplicates(all_files, filters, progress_bar)

            # # Show scan summary
            # log_scan_summary(total_files, processed_files, skipped_no_hash, skipped_filters, duplicates, file_dict)

            if not duplicates:
                raise NoDuplicateException("No duplicate files found in the selected folder.")

            return duplicates
        except (NoDuplicateException, NoFileFoundException) as e:
            raise e # forward the exception
        except Exception as e:
            st.error("Error scanning Google Drive")
            logger.exception(e)
            return {}
        finally:
            status_placeholder.empty()
            status_el.empty()
            progress_bar.empty()

    def delete_files(self, files: List[dict]) -> bool:
        """Delete files from Google Drive"""
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
            st.error("Error during file deletion")
            logger.exception(e)
            return False

    def _delete_single_file(self, file_id: str, file_name: str) -> bool:
        """Delete/Trash a single file from Google Drive"""
        try:
            # Move the file to trash instead of permanent deletion
            self.google_service.get_file_service().update(
                fileId=file_id,
                body={'trashed': True}
            ).execute()
            st.success(f"✅ Moved '{file_name}' to trash")
            return True
        except Exception as e:
            st.error(f"❌ Failed to delete '{file_name}'")
            logger.exception(e)
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
        """Return a custom success message for Google Drive scan completion"""
        return f"✅ Scan complete! Found {duplicate_groups} groups containing {duplicate_files} duplicate files."

    def get_file_info(self, file: dict) -> dict:
        """
        Get Google Drive file info
        base has type as str, but Google Drive files are dicts
        so we need to handle both cases.
        """
        return get_enriched_file_info(file)

    def preview_file(self, file: dict):
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

    def get_file_path(self, file: dict) -> str:
        """Get the formatted file path for Google Drive files"""
        try:
            parent_id: list = file.get('parents', [])[0]
        except IndexError:
            return file.get('name', 'Unknown')
        folder_path = self.google_service.get_folder_path_from_id(parent_id)
        return f"/{folder_path}/{file.get('name', 'Unknown')}"

    def _create_image_thumbnail(self, image_data: bytes, file_name: str) -> bool:
        """Create and display a square thumbnail from image data"""
        try:
            thumbnail = get_thumbnail_from_image_data(image_data)
            st.image(thumbnail, width=250)
            return True

        except Exception as e:
            # Fallback to basic display if thumbnail creation fails
            st.image(image_data, caption=f"Preview of {file_name}", width=250)
            logger.warning("⚠️ Could not create thumbnail: %s", e)
            return True

    def _handle_image_download(self, file_id: str, file_name: str) -> bool:
        """Download and display image from Google Drive"""
        try:
            # file_content = self.google_service.get_file_service().get_media(fileId=file_id).execute()
            file_content = self.google_service.get_file_media(file_id=file_id)
            return self._create_image_thumbnail(file_content, file_name)
        except Exception as e:
            logger.exception(e)
            return False

    def _try_thumbnail_preview(self, file_id: str, file_name: str) -> bool:
        """Try to display image using Google Drive thumbnail API"""
        try:
            st.info("🔄 Trying thumbnail preview...")
            thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w250"

            response = requests.head(thumbnail_url, timeout=10)
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
        if not file_id:
            return

        try:
            pdf_content = self.google_service.get_file_media(file_id=file_id)
            if pdf_content:
                from ...preview import preview_blob_inline
                preview_blob_inline(pdf_content, 'pdf')
        except Exception as e:
            st.error(f"Error previewing PDF: {str(e)}")
            # Fallback to direct link if preview fails
            pdf_embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
            st.markdown(f"**📖 [View PDF]({pdf_embed_url})**")

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
