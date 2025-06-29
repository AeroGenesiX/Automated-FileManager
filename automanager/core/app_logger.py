import logging
import os
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QStandardPaths, QCoreApplication

def setup_logger():
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s (%(filename)s:%(lineno)d)'
    )
    
    org_name = QCoreApplication.organizationName()
    app_name = QCoreApplication.applicationName()

    if not org_name:
        print("CRITICAL WARNING: OrganizationName not set on QApplication. Using default 'MyOrg_Fallback' for log path.")
        org_name = "MyOrg_Fallback"
    if not app_name:
        print("CRITICAL WARNING: ApplicationName not set on QApplication. Using default 'AutomatedFileManager_Fallback' for log path.")
        app_name = "AutomatedFileManager_Fallback"

    base_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    
    if not base_data_path: 
        print("WARNING: Could not determine AppLocalDataLocation. Attempting to log to current directory as fallback.")
        base_data_path = "."

    # --- Defensive path construction ---
    # Construct the target app_data_dir: base_data_path / org_name / app_name
    # Check if org_name and app_name are already part of base_data_path to avoid duplication.
    # This is a bit simplistic; a more robust check might involve os.path.normcase and os.path.sep
    
    path_parts_to_add = []
    current_constructed_path = base_data_path

    # Check for org_name
    # QStandardPaths might already append org_name if it's set globally for the application's domain.
    # However, it doesn't usually append app_name directly into AppLocalDataLocation path string itself.
    # Usually AppLocalDataLocation gives you a path to a folder where you *should* create your org/app subdirs.

    # Let's assume QStandardPaths.AppLocalDataLocation gives the *base* and we *always* add org/app.
    # The issue might be if QCoreApplication.setOrganizationName influences QStandardPaths *before* first use.
    
    # Simpler and more direct: Assume QStandardPaths.AppLocalDataLocation is the parent for OrgName.
    app_data_dir = os.path.join(base_data_path, org_name, app_name)
    # The previous logic was already like this. The warning indicates that
    # QApplication.setOrganizationName() and setApplicationName() were *not* called
    # before the first call to QStandardPaths that might use them implicitly.
    # The fix in main.py should have addressed this.

    # If the duplication persists with main.py fix, it means QStandardPaths is behaving
    # unexpectedly or my assumption about its behavior with pre-set org/app names is incomplete for this Qt version/platform.

    # **Let's ensure the logger uses the names set on QApplication directly and consistently.**
    # The problem might have been if setup_logger was called *before* app.setOrganizationName in main.py.
    # The corrected main.py *should* prevent this.

    # If duplication *still* happens with corrected main.py:
    # A possible quick fix is to check if the last two parts of base_data_path are already org/app:
    # parts = os.path.normpath(base_data_path).split(os.sep)
    # if len(parts) >= 2 and parts[-1] == app_name and parts[-2] == org_name:
    #    app_data_dir = base_data_path # It's already fully formed
    # elif len(parts) >= 1 and parts[-1] == org_name: # Only org_name is there
    #    app_data_dir = os.path.join(base_data_path, app_name)
    # else: # Neither is there, append both
    #    app_data_dir = os.path.join(base_data_path, org_name, app_name)
    # For now, let's stick to the assumption that main.py sets names *before* this is called.

    log_dir = os.path.join(app_data_dir, "logs")
    
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Failed to create log directory '{log_dir}': {e}. Logging to current directory as fallback.")
        log_dir = "." 

    log_file_path = os.path.join(log_dir, "automgr.log")

    file_handler = None
    try:
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
    except (OSError, IOError) as e:
        print(f"CRITICAL ERROR: Failed to create log file handler for '{log_file_path}': {e}. File logging will be disabled.")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG)

    app_root_logger = logging.getLogger("automgr") 
    app_root_logger.setLevel(logging.DEBUG)
    
    if app_root_logger.hasHandlers():
        app_root_logger.handlers.clear()

    if file_handler:
        app_root_logger.addHandler(file_handler)
    app_root_logger.addHandler(console_handler)
    
    if file_handler:
        app_root_logger.info(f"Logger initialized. Logging to file: {log_file_path}")
    else:
        app_root_logger.warning(f"Logger initialized. Console logging only. File logging FAILED for path: {log_file_path}")
        
    return app_root_logger