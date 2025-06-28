import os
import hashlib
import json
from typing import Dict, List, Optional
from .base import BaseStorageProvider


class GoogleAuthenticator:

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
                    else:
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
            else:
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
            elif "invalid_grant" in error_message:
                return False, """
⏰ **Invalid Grant - Code Expired**

The authorization code has expired or was already used.

**Fix:** Click the authorization link again to get a new code.
"""
            elif "invalid_request" in error_message:
                return False, """
📝 **Invalid Request - Code Format Issue**

The authorization code format is incorrect.

**Fix:** Make sure you copied the complete authorization code from Google.
"""
            else:
                return False, f"Authentication error: {error_message}"


class GoogleDriveProvider(BaseStorageProvider, GoogleAuthenticator):
    """Google Drive storage provider with OAuth2 authentication"""

    def __init__(self):
        super().__init__("Google Drive")
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

            if folder_options:
                selected_folder = st.selectbox(
                    "Select Google Drive folder to scan:",
                    folder_options,
                    help="Choose a folder to scan for duplicate files"
                )
                return folder_map.get(selected_folder, "root")
            else:
                st.info("No accessible folders found in Google Drive")
                return "root"

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
                fields="nextPageToken,files(id,name,size,mimeType,md5Checksum,parents,webViewLink)"
            ).execute()

            return results.get('files', []), results.get('nextPageToken')
        except Exception as e:
            import streamlit as st
            st.error(f"Error fetching files: {e}")
            return [], None

    def scan_directory(self, directory: str, exclude_shortcuts: bool = True,
                      exclude_hidden: bool = True, exclude_system: bool = True,
                      min_size_kb: int = 0, max_size_kb: int = 0) -> Dict[str, List[str]]:
        """Scan Google Drive directory for duplicates"""
        import streamlit as st

        if not self.authenticated or not self.service:
            st.error("Not authenticated with Google Drive")
            return {}

        st.info("🔍 Scanning Google Drive for duplicates...")

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            file_dict = {}
            processed_files = 0
            total_files = 0

            # Get all files from the specified folder
            page_token = None
            all_files = []

            status_text.text("Fetching file list from Google Drive...")

            while True:
                files, page_token = self._get_files(directory, page_token)
                all_files.extend(files)

                if not page_token:
                    break

            total_files = len(all_files)
            status_text.text(f"Found {total_files} files. Analyzing for duplicates...")

            if total_files == 0:
                st.info("No files found in the selected folder")
                return {}

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

                    # Skip hidden files
                    if exclude_hidden and file_name.startswith('.'):
                        continue

                    # Skip by size
                    if file_size_kb < min_size_kb:
                        continue
                    if max_size_kb > 0 and file_size_kb > max_size_kb:
                        continue

                    # Use MD5 checksum if available, otherwise skip
                    file_hash = file_info.get('md5Checksum')
                    if not file_hash:
                        continue

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
                        'webViewLink': file_info.get('webViewLink', '')
                    })

                    processed_files += 1

                except Exception as e:
                    # Skip files that cause errors
                    continue

            # Filter to only return groups with duplicates
            duplicates = {k: v for k, v in file_dict.items() if len(v) > 1}

            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()

            if duplicates:
                duplicate_count = sum(len(group) for group in duplicates.values())
                st.success(f"✅ Scan complete! Found {len(duplicates)} groups containing {duplicate_count} duplicate files.")
            else:
                st.info("No duplicate files found in the selected folder.")

            return duplicates

        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error scanning Google Drive: {e}")
            return {}

    def delete_files(self, file_paths: List[str]) -> bool:
        """Delete files from Google Drive"""
        import streamlit as st

        if not self.authenticated or not self.service:
            st.error("Not authenticated with Google Drive")
            return False

        try:
            success_count = 0
            total_count = len(file_paths)

            for file_path in file_paths:
                try:
                    # Extract file ID from path (assumes file_path contains file metadata)
                    if isinstance(file_path, dict):
                        file_id = file_path.get('id')
                        file_name = file_path.get('name', 'Unknown')
                    else:
                        # Fallback for string paths - not ideal but handles edge cases
                        file_id = file_path
                        file_name = file_path

                    if file_id:
                        # Move file to trash instead of permanent deletion
                        self.service.files().update(
                            fileId=file_id,
                            body={'trashed': True}
                        ).execute()
                        success_count += 1
                        st.success(f"✅ Moved '{file_name}' to trash")

                except Exception as e:
                    st.error(f"❌ Failed to delete '{file_name}': {e}")

            if success_count == total_count:
                st.success(f"Successfully moved {success_count} files to trash")
                return True
            else:
                st.warning(f"Moved {success_count}/{total_count} files to trash")
                return success_count > 0

        except Exception as e:
            st.error(f"Error during file deletion: {e}")
            return False

    def get_file_info(self, file_path: str) -> dict:
        """Get Google Drive file info"""
        if isinstance(file_path, dict):
            # File path is already a file info dict
            file_info = file_path
            return {
                'name': file_info.get('name', 'Unknown'),
                'size': file_info.get('size', 0),
                'extension': self._get_file_extension(file_info.get('name', '')),
                'path': file_info.get('webViewLink', file_info.get('id', '')),
                'mime_type': file_info.get('mimeType', ''),
                'source': 'Google Drive'
            }
        else:
            # Fallback for string paths
            return {
                'name': 'Unknown',
                'size': 0,
                'extension': '',
                'path': file_path,
                'mime_type': '',
                'source': 'Google Drive'
            }

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if '.' in filename:
            return filename.rsplit('.', 1)[-1].lower()
        return ''

    def preview_file(self, file_path: str):
        """Preview Google Drive file"""
        import streamlit as st

        if isinstance(file_path, dict):
            file_info = file_path
            file_name = file_info.get('name', 'Unknown')
            web_link = file_info.get('webViewLink', '')
            mime_type = file_info.get('mimeType', '')

            st.subheader(f"📄 {file_name}")

            if web_link:
                st.markdown(f"**🔗 [Open in Google Drive]({web_link})**")

            st.write(f"**Type:** {mime_type}")
            st.write(f"**Size:** {self._format_file_size(int(file_info.get('size', 0)))}")

            # For images, try to show preview (if publicly accessible)
            if mime_type.startswith('image/'):
                st.write("**Preview:**")
                st.info("Image preview requires public sharing. Click the link above to view in Google Drive.")

        else:
            st.info("File preview not available for this Google Drive file")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

