"""Cache manager for Google Drive files."""
import sqlite3
import json
import time
from pathlib import Path
import logging
from typing import Union

logger = logging.getLogger(__name__)

class DriveCache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "gdrive_cache.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Table for file contents cache
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    folder_id TEXT,
                    is_recursive INTEGER,
                    files_data TEXT,
                    timestamp INTEGER,
                    PRIMARY KEY (folder_id, is_recursive)
                )
            """)

            # Table for subfolder relationships with JSON storage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS folder_cache (
                    parent_id TEXT PRIMARY KEY,
                    sub_folders TEXT,  -- Stores subfolders data as JSON
                    timestamp INTEGER
                )
            """)

            # Table for individual file details with JSON metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_details (
                    file_id TEXT PRIMARY KEY,
                    meta_data TEXT NOT NULL,  -- Stores all file metadata as JSON
                    timestamp INTEGER,
                    FOREIGN KEY (file_id) REFERENCES file_cache(folder_id)
                )
            """)

            # Table for media storage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media_storage (
                    file_id TEXT PRIMARY KEY,
                    media_type TEXT,  -- MIME type of the media (nullable)
                    media_blob BLOB NOT NULL,  -- The actual media content
                    timestamp INTEGER,
                    FOREIGN KEY (file_id) REFERENCES file_details(file_id)
                )
            """)

    def get_cached_files(self, folder_id: str, recursive: bool, max_age_hours: int = 24):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT files_data, timestamp FROM file_cache
                WHERE folder_id = ? AND is_recursive = ?
                """,
                (folder_id, int(recursive))
            )
            result = cursor.fetchone()

            if result:
                files_data, timestamp = result
                age_hours = (time.time() - timestamp) / 3600

                if age_hours < max_age_hours:
                    logger.debug(f"Cache hit for folder {folder_id}")
                    return json.loads(files_data)

        return None

    def cache_files(self, folder_id: str, recursive: bool, files: list):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_cache (folder_id, is_recursive, files_data, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (folder_id, int(recursive), json.dumps(files), int(time.time()))
            )

    def get_cached_subfolders(self, parent_id: str, max_age_hours: int = 24):
        """Get cached subfolders for a parent folder if available and not expired"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT sub_folders, timestamp
                FROM folder_cache
                WHERE parent_id = ?
                """,
                (parent_id,)
            )
            result = cursor.fetchone()
            logger.debug("result of cached subfolders query: %s", result)

            if result:
                logger.debug("Found cached subfolders for parent ID: %s", parent_id)
                sub_folders, timestamp = result
                age_hours = (time.time() - timestamp) / 3600

                if age_hours < max_age_hours:
                    logger.debug(f"Cache hit for subfolders of {parent_id}")
                    return json.loads(sub_folders)
                else:
                    # Clean up expired entry
                    conn.execute(
                        "DELETE FROM folder_cache WHERE parent_id = ?",
                        (parent_id,)
                    )

        return None

    def cache_subfolders(self, parent_id: str, subfolders: list):
        """Cache subfolder information for a parent folder"""
        logger.debug(f"Caching subfolders for parent ID: {parent_id}")
        current_time = int(time.time())
        # Filter only folder items and prepare them for storage
        folder_data = [
            {
                'id': folder['id'],
                'name': folder['name'],
                'mimeType': folder['mimeType']
            }
            for folder in subfolders
            if folder.get('mimeType') == 'application/vnd.google-apps.folder'
        ]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO folder_cache
                (parent_id, sub_folders, timestamp)
                VALUES (?, ?, ?)
                """,
                (parent_id, json.dumps(folder_data), current_time)
            )

    def get_cached_file_details(self, file_id: str, max_age_hours: int = 24) -> Union[dict, None]:
        """Get cached details for a specific file if available and not expired"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT meta_data, timestamp
                FROM file_details
                WHERE file_id = ?
                """,
                (file_id,)
            )
            result = cursor.fetchone()

            if result:
                meta_data, timestamp = result
                age_hours = (time.time() - timestamp) / 3600

                if age_hours < max_age_hours:
                    logger.debug(f"Cache hit for file {file_id}")
                    return json.loads(meta_data)
                else:
                    # Clean up expired entry
                    conn.execute("DELETE FROM file_details WHERE file_id = ?", (file_id,))
                    conn.execute("DELETE FROM media_storage WHERE file_id = ?", (file_id,))

        return None

    def cache_file_details(self, file_info: dict):
        """Cache details for a single file"""
        if file_info.get('mimeType') != 'application/vnd.google-apps.folder':
            logger.debug("Caching file details for folder: %s",file_info['id'])
            logger.debug("folder name: %s", file_info.get('name', 'Unknown'))
        current_time = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_details (
                    file_id, meta_data, timestamp
                ) VALUES (?, ?, ?)
                """,
                (
                    file_info['id'],
                    json.dumps(file_info),
                    current_time
                )
            )

    def get_cached_media(self, file_id: str, max_age_hours: int = 24) -> Union[bytes, None]:
        """Get cached media content for a specific file if available and not expired"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT media_type, media_blob, timestamp
                FROM media_storage
                WHERE file_id = ?
                """,
                (file_id,)
            )
            result = cursor.fetchone()

            if result:
                media_type, media_blob, timestamp = result
                age_hours = (time.time() - timestamp) / 3600

                if age_hours < max_age_hours:
                    logger.debug(f"Cache hit for media {file_id}")
                    return media_blob
                else:
                    # Clean up expired entry
                    conn.execute("DELETE FROM media_storage WHERE file_id = ?", (file_id,))

        return None

    def cache_media(self, file_id: str, media_type: str | None, media_content: bytes):
        """
        Cache media content for a file

        Args:
            file_id: The ID of the file
            media_type: The MIME type of the media (can be None)
            media_content: The actual media content as bytes
        """
        current_time = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO media_storage (
                    file_id, media_type, media_blob, timestamp
                ) VALUES (?, ?, ?, ?)
                """,
                (file_id, media_type, media_content, current_time)
            )
