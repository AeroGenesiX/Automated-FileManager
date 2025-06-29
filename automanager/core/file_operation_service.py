import os
import shutil
import logging
from .security_service import security_manager # Use the global instance or pass one

logger = logging.getLogger("automgr.core.file_op_service")

class FileOperationService:
    def __init__(self, security_srv=security_manager):
        self.security_service = security_srv
        self.clipboard = [] # Very basic internal clipboard {action: 'copy'/'cut', paths: []}
        logger.info("FileOperationService initialized.")

    def delete_items(self, paths: list[str], parent_widget=None) -> tuple[bool, str]:
        if not paths:
            return False, "No items selected for deletion."
        logger.info(f"Attempting to delete {len(paths)} items: {paths[:3]}...")

        confirm_msg = f"Are you sure you want to permanently delete these {len(paths)} item(s)?\n"
        for i, path_item in enumerate(paths):
            if i < 5: # Show first 5 items in confirmation
                confirm_msg += f"- {os.path.basename(path_item)}\n"
            else:
                confirm_msg += f"...and {len(paths) - 5} more."
                break
        
        if not self.security_service.request_confirmation("Confirm Deletion", confirm_msg, "", parent_widget):
            logger.info("Deletion cancelled by user.")
            return False, "Deletion cancelled by user."

        deleted_count = 0
        errors = []
        for path_item in paths:
            try:
                if os.path.isfile(path_item) or os.path.islink(path_item):
                    os.remove(path_item)
                    logger.debug(f"Deleted file: {path_item}")
                    deleted_count += 1
                elif os.path.isdir(path_item):
                    shutil.rmtree(path_item)
                    logger.debug(f"Deleted directory: {path_item}")
                    deleted_count += 1
                else:
                    logger.warning(f"Path is not a file or directory: {path_item}")
                    errors.append(f"Not a file/directory: {os.path.basename(path_item)}")
            except Exception as e:
                logger.error(f"Error deleting {path_item}: {e}", exc_info=True)
                errors.append(f"Error deleting {os.path.basename(path_item)}: {e}")
        
        msg = f"Successfully deleted {deleted_count} item(s)."
        if errors:
            msg += "\nErrors occurred:\n" + "\n".join(errors)
        
        logger.info(msg)
        return not errors, msg

    def rename_item(self, old_path: str, new_name: str, parent_widget=None) -> tuple[bool, str]:
        logger.info(f"Attempting to rename '{old_path}' to '{new_name}'")
        if not os.path.exists(old_path):
            logger.error(f"Rename failed: Source path does not exist: {old_path}")
            return False, f"Source path does not exist: {old_path}"
        if not new_name.strip():
            logger.error("Rename failed: New name cannot be empty.")
            return False, "New name cannot be empty."

        old_name_base = os.path.basename(old_path)
        if new_name == old_name_base:
            logger.info("Rename skipped: New name is same as old.")
            return True, "No change in name."

        dir_path = os.path.dirname(old_path)
        new_full_path = os.path.join(dir_path, new_name)

        if os.path.exists(new_full_path):
            logger.error(f"Rename failed: Item '{new_name}' already exists.")
            return False, f"An item named '{new_name}' already exists in this location."

        confirm_msg = f"Are you sure you want to rename '{old_name_base}' to '{new_name}'?"
        if not self.security_service.request_confirmation("Confirm Rename", confirm_msg, "", parent_widget):
            logger.info("Rename cancelled by user.")
            return False, "Rename cancelled by user."
        
        try:
            os.rename(old_path, new_full_path)
            logger.info(f"Renamed '{old_name_base}' to '{new_name}'.")
            return True, f"Renamed '{old_name_base}' to '{new_name}'."
        except Exception as e:
            logger.error(f"Error renaming '{old_path}' to '{new_full_path}': {e}", exc_info=True)
            return False, f"Error renaming: {e}"

    def create_file(self, parent_dir: str, file_name: str, parent_widget=None) -> tuple[bool, str]:
        logger.info(f"Attempting to create file '{file_name}' in '{parent_dir}'")
        if not os.path.isdir(parent_dir):
            logger.error(f"Create file failed: Parent directory does not exist: {parent_dir}")
            return False, f"Parent directory does not exist: {parent_dir}"
        if not file_name.strip():
            logger.error("Create file failed: File name cannot be empty.")
            return False, "File name cannot be empty."
        
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in file_name for char in invalid_chars):
            logger.error(f"Create file failed: File name '{file_name}' contains invalid characters.")
            return False, "The file name contains invalid characters."

        new_file_path = os.path.join(parent_dir, file_name)

        if os.path.exists(new_file_path):
            logger.error(f"Create file failed: Item '{file_name}' already exists.")
            return False, f"A file or folder named '{file_name}' already exists."
            
        try:
            with open(new_file_path, 'w') as f:
                pass 
            logger.info(f"File '{new_file_path}' created successfully.")
            return True, f"File '{file_name}' created successfully."
        except Exception as e:
            logger.error(f"Error creating file '{new_file_path}': {e}", exc_info=True)
            return False, f"Error creating file: {e}"

    def create_folder(self, parent_dir: str, folder_name: str, parent_widget=None) -> tuple[bool, str]:
        logger.info(f"Attempting to create folder '{folder_name}' in '{parent_dir}'")
        if not os.path.isdir(parent_dir):
            logger.error(f"Create folder failed: Parent directory does not exist: {parent_dir}")
            return False, f"Parent directory does not exist: {parent_dir}"
        if not folder_name.strip():
            logger.error("Create folder failed: Folder name cannot be empty.")
            return False, "Folder name cannot be empty."
        
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in folder_name for char in invalid_chars):
            logger.error(f"Create folder failed: Folder name '{folder_name}' contains invalid characters.")
            return False, "The folder name contains invalid characters."

        new_folder_path = os.path.join(parent_dir, folder_name)

        if os.path.exists(new_folder_path):
            logger.error(f"Create folder failed: Item '{folder_name}' already exists.")
            return False, f"A file or folder named '{folder_name}' already exists."
        
        try:
            os.makedirs(new_folder_path)
            logger.info(f"Folder '{new_folder_path}' created successfully.")
            return True, f"Folder '{folder_name}' created."
        except Exception as e:
            logger.error(f"Error creating folder '{new_folder_path}': {e}", exc_info=True)
            return False, f"Error creating folder: {e}"

    def copy_to_clipboard(self, paths: list[str]):
        if paths:
            self.clipboard = {'action': 'copy', 'paths': paths}
            logger.info(f"Copied {len(paths)} items to clipboard: {paths[:3]}...")
        else:
            self.clipboard = []

    def cut_to_clipboard(self, paths: list[str]):
        if paths:
            self.clipboard = {'action': 'cut', 'paths': paths}
            logger.info(f"Cut {len(paths)} items to clipboard: {paths[:3]}...")
        else:
            self.clipboard = []
    
    def get_clipboard_status(self) -> dict:
        return {'can_paste': bool(self.clipboard)}

    def paste_from_clipboard(self, destination_dir: str, parent_widget=None) -> tuple[bool, str]:
        if not self.clipboard:
            return False, "Clipboard is empty."
        if not os.path.isdir(destination_dir):
            return False, f"Destination is not a valid directory: {destination_dir}"

        action = self.clipboard.get('action')
        source_paths = self.clipboard.get('paths', [])
        logger.info(f"Pasting {len(source_paths)} items ({action}) to '{destination_dir}'")

        if not source_paths:
            return False, "No source paths in clipboard."

        success_count = 0
        errors = []

        for src_path in source_paths:
            if not os.path.exists(src_path):
                errors.append(f"Source item no longer exists: {os.path.basename(src_path)}")
                logger.warning(f"Paste source missing: {src_path}")
                continue

            base_name = os.path.basename(src_path)
            dst_path = os.path.join(destination_dir, base_name)

            # Handle name collisions (simple overwrite confirmation, could be more advanced)
            if os.path.exists(dst_path):
                if not self.security_service.request_confirmation(
                    "Confirm Overwrite",
                    f"'{base_name}' already exists in the destination. Overwrite?",
                    "",  # informative_text as empty string or provide additional info if needed
                    parent_widget
                ):
                    errors.append(f"Skipped overwrite of {base_name}")
                    logger.info(f"Paste overwrite skipped for {base_name}")
                    continue
                else: # If confirmed, remove existing destination to allow overwrite by copy/move
                    try:
                        if os.path.isdir(dst_path): shutil.rmtree(dst_path)
                        else: os.remove(dst_path)
                    except Exception as e:
                        errors.append(f"Error removing existing '{base_name}' for overwrite: {e}")
                        logger.error(f"Paste overwrite removal error for '{dst_path}': {e}", exc_info=True)
                        continue


            try:
                if action == 'copy':
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path) # copy2 preserves metadata
                    logger.debug(f"Copied '{src_path}' to '{dst_path}'")
                elif action == 'cut':
                    shutil.move(src_path, dst_path)
                    logger.debug(f"Moved '{src_path}' to '{dst_path}'")
                success_count += 1
            except Exception as e:
                errors.append(f"Error {action}ing {base_name}: {e}")
                logger.error(f"Error {action}ing '{src_path}' to '{dst_path}': {e}", exc_info=True)

        if action == 'cut': # Clear clipboard after successful cut and paste
            if not errors or success_count > 0 : # Only clear if at least some operation might have happened
                self.clipboard = [] 
                logger.info("Clipboard cleared after cut operation.")
        
        msg = f"Successfully {action}ed {success_count} of {len(source_paths)} item(s)."
        if errors:
            msg += "\nErrors occurred:\n" + "\n".join(errors)
        
        logger.info(msg)
        return not errors or success_count > 0, msg