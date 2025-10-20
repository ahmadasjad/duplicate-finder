import os
import logging
import requests
import asyncio

from typing import Dict, Iterable, List, Optional, Union
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.utils import format_iso_timestamp, human_readable_size, get_file_extension
from app.config import GDRIVE_DEFAULT_MEDIA_CONCURRENCY

logger = logging.getLogger(__name__)

# credentials_file
CREDENTIALS_FILE = '.local/credentials.json'
TOKEN_FILE = '.local/token.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive',
    ]

class GoogleService():
    fresh_media_hit_count = 0
    # Default concurrency can be adjusted via environment variable GDRIVE_DEFAULT_MEDIA_CONCURRENCY
    _DEFAULT_MEDIA_CONCURRENCY = GDRIVE_DEFAULT_MEDIA_CONCURRENCY

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
        self.root_folder_id = None  # Will be set after service is built

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

    def _media_cache_key(self, file_id: str, is_thumbnail: bool) -> str:
        suffix = "_thumb" if is_thumbnail else ""
        return f"{file_id}{suffix}"

    def _get_cached_media(self, cache_key: str) -> Optional[bytes]:
        return self.drive_cache.get_cached_media(cache_key)

    def _cache_media(self, cache_key: str, media_type: Optional[str], media_content: bytes) -> None:
        self.drive_cache.cache_media(cache_key, media_type, media_content)

    def _download_file_media(self, file_id: str, is_thumbnail: bool) -> Optional[bytes]:
        if not self.service:
            logger.error("Google Drive service is not initialized.")
            return None

        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
        session = None

        try:
            # Create a new session for each download to prevent SSL context reuse
            session = requests.Session()

            # Try thumbnail URL first for thumbnails
            if is_thumbnail:
                try:
                    thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w250"
                    response = session.get(thumbnail_url, timeout=15, stream=True)
                    if response.status_code == 200:
                        # Check content length if available
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > MAX_FILE_SIZE:
                            logger.warning(f"File {file_id} too large: {content_length} bytes")
                            return None

                        # Read in chunks to avoid memory issues
                        chunks = []
                        total_size = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            total_size += len(chunk)
                            if total_size > MAX_FILE_SIZE:
                                logger.warning(f"File {file_id} exceeded size limit while streaming")
                                return None
                            chunks.append(chunk)

                        if chunks:
                            return b''.join(chunks)
                except (requests.Timeout, requests.RequestException) as e:
                    logger.debug("Failed to get thumbnail via URL, falling back to service: %s", e)
                finally:
                    if session:
                        session.close()

            # Use service.files().get_media() for both full media and thumbnail fallback
            try:
                # Check file size from cache first, then API if not available
                file_size = None
                cached_metadata = self.drive_cache.get_cached_file_details(file_id)

                if cached_metadata and 'size' in cached_metadata:
                    file_size = int(cached_metadata['size'])
                    logger.debug(f"Using cached size for file {file_id}: {file_size} bytes")
                else:
                    # Get file metadata from API to check size
                    file_metadata = self.service.files().get(fileId=file_id, fields="size,id,name,mimeType").execute()
                    if file_metadata:
                        # Cache the metadata for future use
                        self.drive_cache.cache_file_details(file_metadata)
                        if 'size' in file_metadata:
                            file_size = int(file_metadata['size'])

                if file_size and file_size > MAX_FILE_SIZE:
                    logger.warning(f"File {file_id} too large: {file_size} bytes")
                    return None

                # Download the file with size limit
                request = self.service.files().get_media(fileId=file_id)
                response = request.execute()

                if isinstance(response, bytes) and len(response) <= MAX_FILE_SIZE:
                    return response
                else:
                    logger.warning(f"File {file_id} response invalid or too large")
                    return None

            except Exception as e:
                logger.error(f"Service download failed for {file_id}: {str(e)}")
                return None

        except Exception as exc:
            logger.error(
                "Failed to get %s for file %s: %s",
                "thumbnail" if is_thumbnail else "media",
                file_id,
                exc
            )
            return None
        finally:
            # Ensure session is closed
            if session:
                session.close()

    def _fetch_and_cache_media(self, file_id: str, is_thumbnail: bool) -> Optional[bytes]:
        cache_key = self._media_cache_key(file_id, is_thumbnail)
        cached_media = self._get_cached_media(cache_key)
        if cached_media is not None:
            return cached_media

        media_content = self._download_file_media(file_id, is_thumbnail)
        if media_content is not None:
            self._cache_media(cache_key, None, media_content)
            type(self).fresh_media_hit_count += 1
            logger.debug("Total fresh media hits: %d", self.fresh_media_hit_count)
        return media_content

    async def prefetch_media(
        self,
        file_ids: Iterable[str],
        *,
        is_thumbnail: bool = False,
        concurrency: Optional[int] = None,
        progress_callback=None
    ) -> Dict[str, Optional[bytes]]:
        # Process one file at a time to prevent SSL/memory issues
        MAX_RETRIES = 3
        DELAY_BETWEEN_FILES = 0.02  # seconds

        unique_ids: List[str] = []
        seen = set()
        for raw_id in file_ids or []:
            if not raw_id:
                continue
            if raw_id in seen:
                continue
            seen.add(raw_id)
            unique_ids.append(raw_id)

        if not unique_ids:
            return {}

        results: Dict[str, Optional[bytes]] = {}
        uncached: List[str] = []

        # Check cache first
        for file_id in unique_ids:
            cache_key = self._media_cache_key(file_id, is_thumbnail)
            cached = self._get_cached_media(cache_key)
            if cached is not None:
                results[file_id] = cached
            else:
                uncached.append(file_id)

        if not uncached:
            return results

        # Process files one at a time
        total_files = len(uncached)
        completed = 0
        loop = asyncio.get_running_loop()

        # Process files sequentially to prevent memory/SSL issues
        for file_id in uncached:
            try:
                # Run file download in executor to prevent blocking
                media_content = await loop.run_in_executor(
                    None,
                    self._fetch_and_cache_media,
                    file_id,
                    is_thumbnail,
                )

                if media_content is not None:
                    results[file_id] = media_content
                else:
                    # Retry on failure
                    retries = 0
                    while retries < MAX_RETRIES and media_content is None:
                        logger.debug("Retrying fetch for file %s (attempt %d)", file_id, retries + 1)
                        await asyncio.sleep(1)  # Add delay between retries
                        media_content = await loop.run_in_executor(
                            None,
                            self._fetch_and_cache_media,
                            file_id,
                            is_thumbnail
                        )
                        retries += 1

                    results[file_id] = media_content
                    if media_content is None:
                        logger.debug("Failed to fetch media for file %s after %d retries", file_id, MAX_RETRIES)

            except Exception as exc:
                logger.warning(
                    "Error fetching %s for file %s: %s",
                    "thumbnail" if is_thumbnail else "media",
                    file_id,
                    exc
                )
                results[file_id] = None

            # Update progress
            completed += 1
            if progress_callback:
                progress_callback(completed / total_files, f"Fetched media {completed}/{total_files}")

            # Add delay between files to prevent overloading
            await asyncio.sleep(DELAY_BETWEEN_FILES)

            # Force garbage collection after each file
            import gc
            gc.collect()

        return results

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
                'application/vnd.google-apps.shortcut',
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
            return parent_id

        if folder_path.startswith('My Drive'):
            folder_path = folder_path[9:] # Delete "My Drive/" prefix
        parts = folder_path.split('/')

        current_path = parts[0] if parts else 'My Drive'
        self.folder_path_to_id[current_path] = parent_id
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

        return parent_id

    def get_root_folder_id(self):
        if self.root_folder_id:
            return self.root_folder_id

        import time
        time.sleep(1)  # Give some time for the service to initialize
        file = self.get_file_service().get(fileId='root', fields='id').execute()
        logger.debug("Root folder ID from API: %s", file)
        root_id = file['id']
        self.root_folder_id = root_id
        return root_id

    def is_root_folder_id(self, folder_id: str):
        """Check if the given folder ID is the root folder ID"""
        return folder_id == 'root' or folder_id == self.get_root_folder_id()

    def get_folder_name_from_id(self, folder_id: str) -> tuple[Union[str, None], Union[str, None]]:
        if self.is_root_folder_id(folder_id):
            return 'My Drive', None

        file = self.get_folder_info(folder_id)
        return file.get('name'), file.get('parents', [None])[0]

    def get_folder_path_from_id(self, folder_id):
        """Get folder path from Google Drive folder ID"""
        try:
            return self.folder_id_to_path[folder_id]
        except KeyError:
            pass

        if self.is_root_folder_id(folder_id):
            self.folder_id_to_path[folder_id] = 'My Drive' # for future hits
            return 'My Drive'

        folder_name, parent_id = self.get_folder_name_from_id(folder_id)
        full_path = self.get_folder_path_from_id(parent_id) + '/' + folder_name
        self.folder_id_to_path[folder_id] = full_path # for future hits
        return full_path

    def get_file_media(self, file_id: str, is_thumbnail: bool = False) -> Union[bytes, None]:
        """
        Get media content for a file, either from cache or by downloading.

        Args:
            file_id: The ID of the Google Drive file
            is_thumbnail: If True, fetch/cache thumbnail instead of full media
        """
        return self._fetch_and_cache_media(file_id, is_thumbnail)



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
