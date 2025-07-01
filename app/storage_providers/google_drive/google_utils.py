import streamlit as st

from app.storage_providers.google_drive.provider import logger
from app.utils import format_iso_timestamp, human_readable_size, get_file_extension

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
                'application/vnd.google-apps.folder',
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
