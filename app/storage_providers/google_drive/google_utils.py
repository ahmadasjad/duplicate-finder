import os
import streamlit as st

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import logging
from app.utils import format_iso_timestamp, human_readable_size, get_file_extension

logger = logging.getLogger(__name__)

# credentials_file
CREDENTIALS_FILE = 'credentials.json'

class GoogleService():
    def __init__(self):
        self.authenticated = False
        self.credentials = None
        self.service = None
        self._setup_credentials()

    def _setup_credentials(self):
        """Setup Google Drive API credentials"""
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

    def _generate_auth_url(self):
        """Generate authentication URL for user to visit"""
        try:

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

            if not os.path.exists(CREDENTIALS_FILE):
                return None, "credentials.json file not found"

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # For manual copy-paste flow

            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url, None

        except Exception as e:
            return None, str(e)

    def _exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token"""
        try:

            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

            # Exchange code for token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials

            # Save token
            with open('token.json', 'w', encoding='utf-8') as token:
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

    def authenticate(self) -> bool:
        """Check authentication status and return True if authenticated"""

        # If already authenticated, return True
        if self.authenticated and self.service:
            return True

        # OAuth2 configuration
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

        # Check for credentials file
        token_file = 'token.json'

        if not os.path.exists(CREDENTIALS_FILE):
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

    def is_user_authenticated(self):
        return self.authenticated

    def get_file_service(self):
        return self.service.files()

    def get_files(self, parent_folder_id: str, *, per_page: int = 100, page_token=None) -> list[dict]:
        return self.get_files_and_folders(parent_folder_id, per_page=per_page, page_token=page_token, query="not mimeType='application/vnd.google-apps.folder'")

    def get_folders(self, parent_folder_id: str, *, per_page: int = 100, page_token=None) -> list[dict]:
        return self.get_files_and_folders(parent_folder_id, per_page=per_page, page_token=page_token, query="mimeType='application/vnd.google-apps.folder'")

    def get_files_and_folders(self, parent_folder_id: str, *, per_page: int = 100, page_token=None, query=None) -> list[dict]:
        try:
            query_internal = f"'{parent_folder_id}' in parents and trashed=false"

            # Exclude Google Workspace files (Docs, Sheets, Slides, etc.)
            excluded_mimes = [
                'application/vnd.google-apps.document',
                'application/vnd.google-apps.spreadsheet',
                'application/vnd.google-apps.presentation',
                # 'application/vnd.google-apps.folder',
                'application/vnd.google-apps.form',
                'application/vnd.google-apps.drawing',
                'application/vnd.google-apps.site'
            ]

            for mime in excluded_mimes:
                query_internal += f" and not mimeType='{mime}'"

            if query:
                # query_internal += f" and ({query})"
                query_internal += f" and {query}"

            results = self.get_file_service().list(
                q=query_internal,
                pageSize=per_page,
                pageToken=page_token,
                fields="nextPageToken,files(id,name,size,mimeType,md5Checksum,parents,webViewLink,createdTime,modifiedTime)"
            ).execute()

            return results.get('files', []), results.get('nextPageToken')
        except Exception as e:
            st.error(f"Error fetching files: {e}")
            return [], None

    def get_files_recursive(self, parent_folder_id: str, *, visited_folders=None):
        """Recursively get files from Google Drive folder and all subfolders"""
        # folder_id = parent_folder_id
        logger.debug("Scanning folder_id: %s", parent_folder_id)
        if visited_folders is None:
            visited_folders = set()

        # Prevent infinite loops
        if parent_folder_id in visited_folders:
            return []

        visited_folders.add(parent_folder_id)
        all_files = []
        all_subfolders = []
        try:
            # Get files in current folder
            page_token = None
            while True:
                files_and_folders, page_token = self.get_files_and_folders(parent_folder_id, page_token=page_token)
                logger.debug("files_and_folders: %s", files_and_folders)
                files = [f for f in files_and_folders if f.get('mimeType') != 'application/vnd.google-apps.folder']
                subfolders = [f for f in files_and_folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                all_files.extend(files)
                all_subfolders.extend(subfolders)

                logger.debug("Only files: %s", all_files)
                logger.debug("Subfolders: %s", all_subfolders)

                if not page_token:
                    break

            # Get subfolders and recursively scan them
            for subfolder in all_subfolders:
                subfolder_files = self.get_files_recursive(subfolder['id'], visited_folders=visited_folders.copy())
                all_files.extend(subfolder_files)

        except Exception as e:
            st.warning(f"Error scanning folder {parent_folder_id}: {e}")

        return all_files

    def get_file_info(self, file_id: str) -> dict:
        return self.get_file_detail(file_id)

    def get_file_detail(self, file_id: str) -> dict:
        """Retrieve file info from Google Drive by file ID"""
        if not self.service:
            logger.error("Google Drive service is not initialized.")
            return {}

        try:
            file = self.service.files().get(fileId=file_id, fields='*').execute()
            return get_enriched_file_info(file)
        except Exception as e:
            logger.error(f"Failed to retrieve file info: {e}")
            return {}

    def get_folder_info(self, folder_id: str) -> dict:
        return self.get_folder_detail(folder_id)

    def get_folder_detail(self, folder_id: str) -> dict:
        return self.get_file_info(folder_id)



def extract_file_id_and_name(file: dict) -> tuple[str, str]:
    """Extract file ID and name from Google Drive file dictionary"""
    return file.get('id'), file.get('name', 'Unknown')


def extract_time_info(file_info: dict) -> tuple[str, str]:
    """Extract and format creation and modification times from file info"""
    logger.debug("Extracting time info from file:")
    logger.debug(file_info)
    created_time = file_info.get('createdTime', '')
    modified_time = file_info.get('modifiedTime', '')

    created_formatted = format_iso_timestamp(created_time) if created_time else 'Unknown'
    modified_formatted = format_iso_timestamp(modified_time) if modified_time else 'Unknown'

    return created_formatted, modified_formatted


def get_enriched_file_info(file: dict) -> dict:
    """Create a standardized file info dictionary from Google Drive file info"""
    # Extract timestamps
    created_formatted, modified_formatted = extract_time_info(file)

    # Get file size
    size_bytes = int(file.get('size', 0))

    enriched_info = {
        'name': file.get('name', 'Unknown'),
        'size': size_bytes,
        'size_formatted': human_readable_size(size_bytes),
        'extension': get_file_extension(file.get('name', '')),
        'path': file.get('webViewLink', file.get('id', '')),
        'mime_type': file.get('mimeType', ''),
        'created': created_formatted,
        'modified': modified_formatted,
        'source': 'Google Drive'
    }
    enriched_info.update(file)

    return enriched_info
