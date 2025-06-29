import sys
import logging
import json # For parsing FOUND_FILES_JSON
from PyQt6.QtWidgets import QMainWindow, QDockWidget, QApplication, QMessageBox, QStatusBar
from PyQt6.QtCore import Qt, QSize, QStandardPaths, QThread, QProcess, QTimer # Added QTimer
from PyQt6.QtGui import QCloseEvent, QIcon

from .ui.navigation_pane import NavigationPane
from .ui.file_browser_pane import FileBrowserPane
from .ui.preview_metadata_pane import PreviewMetadataPane
from .ui.llm_terminal_pane import LLMTerminalPane

from .core.file_operation_service import FileOperationService
from .core.metadata_service import MetadataService
from .core.security_service import SecurityService
from .core.llm_worker import LLMWorker

logger = logging.getLogger("automgr.app_window")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        if not QApplication.organizationName(): QApplication.setOrganizationName("MyOrg")
        if not QApplication.applicationName(): QApplication.setApplicationName("AutomatedFileManager")

        self.setWindowTitle("Automated FileManager")
        self.setGeometry(100, 100, 1500, 1000)

        self.llm_thread: QThread | None = None
        self.llm_worker: LLMWorker | None = None
        self.is_llm_processing: bool = False

        self._create_services()
        self._create_panes()
        self._setup_docks()
        self._setup_status_bar()
        self._connect_signals()

        initial_fb_path = self.file_browser_pane.current_path
        if hasattr(self.llm_terminal_pane, 'external_path_change_request'):
             self.llm_terminal_pane.external_path_change_request.emit(initial_fb_path)

        self.status_bar.showMessage("Ready.", 3000)
        logger.info("MainWindow initialized.")

    def _create_services(self):
        logger.debug("Creating services...")
        self.security_service = SecurityService()
        self.file_op_service = FileOperationService(security_srv=self.security_service)
        self.metadata_service = MetadataService()
        logger.debug("Services created.")

    def _create_panes(self):
        logger.debug("Creating UI panes...")
        self.navigation_pane = NavigationPane()
        self.file_browser_pane = FileBrowserPane(file_op_service=self.file_op_service)
        self.preview_metadata_pane = PreviewMetadataPane(metadata_service=self.metadata_service)
        self.llm_terminal_pane = LLMTerminalPane()
        logger.debug("UI panes created.")

    def _setup_docks(self):
        logger.debug("Setting up dock widgets...")
        nav_dock = QDockWidget("Navigation", self)
        nav_dock.setWidget(self.navigation_pane)
        nav_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, nav_dock)

        preview_dock = QDockWidget("Preview & Metadata", self)
        preview_dock.setWidget(self.preview_metadata_pane)
        preview_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, preview_dock)

        llm_dock = QDockWidget("LLM & Terminal", self)
        llm_dock.setWidget(self.llm_terminal_pane)
        llm_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, llm_dock)

        self.setCentralWidget(self.file_browser_pane)

        self.resizeDocks([nav_dock], [self.width() // 7], Qt.Orientation.Horizontal)
        self.resizeDocks([preview_dock], [self.width() // 3], Qt.Orientation.Horizontal)
        self.resizeDocks([llm_dock], [self.height() // 4], Qt.Orientation.Vertical)
        logger.debug("Dock widgets configured.")

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        logger.debug("Status bar created.")

    def _connect_signals(self):
        logger.debug("Connecting signals...")
        self.navigation_pane.path_selected.connect(self.file_browser_pane.set_current_path)

        self.file_browser_pane.path_changed_signal.connect(
            self.llm_terminal_pane.external_path_change_request
        )

        terminal_widget = self.llm_terminal_pane.get_terminal_widget()
        if terminal_widget:
            terminal_widget.internal_directory_changed.connect( # Connect terminal 'cd' to FB
                self.file_browser_pane.set_current_path
            )

        self.file_browser_pane.selection_changed_signal.connect(self.preview_metadata_pane.update_preview)
        self.file_browser_pane.status_message_signal.connect(self.status_bar.showMessage)

        llm_chat_widget = self.llm_terminal_pane.get_llm_chat_widget()
        if llm_chat_widget:
            llm_chat_widget.command_submitted.connect(self._initiate_llm_command)
            llm_chat_widget.execute_commands_requested.connect(
                terminal_widget.run_command_externally if terminal_widget else lambda: None
            )

        self.file_browser_pane.request_llm_command_signal.connect(self._handle_file_browser_llm_request)
        logger.debug("Signals connected.")

    def _initiate_llm_command(self, command_text: str):
        self._handle_llm_command_async(command_text)

    def _handle_file_browser_llm_request(self, command_text: str, context_paths: list[str]):
        logger.info(f"LLM command requested from File Browser: '{command_text[:50]}...', Context Paths: {len(context_paths)}")
        current_dir_for_llm = self.file_browser_pane.current_path
        self._handle_llm_command_async(command_text,
                                       cwd_override=current_dir_for_llm,
                                       selected_files_override=context_paths)

    def _handle_llm_command_async(self, command_text: str,
                                  cwd_override: str | None = None,
                                  selected_files_override: list[str] | None = None):
        logger.info(f"LLM command processing initiated: '{command_text[:100]}...'")

        if self.is_llm_processing:
            QMessageBox.warning(self, "LLM Busy", "LLM is already processing a request. Please wait.")
            logger.warning("LLM busy (is_llm_processing=True), new request ignored.")
            return

        self.is_llm_processing = True
        llm_chat_widget = self.llm_terminal_pane.get_llm_chat_widget()
        if llm_chat_widget:
            llm_chat_widget.set_processing_state(True)

        current_dir = cwd_override if cwd_override is not None else self.file_browser_pane.current_path
        selected_files = selected_files_override if selected_files_override is not None else self.file_browser_pane.get_selected_items_paths()

        llm_service_instance = self.llm_terminal_pane.get_llm_service()

        self.llm_thread = QThread(self)
        self.llm_worker = LLMWorker(llm_service_instance, command_text, current_dir, selected_files)
        self.llm_worker.moveToThread(self.llm_thread)

        self.llm_worker.finished.connect(self._handle_llm_response)
        self.llm_worker.error.connect(self._handle_llm_error)
        self.llm_thread.started.connect(self.llm_worker.run)
        self.llm_thread.finished.connect(self.llm_worker.deleteLater)
        self.llm_thread.finished.connect(self.llm_thread.deleteLater)
        self.llm_thread.finished.connect(self._clear_llm_thread_refs)

        logger.debug(f"Starting LLM worker thread for CWD: '{current_dir}', Selected: {len(selected_files)} items.")
        self.llm_thread.start()

    def _finalize_llm_processing(self):
        logger.debug("Finalizing LLM processing...")
        self.is_llm_processing = False

        # Only call deleteLater if the object still exists and is not already deleted
        if self.llm_thread:
            if self.llm_thread.isRunning():
                self.llm_thread.quit()
                if not self.llm_thread.wait(3000):
                    logger.warning("LLM thread did not quit gracefully (_finalize_llm_processing). Terminating.")
                    self.llm_thread.terminate()
                    self.llm_thread.wait(1000)
            # Defensive: Only call deleteLater if not already deleted
            if self.llm_worker and hasattr(self.llm_worker, 'deleteLater'):
                try:
                    self.llm_worker.deleteLater()
                except RuntimeError:
                    logger.warning("llm_worker.deleteLater() called on already deleted object.")
            if self.llm_thread and hasattr(self.llm_thread, 'deleteLater'):
                try:
                    self.llm_thread.deleteLater()
                except RuntimeError:
                    logger.warning("llm_thread.deleteLater() called on already deleted object.")

        self._clear_llm_thread_refs()

        llm_chat_widget = self.llm_terminal_pane.get_llm_chat_widget()
        if llm_chat_widget:
            llm_chat_widget.set_processing_state(False)

    def _handle_llm_response(self, response_text: str):
        logger.info(f"LLM response received (length: {len(response_text)}).")
        llm_chat_widget = self.llm_terminal_pane.get_llm_chat_widget()

        if llm_chat_widget:
            llm_chat_widget.add_message_to_history("LLM", response_text)

        found_files_prefix = "FOUND_FILES_JSON:"
        # Process multi-line responses carefully for the prefix
        response_lines = response_text.strip().split('\n')
        json_str_to_parse = None

        for line in response_lines:
            if line.strip().startswith(found_files_prefix):
                json_part = line.strip()[len(found_files_prefix):].strip()
                # Try to extract a valid JSON array part from this line
                start_index = json_part.find('[')
                end_index = json_part.rfind(']')
                if start_index != -1 and end_index != -1 and end_index > start_index:
                    json_str_to_parse = json_part[start_index : end_index+1]
                    break # Found a JSON array, process it

        if json_str_to_parse:
            try:
                found_paths = json.loads(json_str_to_parse)
                if isinstance(found_paths, list) and all(isinstance(p, str) for p in found_paths):
                    logger.info(f"LLM provided FOUND_FILES_JSON: {found_paths}")
                    QTimer.singleShot(100, lambda: self.file_browser_pane.select_files_by_paths(found_paths))
                    self.status_bar.showMessage(f"LLM found {len(found_paths)} files. Selecting...", 5000)
                else:
                    logger.warning(f"FOUND_FILES_JSON did not contain a valid list of strings: {json_str_to_parse}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse FOUND_FILES_JSON: {e}. JSON string: {json_str_to_parse}", exc_info=True)
            except Exception as e:
                logger.error(f"Error processing FOUND_FILES_JSON content: {e}", exc_info=True)
        else:
             self.status_bar.showMessage("LLM response processed.", 3000)

        self._finalize_llm_processing()

    def _handle_llm_error(self, error_message: str):
        logger.error(f"LLM processing error: {error_message}")
        llm_chat_widget = self.llm_terminal_pane.get_llm_chat_widget()
        if llm_chat_widget:
            llm_chat_widget.add_message_to_history("LLM Error", error_message)

        QMessageBox.critical(self, "LLM Processing Error", f"An error occurred with the LLM:\n{error_message}")
        self.status_bar.showMessage(f"LLM Error: {error_message[:50]}...", 5000)
        self._finalize_llm_processing()

    def _clear_llm_thread_refs(self):
        logger.debug("Clearing LLM thread and worker references explicitly.")
        self.llm_thread = None
        self.llm_worker = None

    def closeEvent(self, a0: QCloseEvent | None):
        logger.info("Close event triggered. Initiating application shutdown...")

        if self.is_llm_processing or (self.llm_thread and self.llm_thread.isRunning()):
            logger.warning("LLM processing seems active during close. Attempting to stop.")
            if self.llm_worker: self.llm_worker.stop()
            if self.llm_thread:
                self.llm_thread.quit()
                if not self.llm_thread.wait(3000):
                    logger.warning("LLM thread did not quit gracefully (closeEvent). Terminating.")
                    self.llm_thread.terminate()
                    self.llm_thread.wait(1000)
            self.is_llm_processing = False
            self._clear_llm_thread_refs()
            logger.debug("LLM thread forced stop during closeEvent.")

        if self.metadata_service:
            logger.debug("Closing metadata service...")
            self.metadata_service.close()

        terminal_widget = self.llm_terminal_pane.get_terminal_widget()
        if terminal_widget and terminal_widget.process and terminal_widget.process.state() != QProcess.ProcessState.NotRunning:
            logger.warning("Terminal process is running during close.")
            reply = QMessageBox.question(self, "Confirm Exit",
                                         "A terminal process is still running. Do you want to kill it and exit?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                logger.info("User confirmed: Killing terminal process.")
                terminal_widget.process.kill()
                terminal_widget.process.waitForFinished(1000)
            else:
                logger.info("Close cancelled by user due to running terminal process.")
                if a0: a0.ignore()
                return

        logger.info("Application shutdown sequence complete.")
        if a0: super().closeEvent(a0)
        else: super().closeEvent(QCloseEvent())

    def __del__(self):
        # Extra safety: ensure LLM thread is stopped if window is deleted
        if hasattr(self, 'llm_thread') and self.llm_thread is not None:
            if self.llm_thread.isRunning():
                if hasattr(self, 'llm_worker') and self.llm_worker is not None:
                    self.llm_worker.stop()
                self.llm_thread.quit()
                self.llm_thread.wait(3000)  # Wait up to 3 seconds
            self.llm_thread = None
        if hasattr(self, 'llm_worker') and self.llm_worker is not None:
            self.llm_worker.deleteLater()
            self.llm_worker = None
