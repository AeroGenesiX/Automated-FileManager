"""
File operations for the Simple File Explorer.
"""

import os
import shutil
import logging
from PyQt6.QtCore import QObject, pyqtSignal

class FileOperations(QObject):
    """Handles file system operations with signal emissions."""
    
    # Define signals
    operation_completed = pyqtSignal(bool, str)  # Success flag, message
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def create_directory(self, path):
        """Create a new directory."""
        try:
            os.makedirs(path, exist_ok=True)
            self.operation_completed.emit(True, f"Created directory: {os.path.basename(path)}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {str(e)}")
            self.operation_completed.emit(False, f"Failed to create directory: {str(e)}")
            return False
    
    def delete_item(self, path):
        """Delete a file or directory."""
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                self.operation_completed.emit(True, f"Deleted directory: {os.path.basename(path)}")
            else:
                os.remove(path)
                self.operation_completed.emit(True, f"Deleted file: {os.path.basename(path)}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting {path}: {str(e)}")
            self.operation_completed.emit(False, f"Failed to delete: {str(e)}")
            return False
    
    def rename_item(self, old_path, new_path):
        """Rename a file or directory."""
        try:
            os.rename(old_path, new_path)
            self.operation_completed.emit(True, f"Renamed to: {os.path.basename(new_path)}")
            return True
        except Exception as e:
            self.logger.error(f"Error renaming {old_path} to {new_path}: {str(e)}")
            self.operation_completed.emit(False, f"Failed to rename: {str(e)}")
            return False
    
    def copy_item(self, source, destination):
        """Copy a file or directory."""
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
                self.operation_completed.emit(True, f"Copied directory to: {os.path.basename(destination)}")
            else:
                shutil.copy2(source, destination)
                self.operation_completed.emit(True, f"Copied file to: {os.path.basename(destination)}")
            return True
        except Exception as e:
            self.logger.error(f"Error copying {source} to {destination}: {str(e)}")
            self.operation_completed.emit(False, f"Failed to copy: {str(e)}")
            return False
    
    def move_item(self, source, destination):
        """Move a file or directory."""
        try:
            shutil.move(source, destination)
            self.operation_completed.emit(True, f"Moved to: {os.path.basename(destination)}")
            return True
        except Exception as e:
            self.logger.error(f"Error moving {source} to {destination}: {str(e)}")
            self.operation_completed.emit(False, f"Failed to move: {str(e)}")
            return False
