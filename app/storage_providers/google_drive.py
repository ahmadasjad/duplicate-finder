import io
import os
import logging
import requests
import streamlit as st
from typing import Dict, List, Optional
from .base import BaseStorageProvider
from ..utils import human_readable_size

logger = logging.getLogger(__name__)


class GoogleAuthenticator:
    def __init__(self):
        self.authenticated = False
        self.credentials = None
        self.service = None
        self._setup_credentials()

    def _setup_credentials(self):
        """Setup Google Drive API credentials"""
        import streamlit as st

        # Check if credentials are already stored in session state
        if 'gdrive_credentials' in st.session_state:
            self.credentials = st.session_state.gdrive_credentials
            self.authenticated = True
            self._build_service()

    def _build_service(self):
        """Build Google Drive API service"""
        try:
            from googleapiclient.discovery import build
            if self.credentials:
                self.service = build('drive', 'v3', credentials=self.credentials)
                return True
        except ImportError:
            return False
        return False

    def _perform_oauth_flow(self):
        """Perform OAuth flow directly in the application"""
        import streamlit as st

        st.markdown("### 🔐 Google Drive Authentication")

        # Generate auth URL
        auth_url, error = self._generate_auth_url()
        if error:
            st.error(f"Failed to generate authentication URL: {error}")
            return False

        if auth_url:
            # Step 1: Show authorization URL
            st.markdown("**Step 1:** Click the link below to authorize access:")
            st.markdown(f"🔗 **[Authorize Google Drive Access]({auth_url})**")

            # Important note about OAuth consent screen
            st.info("""
            💡 **Important**: If you get an "access_denied" error, you need to add your email as a test user:

            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Select your project → APIs & Services → OAuth consent screen
            3. Add your email to "Test users" section
            """)

            # Step 2: Get authorization code
            st.markdown("**Step 2:** Copy the authorization code and paste it below:")

            auth_code = st.text_input(
                "Authorization Code:",
                placeholder="Paste the authorization code here...",
                help="After clicking the link above, Google will show you an authorization code. Copy and paste it here.",
                key="gdrive_auth_code"
            )

            if auth_code and st.button("✅ Complete Authentication", type="primary"):
                with st.spinner("Completing authentication..."):
                    success, error = self._exchange_code_for_token(auth_code.strip())

                    if success:
                        st.success("🎉 Authentication successful!")
                        st.balloons()
                        st.session_state.gdrive_auth_flow = False
                        return True
                    st.error(f"❌ Authentication failed: {error}")
                    st.info("Please check the authorization code and try again.")
                    return False

        return False

    def _generate_auth_url(self):
        """Generate authentication URL for user to visit"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials_file = 'credentials.json'

            if not os.path.exists(credentials_file):
                return None, "credentials.json file not found"

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # For manual copy-paste flow

            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url, None

        except Exception as e:
            return None, str(e)

    def _exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token"""
        try:
            import streamlit as st
            from google_auth_oauthlib.flow import InstalledAppFlow

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            credentials_file = 'credentials.json'

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

            # Exchange code for token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials

            # Save token
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

            # Update instance
            self.credentials = creds
            st.session_state.gdrive_credentials = creds

            if self._build_service():
                self.authenticated = True
                return True, None
            return False, "Failed to build Google Drive service"

        except Exception as e:
            error_message = str(e)

            # Handle common OAuth errors with helpful messages
            if "access_denied" in error_message:
                return False, """
🚫 **Access Denied - OAuth Consent Screen Issue**

This error usually means your app is in testing mode and you need to add your email as a test user:

**Fix Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project 'duplicate-file-finder-464317'
3. Go to APIs & Services → OAuth consent screen
4. Scroll to "Test users" section
5. Click "+ ADD USERS"
6. Add your email address
7. Click Save and try again

**Alternative:** You can also publish your OAuth consent screen to make it available to all users.
"""
            if "invalid_grant" in error_message:
                return False, """
⏰ **Invalid Grant - Code Expired**

The authorization code has expired or was already used.

**Fix:** Click the authorization link again to get a new code.
"""
            if "invalid_request" in error_message:
                return False, """
📝 **Invalid Request - Code Format Issue**

The authorization code format is incorrect.

**Fix:** Make sure you copied the complete authorization code from Google.
"""

            return False, f"Authentication error: {error_message}"


