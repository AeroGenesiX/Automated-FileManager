import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListView, QMenu, QMessageBox,
                             QInputDialog, QApplication, QSizePolicy)
from PyQt6.QtGui import QFileSystemModel, QFontMetrics
from PyQt6.QtCore import (QDir, pyqtSignal, QModelIndex, Qt, QUrl, QMimeData,
                          QPoint, QSize, QItemSelection, QTimer, QItemSelectionModel) # Added QTimer
from PyQt6.QtGui import QDesktopServices, QIcon, QAction, QKeySequence

from .icon_provider import IconProvider # Import the new icon provider

logger = logging.getLogger("automgr.ui.file_browser")

class FileBrowserPane(QWidget):
    selection_changed_signal = pyqtSignal(list)
    path_changed_signal = pyqtSignal(str)
    status_message_signal = pyqtSignal(str)
    request_llm_command_signal = pyqtSignal(str, list)

    TARGET_ICON_SIZE = QSize(48, 48)
    GRID_CELL_WIDTH = 90

    def __init__(self, file_op_service=None, parent=None):
        super().__init__(parent)
        self.file_op_service = file_op_service
        self.current_path = QDir.homePath()
        logger.info(f"FileBrowserPane initialized for Icon View. Initial path: {self.current_path}")

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.model = QFileSystemModel(self)
        self.model.setIconProvider(IconProvider()) # Set the custom icon provider
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.Hidden | QDir.Filter.System | QDir.Filter.NoDotAndDotDot)

        self.list_view = QListView(self)
        self.list_view.setModel(self.model)
        self.list_view.setRootIndex(self.model.index(self.current_path))

        self.list_view.setViewMode(QListView.ViewMode.IconMode)
        self.list_view.setIconSize(self.TARGET_ICON_SIZE)

        # Calculate grid size after QApplication is created
        font_metrics = QFontMetrics(QApplication.font())
        text_margin_vertical = 2
        icon_text_spacing = 8
        max_filename_lines = 2
        grid_cell_height = (self.TARGET_ICON_SIZE.height() +
                            text_margin_vertical +
                            icon_text_spacing +
                            (font_metrics.height() * max_filename_lines) +
                            text_margin_vertical + 5)
        target_grid_size = QSize(self.GRID_CELL_WIDTH, int(grid_cell_height))
        self.list_view.setGridSize(target_grid_size)

        self.list_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_view.setMovement(QListView.Movement.Static)
        self.list_view.setFlow(QListView.Flow.LeftToRight)
        self.list_view.setWrapping(True)
        self.list_view.setUniformItemSizes(True)

        self.list_view.setDragEnabled(True)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDropIndicatorShown(True)

        layout.addWidget(self.list_view)

        selection_model = self.list_view.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_selection_changed)
        else:
            logger.error("QListView selection model not found.")

        self.list_view.doubleClicked.connect(self._on_double_clicked)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._open_context_menu)

        self._setup_standard_shortcuts()
        logger.debug("FileBrowserPane UI (Icon View) setup complete.")

    def select_files_by_paths(self, paths_to_select: list[str]):
        if not paths_to_select:
            if self.list_view.selection_model(): self.list_view.selection_model().clear()
            logger.debug("select_files_by_paths called with empty list, selection cleared.")
            return

        logger.info(f"Attempting to select {len(paths_to_select)} files by paths. First: {paths_to_select[0]}")

        first_file_dir = os.path.dirname(paths_to_select[0])
        # Normalize paths for comparison
        norm_first_file_dir = QDir.cleanPath(first_file_dir)
        norm_current_path = QDir.cleanPath(self.current_path)

        if norm_first_file_dir != norm_current_path:
            logger.info(f"Target directory '{norm_first_file_dir}' for selection is different from current '{norm_current_path}'. Navigating...")
            self.set_current_path(norm_first_file_dir) # This will change self.current_path
            # Use QTimer to defer selection until after path change and model update are processed
            QTimer.singleShot(100, lambda: self._perform_selection(paths_to_select))
            return # Selection will happen in _perform_selection

        self._perform_selection(paths_to_select) # If already in correct dir, select immediately

    def _perform_selection(self, paths_to_select: list[str]):
        """Internal method to actually perform the selection. Called after potential path change."""
        logger.debug(f"_perform_selection called for {len(paths_to_select)} paths in '{self.current_path}'.")
        selection_model = self.list_view.selectionModel()
        if not selection_model:
            logger.error("Cannot select files: No selection model found in _perform_selection.")
            return

        selection_model.clear()
        selection_flags = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
        successful_selections = 0
        first_selected_index = QModelIndex() # To scroll to

        for path_str in paths_to_select:
            # Only select if the file is directly in the current view's directory
            if QDir.cleanPath(os.path.dirname(path_str)) == QDir.cleanPath(self.current_path):
                file_name = os.path.basename(path_str)
                # QFileSystemModel.index() takes full path or path relative to its own root.
                # We are providing absolute path.
                index = self.model.index(path_str)

                if index.isValid():
                    # Check if the parent of this index in the model matches the view's root index path
                    # This ensures the item is indeed under the currently displayed folder.
                    # For files directly in self.current_path, index.parent() will be model.index(self.current_path)
                    # For folders, index.parent() is its parent. This check is a bit tricky.
                    # Simpler: if self.model.filePath(index) matches path_str, it's the right item.
                    if self.model.filePath(index) == path_str:
                        if not first_selected_index.isValid():
                            first_selected_index = index
                        selection_model.select(index, selection_flags)
                        successful_selections += 1
                        logger.debug(f"Selected file via path: {path_str}")
                    else:
                        logger.warning(f"Could not select '{file_name}'. Index found, but path mismatch or not directly in view. Model path: {self.model.filePath(index)}")
                else:
                    logger.warning(f"Could not select '{file_name}'. Invalid index returned by model for path: {path_str}")
            else:
                logger.warning(f"Cannot select '{os.path.basename(path_str)}': Not in current directory '{self.current_path}'.")

        if first_selected_index.isValid():
            self.list_view.scrollTo(first_selected_index, QListView.ScrollHint.EnsureVisible)

        if successful_selections > 0:
            msg = f"{successful_selections} file(s) programmatically selected."
            if successful_selections < len(paths_to_select):
                msg = f"Selected {successful_selections} of {len(paths_to_select)} files. Some might not be in the current view."
            self.status_message_signal.emit(msg)
        else:
            self.status_message_signal.emit("Could not select any of the specified files in the current view.")


    # ... (Rest of FileBrowserPane methods: _setup_standard_shortcuts, set_current_path,
    #      _on_selection_changed, get_selected_items_paths, _on_double_clicked,
    #      _open_context_menu, _send_to_llm..., _handle_... methods remain IDENTICAL
    #      to the version from the "optimized" response. Only __init__ and select_files_by_paths
    #      and _perform_selection are shown with significant changes here.)
    # --- Copy the rest from previous full FileBrowserPane version ---
    def _setup_standard_shortcuts(self):
        logger.debug("Setting up standard shortcuts.")
        shortcuts = [
            (QKeySequence.StandardKey.Delete, lambda: self._handle_delete(self.get_selected_items_paths())),
            (QKeySequence.StandardKey.Copy, lambda: self._handle_copy(self.get_selected_items_paths())),
            (QKeySequence.StandardKey.Cut, lambda: self._handle_cut(self.get_selected_items_paths())),
            (QKeySequence.StandardKey.Paste, lambda: self._handle_paste(self.current_path)),
        ]
        for key_seq, slot in shortcuts:
            action = QAction(self)
            action.setShortcut(QKeySequence(key_seq))
            action.triggered.connect(slot)
            self.addAction(action)
        logger.debug("Standard shortcuts set up.")

    def set_file_operation_service(self, service):
        self.file_op_service = service
        logger.debug(f"FileOperationService instance {'set' if service else 'cleared'}.")

    def set_current_path(self, path_str: str):
        logger.debug(f"Request to set current path to: '{path_str}' for Icon View")
        normalized_path = QDir.cleanPath(path_str)
        effective_path_str = normalized_path

        dir_to_set = QDir(normalized_path)
        if not dir_to_set.exists() or not dir_to_set.isReadable():
            logger.warning(f"Path '{normalized_path}' does not exist or is not readable.")
            original_path_basename = os.path.basename(normalized_path)
            parent_dir_q = QDir(normalized_path)
            while not (parent_dir_q.exists() and parent_dir_q.isReadable()):
                if not parent_dir_q.cdUp():
                    parent_dir_q.setPath(QDir.homePath())
                    break
            effective_path_str = parent_dir_q.absolutePath()
            self.status_message_signal.emit(f"Path Error: '{original_path_basename}' inaccessible. Switched to '{os.path.basename(effective_path_str)}'.")
            logger.info(f"Path switched to fallback: '{effective_path_str}'")

        if self.current_path != effective_path_str:
            self.current_path = effective_path_str
            new_root_index = self.model.index(self.current_path)
            if new_root_index.isValid():
                self.list_view.setRootIndex(new_root_index)
                self.path_changed_signal.emit(self.current_path)
                logger.info(f"FileBrowser (Icon View) current path set to: '{self.current_path}'")
                self.list_view.clearSelection()
            else:
                logger.error(f"Critical: Failed to set root index for validated path '{self.current_path}'. Reverting to home.")
                self.current_path = QDir.homePath()
                self.list_view.setRootIndex(self.model.index(self.current_path))
                self.path_changed_signal.emit(self.current_path)

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        selected_paths = self.get_selected_items_paths()
        self.selection_changed_signal.emit(selected_paths)

        if selected_paths:
            count = len(selected_paths)
            if count == 1:
                self.status_message_signal.emit(f"Selected: {os.path.basename(selected_paths[0])}")
            else:
                self.status_message_signal.emit(f"{count} items selected.")
        else:
            self.status_message_signal.emit("No items selected.")

    def get_selected_items_paths(self) -> list[str]:
        selection_model = self.list_view.selectionModel()
        if not selection_model: return []
        selected_indexes = selection_model.selectedIndexes() # QListView's selectedIndexes() is direct
        paths = [self.model.filePath(index) for index in selected_indexes]
        return paths

    def _on_double_clicked(self, index: QModelIndex):
        if not index.isValid():
            logger.warning("Double-clicked on an invalid index.")
            return

        file_path = self.model.filePath(index)
        logger.debug(f"Double-clicked on item (Icon View): '{file_path}'")

        if self.model.isDir(index):
            self.set_current_path(file_path)
        else:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)):
                err_msg = f"Could not open file '{os.path.basename(file_path)}'. No default application or permission denied."
                logger.error(f"QDesktopServices.openUrl failed for: '{file_path}'. {err_msg}")
                QMessageBox.warning(self, "Open File Error", err_msg)
            else:
                logger.info(f"Opened file with default application: '{file_path}'")

    def _open_context_menu(self, position: QPoint):
        selected_paths = self.get_selected_items_paths()
        index_under_mouse = self.list_view.indexAt(position)

        target_dir_for_creation = self.current_path
        if index_under_mouse.isValid() and self.model.isDir(index_under_mouse):
            target_dir_for_creation = self.model.filePath(index_under_mouse)

        menu = QMenu(self)

        def add_menu_action(text, slot, icon_theme_name=None, shortcut=None, enabled=True):
            icon = QIcon.fromTheme(icon_theme_name, QIcon()) if icon_theme_name else QIcon()
            action = QAction(icon, text, menu)
            if slot: action.triggered.connect(slot)
            if shortcut: action.setShortcut(QKeySequence(shortcut))
            action.setEnabled(enabled)
            menu.addAction(action)
            return action

        if selected_paths:
            add_menu_action("Open", lambda: self._handle_open_selected(selected_paths), "document-open")
            if len(selected_paths) == 1:
                add_menu_action("Rename...", lambda: self._handle_rename(selected_paths[0]), "edit-rename")
            menu.addSeparator()
            add_menu_action("Copy", lambda: self._handle_copy(selected_paths), "edit-copy", QKeySequence.StandardKey.Copy)
            add_menu_action("Cut", lambda: self._handle_cut(selected_paths), "edit-cut", QKeySequence.StandardKey.Cut)
            menu.addSeparator()
            add_menu_action("Delete", lambda: self._handle_delete(selected_paths), "edit-delete", QKeySequence.StandardKey.Delete)
            menu.addSeparator()

        can_paste = self.file_op_service and self.file_op_service.get_clipboard_status().get('can_paste', False)
        add_menu_action("Paste", lambda: self._handle_paste(target_dir_for_creation), "edit-paste", QKeySequence.StandardKey.Paste, enabled=can_paste)
        menu.addSeparator()
        add_menu_action("New Folder...", lambda: self._handle_create_folder(target_dir_for_creation), "folder-new")
        add_menu_action("New File...", lambda: self._handle_create_file(target_dir_for_creation), "document-new")

        if selected_paths:
            menu.addSeparator()
            llm_submenu = menu.addMenu(QIcon.fromTheme("system-search", QIcon()), "LLM Actions")
            analyze_action = QAction("Analyze / Summarize Selection", llm_submenu)
            analyze_action.triggered.connect(lambda: self._send_to_llm_for_analysis(selected_paths))
            llm_submenu.addAction(analyze_action)
            if len(selected_paths) == 1:
                rename_sugg_action = QAction("Suggest New Name(s)", llm_submenu)
                rename_sugg_action.triggered.connect(lambda: self._send_to_llm_for_rename_suggestion(selected_paths[0]))
                llm_submenu.addAction(rename_sugg_action)

        viewport = self.list_view.viewport()
        if viewport:
            menu.exec(viewport.mapToGlobal(position))
        else:
            logger.error("ListView viewport not found, cannot show context menu.")

    def _send_to_llm_for_analysis(self, paths: list[str]):
        if not paths: return
        filenames = [os.path.basename(p) for p in paths]
        command = f"Analyze the following selected items: {', '.join(filenames)}. Provide a brief overview or interesting details."
        if len(paths) == 1 and os.path.isfile(paths[0]):
            command = f"Summarize or analyze the selected file: {os.path.basename(paths[0])}."
        logger.info(f"Emitting LLM request for analysis: {command[:100]}...")
        self.request_llm_command_signal.emit(command, paths)

    def _send_to_llm_for_rename_suggestion(self, path: str):
        if not path: return
        filename = os.path.basename(path)
        command = f"Suggest 3 better or alternative names for the file: '{filename}'."
        logger.info(f"Emitting LLM request for rename suggestion: {command}")
        self.request_llm_command_signal.emit(command, [path])

    def _handle_operation(self, operation_name: str, op_callable, success_msg: str, error_msg: str, *args):
        if not self.file_op_service:
            QMessageBox.warning(self, "Service Error", "File Operation Service is not available.")
            logger.error(f"{operation_name} failed: FileOperationService not available.")
            return

        logger.info(f"Handling '{operation_name}' with args: {args}")
        actual_args = list(args)
        actual_args.append(self)

        success, message = op_callable(*actual_args)

        if success:
            QMessageBox.information(self, success_msg, message)
        else:
            QMessageBox.warning(self, error_msg, message)
        self.status_message_signal.emit(message)

    def _handle_input_operation(self, operation_name: str, op_callable,
                                input_title: str, input_label: str,
                                success_msg: str, error_msg: str,
                                first_arg_for_op,
                                default_text: str = ""):
        input_text, ok = QInputDialog.getText(self, input_title, input_label, text=default_text)
        if ok and input_text.strip():
            self._handle_operation(operation_name, op_callable, success_msg, error_msg,
                                   first_arg_for_op, input_text.strip())
        elif ok and not input_text.strip():
            QMessageBox.warning(self, "Invalid Name", f"{operation_name} name cannot be empty.")
            logger.warning(f"{operation_name} attempt with empty name.")
        else:
            logger.info(f"{operation_name} operation cancelled by user.")

    def _handle_open_selected(self, paths: list[str]):
        if not paths: return
        logger.info(f"Handling 'Open' for {len(paths)} item(s). First: {paths[0]}")
        for path_item in paths:
            index = self.model.index(path_item)
            if index.isValid(): self._on_double_clicked(index)
            else:
                logger.warning(f"Invalid model index for path: '{path_item}'. Fallback open.")
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(path_item)):
                    QMessageBox.warning(self, "Open Error", f"Could not open {os.path.basename(path_item)}.")

    def _handle_delete(self, paths_to_delete: list[str]):
        if paths_to_delete and self.file_op_service:
            self._handle_operation("Delete", self.file_op_service.delete_items,
                                   "Deletion Complete", "Deletion Error", paths_to_delete)
        elif not self.file_op_service:
            QMessageBox.warning(self, "Service Error", "File Operation Service is not available.")
        else:
            logger.debug("Delete called with no selection.")

    def _handle_rename(self, path_to_rename: str):
        if not self.file_op_service:
            QMessageBox.warning(self, "Service Error", "File Operation Service is not available.")
            return
        current_name = os.path.basename(path_to_rename)
        self._handle_input_operation(
            "Rename", self.file_op_service.rename_item,
            "Rename Item", f"Enter new name for '{current_name}':",
            "Rename Complete", "Rename Error",
            path_to_rename,
            default_text=current_name
        )

    def _handle_create_file(self, parent_dir_path: str):
        if not self.file_op_service:
            QMessageBox.warning(self, "Service Error", "File Operation Service is not available.")
            return
        self._handle_input_operation(
            "Create File", self.file_op_service.create_file,
            "Create New File", "Enter file name (e.g., new_document.txt):",
            "Success", "Error Creating File",
            parent_dir_path
        )

    def _handle_create_folder(self, parent_dir_path: str):
        if not self.file_op_service:
            QMessageBox.warning(self, "Service Error", "File Operation Service is not available.")
            return
        self._handle_input_operation(
            "Create Folder", self.file_op_service.create_folder,
            "Create New Folder", "Enter folder name:",
            "Success", "Error Creating Folder",
            parent_dir_path
        )

    def _handle_copy(self, paths_to_copy: list[str]):
        if not self.file_op_service: return
        if paths_to_copy:
            self.file_op_service.copy_to_clipboard(paths_to_copy)
            msg = f"{len(paths_to_copy)} item(s) copied to clipboard."
            self.status_message_signal.emit(msg)
            logger.info(msg)
        else: self.status_message_signal.emit("Nothing selected to copy.")

    def _handle_cut(self, paths_to_cut: list[str]):
        if not self.file_op_service: return
        if paths_to_cut:
            self.file_op_service.cut_to_clipboard(paths_to_cut)
            msg = f"{len(paths_to_cut)} item(s) cut to clipboard."
            self.status_message_signal.emit(msg)
            logger.info(msg)
        else: self.status_message_signal.emit("Nothing selected to cut.")

    def _handle_paste(self, destination_dir: str):
        if not self.file_op_service:
            QMessageBox.warning(self, "Service Error", "File Operation Service is not available.")
            return
        self._handle_operation("Paste", self.file_op_service.paste_from_clipboard,
                               "Paste Operation", "Paste Operation", destination_dir)
