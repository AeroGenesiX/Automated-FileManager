import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread # QThread is not directly used here but good to remember context

logger = logging.getLogger("automgr.core.llm_worker")

class LLMWorker(QObject):
    """
    A QObject-based worker that performs LLM processing in a separate thread.
    Emits signals for success (finished) or failure (error).
    """
    finished = pyqtSignal(str)  # Emits the LLM response string on success
    error = pyqtSignal(str)     # Emits an error message string on failure

    def __init__(self, llm_service, command_text: str, current_dir: str, selected_files: list):
        """
        Args:
            llm_service: An instance of the LLMService.
            command_text (str): The natural language command from the user.
            current_dir (str): The current directory in the file browser.
            selected_files (list): A list of paths to currently selected files/folders.
        """
        super().__init__()
        self.llm_service = llm_service
        self.command_text = command_text
        self.current_dir = current_dir
        self.selected_files = selected_files
        self._is_running = True # Internal flag to allow premature stopping
        logger.debug(f"LLMWorker initialized for command: '{self.command_text[:50]}...'")

    def run(self):
        """
        This method is executed when the QThread (that this worker is moved to) starts.
        It calls the LLM service and emits appropriate signals.
        """
        if not self._is_running:
            logger.info("LLMWorker.run() called, but worker was already stopped. Aborting.")
            return 
        
        logger.info(f"LLMWorker starting to process command: '{self.command_text[:50]}...'")
        try:
            response = self.llm_service.process_command(
                self.command_text,
                self.current_dir,
                self.selected_files
            )
            # Critical check: Ensure the worker hasn't been stopped while the LLM was processing
            if self._is_running:
                logger.info(f"LLMWorker finished processing. Emitting 'finished' signal.")
                self.finished.emit(response)
            else:
                logger.info("LLMWorker finished processing, but was stopped before emitting. Response discarded.")

        except Exception as e:
            # This catch-all is a safety net. LLMService.process_command should ideally
            # handle its own specific exceptions and return error strings.
            logger.critical(f"Unhandled exception in LLMWorker.run() during llm_service.process_command: {e}", exc_info=True)
            if self._is_running:
                self.error.emit(f"Critical Worker Error: {e}")
        finally:
            # Ensure _is_running is set to False, regardless of how run exits
            # This helps in cleanup and state management.
            self._is_running = False 
            logger.debug("LLMWorker.run() completed.")


    def stop(self):
        """
        Public method to signal the worker that it should stop its operation if possible.
        Useful if the thread needs to be quit prematurely (e.g., application closing).
        """
        logger.info("LLMWorker stop requested.")
        self._is_running = False