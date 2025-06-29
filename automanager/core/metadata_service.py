import sqlite3
import os
import logging
from PyQt6.QtCore import QStandardPaths, QCoreApplication

logger = logging.getLogger("automgr.core.metadata_service")

class MetadataService:
    DB_NAME = "metadata.sqlite3"

    def __init__(self):
        org_name = QCoreApplication.organizationName()
        app_name = QCoreApplication.applicationName()

        if not org_name:
            logger.critical("OrganizationName not set on QApplication. Metadata path will use 'MyOrg_Fallback'.")
            org_name = "MyOrg_Fallback"
        if not app_name:
            logger.critical("ApplicationName not set on QApplication. Metadata path will use 'AutomatedFileManager_Fallback'.")
            app_name = "AutomatedFileManager_Fallback"

        base_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        
        if not base_data_path:
            logger.error("Could not determine AppLocalDataLocation. Using current directory as fallback for database.")
            base_data_path = "." 

        # Construct the full application-specific data directory path: base_path/OrgName/AppName
        self.app_specific_data_path = os.path.join(base_data_path, org_name, app_name)
        
        # This was the crucial part - ensure it matches the logger's app_data_dir construction.
        # If QStandardPaths.AppLocalDataLocation already includes org/app, then the above will duplicate.
        # However, with app.setOrganizationName called *before* this, QStandardPaths *should* give the base.

        if not os.path.exists(self.app_specific_data_path):
            try:
                os.makedirs(self.app_specific_data_path, exist_ok=True)
                logger.info(f"Created application data directory for database: {self.app_specific_data_path}")
            except OSError as e:
                logger.error(f"Error creating data directory '{self.app_specific_data_path}' for database: {e}. Using current directory as fallback.")
                self.app_specific_data_path = "."

        self.db_path = os.path.join(self.app_specific_data_path, self.DB_NAME)
        logger.info(f"MetadataService: Database path set to: {self.db_path}")
        
        self._conn = None
        try:
            self._ensure_db_and_table()
            logger.info("MetadataService initialized successfully and database table ensured.")
        except sqlite3.Error as e:
            logger.critical(f"FATAL: Failed to initialize metadata database at '{self.db_path}': {e}", exc_info=True)
            self._conn = None
    # ... rest of MetadataService ( _get_connection, _ensure_db_and_table, etc. remain the same)
    def _get_connection(self) -> sqlite3.Connection | None:
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(self.db_path, timeout=10) 
                self._conn.row_factory = sqlite3.Row 
                self._conn.execute("PRAGMA journal_mode=WAL;")
                logger.debug("New SQLite connection established.")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database '{self.db_path}': {e}", exc_info=True)
                self._conn = None
        return self._conn

    def _ensure_db_and_table(self):
        conn = self._get_connection()
        if not conn:
            logger.error("Cannot ensure DB table: No database connection.")
            raise sqlite3.OperationalError("Database connection not available for table creation.")

        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_metadata (
                    file_path TEXT PRIMARY KEY,
                    tags TEXT, 
                    notes TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            logger.debug("Database table 'file_metadata' schema ensured.")
        except sqlite3.Error as e:
            logger.error(f"Error ensuring 'file_metadata' table schema: {e}", exc_info=True)
            conn.rollback()
            raise

    def get_metadata(self, file_path: str) -> dict | None:
        abs_path = os.path.abspath(file_path)
        try:
            conn = self._get_connection()
            if not conn: return None

            cursor = conn.cursor()
            cursor.execute("SELECT tags, notes FROM file_metadata WHERE file_path = ?", (abs_path,))
            row = cursor.fetchone()
            if row:
                tags_list = row['tags'].split(',') if row['tags'] else []
                return {'tags': tags_list, 'notes': row['notes']}
            return None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving metadata for '{abs_path}': {e}", exc_info=True)
            return None

    def save_metadata(self, file_path: str, tags: list[str] | None = None, note_text: str | None = None):
        abs_path = os.path.abspath(file_path)
        try:
            conn = self._get_connection()
            if not conn: return

            cursor = conn.cursor()
            existing_meta = self.get_metadata(abs_path)

            if existing_meta is None: # New entry
                tags_to_save_str = ",".join(tag.strip() for tag in tags if tag.strip()) if tags is not None else ""
                note_to_save = note_text if note_text is not None else ""
                
                cursor.execute('''
                    INSERT INTO file_metadata (file_path, tags, notes, last_updated) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (abs_path, tags_to_save_str, note_to_save))
                logger.info(f"Inserted new metadata for '{abs_path}'.")
            else: # Existing entry
                update_clauses = []
                params = []

                current_tags_str = ",".join(existing_meta.get('tags', []))
                current_notes = existing_meta.get('notes', '')

                if tags is not None:
                    new_tags_str = ",".join(tag.strip() for tag in tags if tag.strip())
                    if new_tags_str != current_tags_str:
                        update_clauses.append("tags = ?")
                        params.append(new_tags_str)
                
                if note_text is not None:
                    if note_text != current_notes:
                        update_clauses.append("notes = ?")
                        params.append(note_text)
                
                if not update_clauses:
                    logger.debug(f"No metadata values changed for '{abs_path}'. Update skipped.")
                    return

                update_clauses.append("last_updated = CURRENT_TIMESTAMP")
                sql = f"UPDATE file_metadata SET {', '.join(update_clauses)} WHERE file_path = ?"
                params.append(abs_path)
                
                cursor.execute(sql, tuple(params))
                logger.info(f"Updated metadata for '{abs_path}'. Changed fields: {[c.split(' = ')[0] for c in update_clauses if 'CURRENT_TIMESTAMP' not in c]}.")
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving metadata for '{abs_path}': {e}", exc_info=True)
            if self._conn: self._conn.rollback()

    def close(self):
        if self._conn:
            try:
                self._conn.close()
                logger.info("Metadata database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing metadata database connection: {e}", exc_info=True)
            finally:
                self._conn = None