class GoogleDriveProvider(BaseStorageProvider, GoogleAuthenticator):
    """Google Drive storage provider with OAuth2 authentication"""

    def __init__(self):
        BaseStorageProvider.__init__(self, "Google Drive")
        GoogleAuthenticator.__init__(self)

    def authenticate(self) -> bool:
        """Check authentication status and return True if authenticated"""
        import streamlit as st

        # Check if required packages are installed
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import Flow
            from googleapiclient.discovery import build
        except ImportError:
            return False  # Dependencies not available

        # If already authenticated, return True
        if self.authenticated and self.service:
            return True

        # OAuth2 configuration
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

        # Check for credentials file
        credentials_file = 'credentials.json'
        token_file = 'token.json'

        if not os.path.exists(credentials_file):
            return False  # Setup required

        creds = None

        # Load existing token
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # Check if credentials are valid
        if creds and creds.valid:
            # Save credentials and build service
            self.credentials = creds
            st.session_state.gdrive_credentials = creds

            if self._build_service():
                self.authenticated = True
                return True

        # Try to refresh expired credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.credentials = creds
                st.session_state.gdrive_credentials = creds

                # Save refreshed token
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())

                if self._build_service():
                    self.authenticated = True
                    return True
            except Exception:
                pass

        return False  # Not authenticated

    def get_directory_input_widget(self):
        """Return widget for Google Drive folder selection"""
        import streamlit as st

        # Check if required packages are installed
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import Flow
            from googleapiclient.discovery import build
        except ImportError:
            st.error("📦 **Missing Dependencies**")
            st.markdown("""
            To use Google Drive integration, install the required packages:
            ```bash
            pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
            ```
            """)
            return None

        # Check for credentials file
        credentials_file = 'credentials.json'
        if not os.path.exists(credentials_file):
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
            return None

        if not self.authenticated:
            st.warning("🔐 Authentication required for Google Drive access")

            # Check if we have credentials file but no token
            token_file = 'token.json'
            if not os.path.exists(token_file):
                st.info("🔐 **Easy Authentication Setup**")

                # Check if we're in authentication flow
                if 'gdrive_auth_flow' not in st.session_state:
                    st.session_state.gdrive_auth_flow = False

                if not st.session_state.gdrive_auth_flow:
                    # Option 1: Start direct authentication
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        if st.button("🚀 Start Authentication", type="primary", help="Click to start the OAuth flow"):
                            st.session_state.gdrive_auth_flow = True
                            st.rerun()

                    with col2:
                        if st.button("🔄 Check Status", help="Check if authentication is complete"):
                            st.rerun()

                    st.markdown("---")

                    # Option 2: Upload token file
                    st.markdown("**Alternative: Upload Token File**")
                    st.caption("If you have a token.json file from a previous authentication:")

                    uploaded_token = st.file_uploader(
                        "Upload token.json file",
                        type=['json'],
                        help="Upload a previously saved token.json file"
                    )

                    if uploaded_token is not None:
                        try:
                            # Save the uploaded token file
                            with open('token.json', 'wb') as f:
                                f.write(uploaded_token.getbuffer())
                            st.success("Token file uploaded successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save token file: {e}")
                else:
                    # Show OAuth flow
                    if self._perform_oauth_flow():
                        st.session_state.gdrive_auth_flow = False
                        st.rerun()

                    if st.button("⬅️ Back"):
                        st.session_state.gdrive_auth_flow = False
                        st.rerun()
            else:
                if st.button("🔄 Refresh Authentication", type="primary"):
                    st.rerun()
            return None

        # Show connection status with user identity
        user_info = self._get_user_info()
        if user_info:
            st.success(f"✅ Connected to Google Drive as **{user_info['name']}** ({user_info['email']})")
        else:
            st.success("✅ Connected to Google Drive")

        # Get available folders
        try:
            folders = self._get_folders()

            # Create folder options
            folder_options = ["Root Folder"]
            folder_map = {"Root Folder": "root"}

            for folder in folders:
                display_name = f"📁 {folder['name']}"
                folder_options.append(display_name)
                folder_map[display_name] = folder['id']

            # Add option for manual folder ID entry
            folder_options.append("🔧 Enter Folder ID/Path Manually")

            if folder_options:
                selected_folder = st.selectbox(
                    "Select Google Drive folder to scan:",
                    folder_options,
                    help="Choose a folder to scan for duplicate files"
                )

                # Handle manual folder ID entry
                if selected_folder == "🔧 Enter Folder ID/Path Manually":
                    manual_folder = st.text_input(
                        "Enter Google Drive Folder ID or URL:",
                        placeholder="e.g., 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms or https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                        help="Enter the folder ID or paste the full Google Drive folder URL"
                    )

                    if manual_folder:
                        # Extract folder ID from URL if necessary
                        if "drive.google.com" in manual_folder:
                            import re
                            folder_id_match = re.search(r'/folders/([a-zA-Z0-9-_]+)', manual_folder)
                            if folder_id_match:
                                folder_id = folder_id_match.group(1)
                                st.success(f"Extracted folder ID: {folder_id}")
                            else:
                                st.error("Could not extract folder ID from URL")
                                return None
                        else:
                            folder_id = manual_folder.strip()

                        # Add recursive option
                        include_subfolders = st.checkbox(
                            "🔄 Include subfolders (recursive scan)",
                            value=True,
                            help="Scan all subfolders within the selected folder"
                        )

                        return {
                            'folder_id': folder_id,
                            'recursive': include_subfolders
                        }
                    return None
                else:
                    folder_id = folder_map.get(selected_folder, "root")

                    # Add recursive option for selected folders
                    include_subfolders = st.checkbox(
                        "🔄 Include subfolders (recursive scan)",
                        value=True,
                        help="Scan all subfolders within the selected folder"
                    )

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

        except Exception as e:
            st.error(f"Error accessing Google Drive: {e}")
            return None

    def _get_user_info(self):
        """Get user information from Google Drive API"""
        try:
            # Get user info from the Drive API
            about = self.service.about().get(fields="user").execute()
            user = about.get('user', {})

            return {
                'name': user.get('displayName', 'Unknown User'),
                'email': user.get('emailAddress', 'Unknown Email'),
                'photo': user.get('photoLink', '')
            }
        except Exception:
            # Fallback: try to get info from OAuth2 userinfo API
            try:
                from googleapiclient.discovery import build
                userinfo_service = build('oauth2', 'v2', credentials=self.credentials)
                user_info = userinfo_service.userinfo().get().execute()

                return {
                    'name': user_info.get('name', 'Unknown User'),
                    'email': user_info.get('email', 'Unknown Email'),
                    'photo': user_info.get('picture', '')
                }
            except Exception:
                return None

    def _get_folders(self, parent_id='root', limit=50):
        """Get list of folders from Google Drive"""
        try:
            query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id,name,parents)"
            ).execute()
            return results.get('files', [])
        except Exception:
            return []

    def _get_files(self, folder_id='root', page_token=None):
        """Get files from a Google Drive folder"""
        try:
            query = f"'{folder_id}' in parents and trashed=false"

            # Exclude Google Workspace files (Docs, Sheets, Slides, etc.)
            excluded_mimes = [
                'application/vnd.google-apps.document',
                'application/vnd.google-apps.spreadsheet',
                'application/vnd.google-apps.presentation',
                'application/vnd.google-apps.folder',
                'application/vnd.google-apps.form',
                'application/vnd.google-apps.drawing',
                'application/vnd.google-apps.site'
            ]

            for mime in excluded_mimes:
                query += f" and not mimeType='{mime}'"

            results = self.service.files().list(
                q=query,
                pageSize=100,
                pageToken=page_token,
                fields="nextPageToken,files(id,name,size,mimeType,md5Checksum,parents,webViewLink,createdTime,modifiedTime)"
            ).execute()

            return results.get('files', []), results.get('nextPageToken')
        except Exception as e:
            import streamlit as st
            st.error(f"Error fetching files: {e}")
            return [], None

    def _get_files_recursive(self, folder_id='root', visited_folders=None):
        """Recursively get files from Google Drive folder and all subfolders"""
        if visited_folders is None:
            visited_folders = set()

        # Prevent infinite loops
        if folder_id in visited_folders:
            return []

        visited_folders.add(folder_id)
        all_files = []

        try:
            # Get files in current folder
            page_token = None
            while True:
                files, page_token = self._get_files(folder_id, page_token)
                for file in files:
                    # Add folder path information for debugging
                    file['folder_id'] = folder_id
                    if folder_id == 'root':
                        file['folder_path'] = 'Root'
                    else:
                        try:
                            folder_info = self.service.files().get(fileId=folder_id, fields="name").execute()
                            file['folder_path'] = folder_info.get('name', 'Unknown')
                        except:
                            file['folder_path'] = folder_id[:8] + "..."

                all_files.extend(files)
                if not page_token:
                    break

            # Get subfolders and recursively scan them
            subfolders = self._get_folders(folder_id)
            for subfolder in subfolders:
                subfolder_files = self._get_files_recursive(subfolder['id'], visited_folders.copy())
                all_files.extend(subfolder_files)

        except Exception as e:
            import streamlit as st
            st.warning(f"Error scanning folder {folder_id}: {e}")

        return all_files

    def scan_directory(self, directory, exclude_shortcuts: bool = True,
                      exclude_hidden: bool = True, exclude_system: bool = True,
                      min_size_kb: int = 0, max_size_kb: int = 0) -> Dict[str, List[str]]:
        """Scan Google Drive directory for duplicates"""
        import streamlit as st
        import time

        if not self.authenticated or not self.service:
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

        # Function to display a status message for at least 5 seconds
        # last_message_time = [time.time()]  # Using list to make it mutable in nested function

        # def show_status(message):
        #     # current_time = time.time()
        #     # # Ensure previous message showed for at least 5 seconds
        #     # if current_time - last_message_time[0] < 5:
        #     #     time.sleep(5 - (current_time - last_message_time[0]))
        #     # Update the message and time
        #     status_placeholder.info(message)
        #     # last_message_time[0] = time.time()

        # Initial status message
        status_placeholder.info("🔍 Scanning Google Drive for duplicates...")

        if recursive:
            status_placeholder.info("🔄 Recursive mode: Scanning all subfolders...")

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            file_dict = {}
            processed_files = 0
            total_files = 0
            skipped_no_hash = 0
            skipped_filters = 0

            # Get all files from the specified folder and subfolders
            all_files = []

            if recursive:
                status_text.text("Discovering folders and files recursively...")
                all_files = self._get_files_recursive(folder_id)
            else:
                status_text.text("Fetching file list from Google Drive...")
                page_token = None
                while True:
                    files, page_token = self._get_files(folder_id, page_token)
                    all_files.extend(files)
                    if not page_token:
                        break

            total_files = len(all_files)
            status_text.text(f"Found {total_files} files. Analyzing for duplicates...")

            if total_files == 0:
                st.info("No files found in the selected folder")
                return {}

            # Show processing status
            status_placeholder.info(f"🔍 Processing {total_files} files from Google Drive...")

            # Show first few files for debugging
            if total_files > 0:
                logger.info("**First few files found:**")
                for i, file_info in enumerate(all_files[:5]):
                    file_name = file_info.get('name', 'Unknown')
                    file_size = int(file_info.get('size', 0))
                    has_md5 = bool(file_info.get('md5Checksum'))
                    md5_hash = file_info.get('md5Checksum', 'None')[:8] + "..." if file_info.get('md5Checksum') else 'None'
                    folder_path = file_info.get('folder_path', 'Unknown')
                    logger.debug(f"  %s. %s (%s bytes, MD5: %s, Has MD5: %s) - Path: %s", i+1,file_name, file_size, md5_hash, has_md5, folder_path)

            for i, file_info in enumerate(all_files):
                try:
                    # Update progress
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)
                    status_text.text(f"Processing file {i + 1}/{total_files}: {file_info['name']}")

                    # Apply filters
                    file_name = file_info.get('name', '')
                    file_size_bytes = int(file_info.get('size', 0))
                    file_size_kb = file_size_bytes / 1024

                    # Debug: Log filter decisions
                    skip_reason = None

                    # Skip hidden files
                    if exclude_hidden and file_name.startswith('.'):
                        skipped_filters += 1
                        skip_reason = "hidden file"
                        continue

                    # Skip by size
                    if file_size_kb < min_size_kb:
                        skipped_filters += 1
                        skip_reason = f"too small ({file_size_kb:.1f} KB < {min_size_kb} KB)"
                        continue
                    if max_size_kb > 0 and file_size_kb > max_size_kb:
                        skipped_filters += 1
                        skip_reason = f"too large ({file_size_kb:.1f} KB > {max_size_kb} KB)"
                        continue

                    # Use MD5 checksum if available, otherwise use name + size for basic duplicate detection
                    file_hash = file_info.get('md5Checksum')
                    if not file_hash:
                        # Fallback: use filename and size as identifier for files without MD5
                        # This is less accurate but better than skipping files entirely
                        file_hash = f"fallback_{file_name}_{file_size_bytes}"
                        skipped_no_hash += 1

                    # Create file identifier (use webViewLink for easy access)
                    file_id = file_info.get('webViewLink', file_info.get('id', ''))

                    # Group by hash
                    if file_hash not in file_dict:
                        file_dict[file_hash] = []

                    file_dict[file_hash].append({
                        'path': file_id,
                        'name': file_name,
                        'size': file_size_bytes,
                        'id': file_info.get('id', ''),
                        'mimeType': file_info.get('mimeType', ''),
                        'webViewLink': file_info.get('webViewLink', ''),
                        'has_md5': bool(file_info.get('md5Checksum')),
                        'md5_hash': file_info.get('md5Checksum', 'fallback')
                    })

                    processed_files += 1

                except Exception as e:
                    # Skip files that cause errors
                    st.write(f"Error processing {file_info.get('name', 'unknown')}: {e}")
                    continue

            # Filter to only return groups with duplicates
            duplicates = {k: v for k, v in file_dict.items() if len(v) > 1}

            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()
            status_placeholder.empty()  # Clean up our status messages placeholder

            # Show detailed results
            logger.info(f"📊 **Scan Summary:**")
            logger.info(f"- Total files found: {total_files}")
            logger.info(f"- Files processed: {processed_files}")
            logger.info(f"- Files skipped (no MD5): {skipped_no_hash}")
            logger.info(f"- Files skipped (filters): {skipped_filters}")
            logger.info(f"- Duplicate groups found: {len(duplicates)}")

            # Debug: Show all processed files and their hashes
            if processed_files > 0:
                logger.info("**All processed files with hashes:**")
                for hash_key, files in file_dict.items():
                    hash_display = hash_key[:16] + "..." if len(hash_key) > 16 else hash_key
                    logger.debug(f"**Hash {hash_display}:** {len(files)} file(s)")
                    for file in files:
                        md5_display = file['md5_hash'][:8] + "..." if file['md5_hash'] != 'fallback' and len(file['md5_hash']) > 8 else file['md5_hash']
                        logger.debug(f"  - {file['name']} ({file['size']} bytes, MD5: {md5_display})")

            if duplicates:
                duplicate_count = sum(len(group) for group in duplicates.values())
                # status_placeholder.success(f"✅ Scan complete! Found {len(duplicates)} groups containing {duplicate_count} duplicate files.")
                status_placeholder.empty()  # Clear the status message after showing success

                # Show some details about the duplicates found
                for i, (hash_key, files) in enumerate(list(duplicates.items())[:3]):  # Show first 3 groups
                    logger.info(f"**Group {i+1}:** {len(files)} files")
                    for file in files:
                        hash_type = "MD5" if file.get('has_md5') else "Name+Size"
                        logger.debug(f"  - {file['name']} ({hash_type})")

                if len(duplicates) > 3:
                    logger.info(f"... and {len(duplicates) - 3} more groups")
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
            status_text.empty()
            status_placeholder.empty()  # Clean up our status messages placeholder
            st.error(f"Error scanning Google Drive: {e}")
            return {}

    def delete_files(self, files: List[str]) -> bool:
        """Delete files from Google Drive"""
        if not self.authenticated or not self.service:
            st.error("Not authenticated with Google Drive")
            return False

        try:
            success_count = 0
            total_count = len(files)

            for file_path in files:
                file_id, file_name = self._extract_file_id_and_name(file_path)
                if file_id and self._delete_single_file(file_id, file_name):
                    success_count += 1

            return self._process_deletion_results(success_count, total_count)

        except Exception as e:
            st.error(f"Error during file deletion: {e}")
            return False

    def _extract_file_id_and_name(self, file: dict) -> tuple[str, str]:
        """Extract file ID and name from Google Drive file dictionary"""
        return file.get('id'), file.get('name', 'Unknown')

    def _delete_single_file(self, file_id: str, file_name: str) -> bool:
        """Delete/Trash a single file from Google Drive"""
        try:
            # Move file to trash instead of permanent deletion
            self.service.files().update(
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
        elif success_count > 0:
            st.warning(f"Moved {success_count}/{total_count} files to trash")
            return True
        return False

    def get_scan_success_msg(self, duplicate_groups: int, duplicate_count: int) -> str:
        """Return custom success message for Google Drive scan completion"""
        return f"✅ Scan complete! Found {duplicate_groups} groups containing {duplicate_count} duplicate files."

    def _format_timestamp(self, timestamp: str, default: str = 'Unknown') -> str:
        """Format ISO timestamp to readable format"""
        if not timestamp:
            return default

        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return timestamp

    def _extract_time_info(self, file_info: dict) -> tuple[str, str]:
        """Extract and format creation and modification times from file info"""
        created_time = file_info.get('createdTime', '')
        modified_time = file_info.get('modifiedTime', '')

        created_formatted = self._format_timestamp(created_time) if created_time else 'Unknown'
        modified_formatted = self._format_timestamp(modified_time) if modified_time else 'Unknown'

        return created_formatted, modified_formatted

    def _create_file_info_dict(self, file_info: dict) -> dict:
        """Create a standardized file info dictionary from Google Drive file info"""
        # Extract timestamps
        created_formatted, modified_formatted = self._extract_time_info(file_info)

        # Get file size
        size_bytes = int(file_info.get('size', 0))

        return {
            'name': file_info.get('name', 'Unknown'),
            'size': size_bytes,
            'size_formatted': human_readable_size(size_bytes),
            'extension': self._get_file_extension(file_info.get('name', '')),
            'path': file_info.get('webViewLink', file_info.get('id', '')),
            'mime_type': file_info.get('mimeType', ''),
            'created': created_formatted,
            'modified': modified_formatted,
            'source': 'Google Drive'
        }

    def get_file_info(self, file: str) -> dict:
        """Get Google Drive file info"""
        if isinstance(file, dict):
            return self._create_file_info_dict(file)
        else:
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

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if '.' in filename:
            return filename.rsplit('.', 1)[-1].lower()
        return ''

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
            # For Google Drive, use the full path if available
            if 'full_path' in file:
                return file['full_path']
            else:
                # Fallback to constructing path from available info
                folder_path = file.get('folder_path', 'Root')
                file_name = file.get('name', 'Unknown')
                return f"/{folder_path}/{file_name}" if folder_path != 'Root' else f"/Root/{file_name}"
        else:
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
            from PIL import Image
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

        except ImportError:
            # Fallback if PIL not available
            st.image(image_data, caption=f"Preview of {file_name}", width=250)
            st.success("✅ Image loaded from Google Drive (install Pillow for better thumbnails)")
            return True

        except Exception as e:
            # Fallback to basic display if thumbnail creation fails
            st.image(image_data, caption=f"Preview of {file_name}", width=250)
            st.warning(f"⚠️ Could not create thumbnail: {e}")
            return True

    def _handle_image_download(self, file_id: str, file_name: str) -> bool:
        """Download and display image from Google Drive"""
        try:
            file_content = self.service.files().get_media(fileId=file_id).execute()
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
