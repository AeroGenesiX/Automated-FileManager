import sys
from PyQt6.QtWidgets import QApplication # QApplication import first
import qdarkstyle # Import the dark theme library
# Import your other modules after QApplication is potentially configured
from .core.app_logger import setup_logger
from .app_window import MainWindow

def main():
    app = QApplication(sys.argv) # 1. Create App

    # 2. Set Org/App Names IMMEDIATELY
    app.setOrganizationName("MyOrg") 
    app.setApplicationName("AutomatedFileManager")

    # 3. Setup Logger (now it can correctly get names)
    logger = setup_logger() 
    logger.info("========================================")
    logger.info(f"Application '{app.applicationName()}' by '{app.organizationName()}' starting...")
    logger.info(f"Version: {app.applicationVersion() if app.applicationVersion() else 'N/A'}") # You can set app version too

    # Apply the dark stylesheet
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    try:
        # 4. Create and show your main window.
        window = MainWindow()  # MainWindow's __init__ might also set these if not done here,
                               # but setting in main.py is more robust for early service init.
        window.show()

        # --- Global LLM thread cleanup on exit ---
        def cleanup_llm_threads():
            # If the window has a thread, ensure it's stopped before app quits
            if hasattr(window, 'llm_thread') and window.llm_thread is not None:
                if window.llm_thread.isRunning():
                    if hasattr(window, 'llm_worker') and window.llm_worker is not None:
                        window.llm_worker.stop()
                    window.llm_thread.quit()
                    finished = window.llm_thread.wait(3000)
                    if not finished:
                        logger.warning("LLM thread did not finish in time, terminating forcefully.")
                        window.llm_thread.terminate()
                        window.llm_thread.wait(1000)
                window.llm_thread = None
            if hasattr(window, 'llm_worker') and window.llm_worker is not None:
                window.llm_worker.deleteLater()
                window.llm_worker = None
        app.aboutToQuit.connect(cleanup_llm_threads)
        # --- End global cleanup ---

        # 5. Start the Qt event loop.
        exit_code = app.exec()
        logger.info(f"Application exited with code {exit_code}.")
        return exit_code
    except Exception as e:
        # Catch any unhandled exceptions during app initialization or runtime
        # that weren't caught elsewhere.
        logger.critical(f"Unhandled critical exception at top level: {e}", exc_info=True)
        # Consider showing a user-friendly critical error dialog here before exiting
        # from PyQt6.QtWidgets import QMessageBox
        # QMessageBox.critical(None, "Critical Application Error", f"A critical error occurred and the application must close:\n{e}")
        return 1 # Indicate an error exit status

if __name__ == '__main__':
    # This ensures that if the script is run directly, main() is executed.
    # sys.exit() passes the return code of main() to the operating system.
    sys.exit(main())