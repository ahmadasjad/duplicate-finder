import os
import logging
import requests

from typing import Union
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.utils import format_iso_timestamp, human_readable_size, get_file_extension

logger = logging.getLogger(__name__)

# credentials_file
CREDENTIALS_FILE = '.local/credentials.json'
TOKEN_FILE = '.local/token.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleService():
    def __init__(self):
        self.authenticated = False
        self.credentials = None
        self.service = None
        self._setup_credentials()
        self.folder_id_to_path = {}  # Cache for folder ID to path mapping
        self.folder_path_to_id = {}  # Cache for folder paths to ID mapping
        # Initialize drive cache for files
        from .cache_manager import DriveCache
        self.drive_cache = DriveCache()

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

    def generate_auth_url(self):
        """Generate authentication URL for user to visit"""
        try:
            if not os.path.exists(CREDENTIALS_FILE):
                return None, "credentials.json file not found"

            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # For manual copy-paste flow

            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url, None

        except Exception as e:
            return None, str(e)

    def exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token"""
        try:
            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

            # Exchange code for token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials

            # Save token
            with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
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
            logger.debug("Already authenticated with Google Drive")
            return True

        # Check for credentials file
        logger.debug("Checking Google Drive credentials in file: %s", CREDENTIALS_FILE)
        if not os.path.exists(CREDENTIALS_FILE):
            logger.error("Google Drive credentials file not found: %s", CREDENTIALS_FILE)
            return False  # Setup required

        creds = None

        # Load existing token
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

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
            logger.debug("Refreshing expired Google Drive credentials")
            try:
                creds.refresh(Request())
                self.credentials = creds
                st.session_state.gdrive_credentials = creds

                # Save refreshed token
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())

                if self._build_service():
                    self.authenticated = True
                    return True
            except Exception as e:
                logger.error("Failed to refresh Google Drive credentials: %s", e)
                if os.path.exists(TOKEN_FILE):
                    try:
                        os.remove(TOKEN_FILE)
                        logger.warning("Deleted invalid token file: %s", TOKEN_FILE)
                    except Exception as delete_error:
                        logger.error("Failed to delete token file: %s", delete_error)

        logger.debug("Google Drive authentication failed")
        return False  # Not authenticated

    def is_user_authenticated(self):
        return self.authenticated

    def get_file_service(self):
        logger.debug("Getting Google Drive file service")
        return self.service.files()

    async def get_files(self, parent_folder_id: str, *, per_page: int = 100, page_token=None) -> tuple:
        return await self.get_files_and_folders(
            parent_folder_id, per_page=per_page, page_token=page_token,
            query="not mimeType='application/vnd.google-apps.folder'"
        )

    async def get_folders(self, parent_folder_id: str, *, per_page: int = 100, page_token=None) -> tuple:
        return await self.get_files_and_folders(
            parent_folder_id, per_page=per_page, page_token=page_token,
            query="mimeType='application/vnd.google-apps.folder'"
        )

    async def get_files_and_folders(self, parent_folder_id: str, *, per_page: int = 100, page_token=None, query=None) -> tuple:
        try:
            query_internal = f"'{parent_folder_id}' in parents and trashed=false"

            # Exclude Google Workspace files (Docs, Sheets, Slides, etc.)
            excluded_mimes = [
                'application/vnd.google-apps.shortcut'
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

    async def get_files_recursive(self, parent_folder_id: str, *, visited_folders=None):
        """Recursively get files from Google Drive folder and all subfolders"""
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
            # Try to get subfolders from cache first
            cached_subfolders = self.drive_cache.get_cached_subfolders(parent_folder_id)
            cached_files = self.drive_cache.get_cached_files(parent_folder_id, recursive=False)

            if cached_files is not None or cached_subfolders is not None: # use cache if available
                logger.debug(f"Using cached files or subfolders for {parent_folder_id}")
                if cached_files:
                    all_files.extend(cached_files)
                if cached_subfolders:
                    all_subfolders.extend(cached_subfolders)
            else: # use API if cache is not available
                logger.debug(f"No cache found for {parent_folder_id}, fetching from API")

                # Get both files and folders from API
                page_token = None
                while True:
                    files_and_folders, page_token = await self.get_files_and_folders(parent_folder_id, page_token=page_token)
                    logger.debug("files_and_folders: %s", files_and_folders)
                    files = [f for f in files_and_folders if f.get('mimeType') != 'application/vnd.google-apps.folder']
                    subfolders = [f for f in files_and_folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                    all_files.extend(files)
                    all_subfolders.extend(subfolders)

                    logger.debug("Only files: %s", all_files)
                    logger.debug("Subfolders: %s", all_subfolders)

                    if not page_token:
                        break

                # Cache both subfolders and files for future use
                self.drive_cache.cache_subfolders(parent_folder_id, all_subfolders)
                self.drive_cache.cache_files(parent_folder_id, recursive=False, files=all_files)

            # Get subfolders and recursively scan them
            for subfolder in all_subfolders:
                subfolder_files = await self.get_files_recursive(subfolder['id'], visited_folders=visited_folders.copy())
                all_files.extend(subfolder_files)

        except Exception as e:
            st.warning(f"Error scanning folder {parent_folder_id}: {e}")

        return all_files

    def get_file_info(self, file:dict) -> dict:
        file_id = file['id']
        return self.get_file_detail(file_id)

    def get_file_detail(self, file_id: str) -> dict:
        """Retrieve file info from Google Drive by file ID"""
        if not self.service:
            logger.error("Google Drive service is not initialized.")
            return {}

        try:
            # Try to get from cache first
            cached_info = self.drive_cache.get_cached_file_details(file_id)
            if cached_info:
                file = get_enriched_file_info(cached_info)
            else:
                # Not in cache, fetch from API
                file = self.service.files().get(fileId=file_id, fields='*').execute()
                # Cache the result
                self.drive_cache.cache_file_details(file)
            return get_enriched_file_info(file)
        except Exception as e:
            logger.error("Failed to retrieve file info: %s", e)
            return {}

    def get_folder_info(self, folder_id: str) -> dict:
        return self.get_folder_detail(folder_id)

    def get_folder_detail(self, folder_id: str) -> dict:
        return self.get_file_info({'id':folder_id})

    def get_folder_id_from_path(self, folder_path: str):
        folder_path = folder_path.strip().strip('/')

        try:
            return self.folder_path_to_id[folder_path]
        except KeyError:
            pass

        parent_id = 'root'  # Start from "My Drive"
        if folder_path in ('My Drive', 'root'):
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
            results = self.get_file_service().list(q=query, spaces='drive', fields="files(id, name)").execute()
            items = results.get('files', [])
            if not items:
                raise FileNotFoundError(f"Folder '{part}' not found in path.")

            parent_id = items[0]['id']  # Go one level deeper

            # Build up the current path as we go
            current_path = f"{current_path}/{part}"

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
                if not hit_cached_path_parts:  # Only store the first cached path we find
                    hit_cached_path_parts = cached_path.split('/')
            except KeyError:
                # No cached path found, continue building the path
                file = self.get_folder_info(current_id)
                ids_to_cache.append((current_id, file['name']))
                path_parts.append(file['name'])

                try:
                    current_id = file['parents'][0]
                except (KeyError, IndexError):
                    break  # Reached root

            if not current_id:  # Stop if we've reached the root
                break

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

        # Also cache the final path for the requested folder_id
        self.folder_id_to_path[folder_id] = full_path

        return full_path

    def get_file_media(self, file_id: str, is_thumbnail: bool = False) -> Union[bytes, None]:
        """
        Get media content for a file, either from cache or by downloading.

        Args:
            file_id: The ID of the Google Drive file
            is_thumbnail: If True, fetch/cache thumbnail instead of full media

        Returns:
            tuple: (media_type, media_content)
        """
        cache_id = f"{file_id}_thumb" if is_thumbnail else file_id
        logger.debug("Cache hit for media %s", file_id)

        # First check the cache
        media_content = self.drive_cache.get_cached_media(cache_id)

        if media_content is not None:
            logger.debug("Media content found in cache for file %s", file_id)
            logger.debug("media_content: %s", media_content[:100])  # Log first 100 bytes
            return media_content

        try:
            logger.debug("Not found in cache, fetching from Google Drive")
            media_type: Union[str, None] = None
            if is_thumbnail:
                # Try to get thumbnail from Google Drive's thumbnail API
                thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w250"
                response = requests.head(thumbnail_url, timeout=10)

                if response.status_code == 200:
                    # media_type = response.headers.get('content-type', 'image/*')
                    media_content = response.content
                    return media_content
            # Get full media content
            media_content = self.service.files().get_media(fileId=file_id).execute()

            # Cache the media content
            self.drive_cache.cache_media(
                file_id=cache_id,
                media_type=media_type,
                media_content=media_content
            )

            return media_content

        except Exception as e:
            logger.error(f"Failed to get {'thumbnail' if is_thumbnail else 'media'} for file {file_id}: {e}")
            return None


def extract_file_id_and_name(file: dict) -> tuple[str, str]:
    """Extract file ID and name from Google Drive file dictionary"""
    return str(file.get('id')), str(file.get('name', 'Unknown'))


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
