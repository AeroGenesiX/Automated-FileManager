"""
Main window for the Simple File Explorer application.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QListView, QMenu, QToolBar,
    QStatusBar, QMessageBox, QInputDialog, QLineEdit, QPushButton,
    QTabWidget
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QIcon

from file_operations import FileOperations
from preview import PreviewPanel
from command_console import CommandConsole

class FileExplorerWindow(QMainWindow):
    """Main window for the file explorer application."""
    
    def __init__(self):
        super().__init__()
        
        self.file_ops = FileOperations()
        
        self.setWindowTitle("Simple File Explorer")
        self.resize(1000, 600)
        
        self._init_ui()
        self._create_actions()
        self._create_menu()
        self._create_toolbar()
        self._connect_signals()
        
        # Set initial directory
        self._set_initial_directory()
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File system model
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.rootPath())
        
        # Directory tree view (left panel)
        self.dir_tree = QTreeView()
        self.dir_tree.setModel(self.fs_model)
        self.dir_tree.setRootIndex(self.fs_model.index(QDir.rootPath()))
        self.dir_tree.setAnimated(True)
        self.dir_tree.setHeaderHidden(True)
        self.dir_tree.setSortingEnabled(True)
        
        # Hide all columns except the first one (name)
        for i in range(1, self.fs_model.columnCount()):
            self.dir_tree.hideColumn(i)
        
        # File list view (middle panel)
        self.file_list = QListView()
        self.file_list.setModel(self.fs_model)
        self.file_list.setViewMode(QListView.ViewMode.IconMode)
        self.file_list.setGridSize(QSize(80, 80))
        self.file_list.setIconSize(QSize(48, 48))
        self.file_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.file_list.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        
        # Right panel with tabs
        self.right_panel = QTabWidget()
        
        # Preview panel (first tab)
        self.preview_panel = PreviewPanel()
        self.right_panel.addTab(self.preview_panel, "Preview")
        
        # Command console (second tab)
        self.command_console = CommandConsole()
        self.right_panel.addTab(self.command_console, "Console")
        
        # Add widgets to splitter
        self.splitter.addWidget(self.dir_tree)
        self.splitter.addWidget(self.file_list)
        self.splitter.addWidget(self.right_panel)
        
        # Set initial splitter sizes (30% / 40% / 30%)
        self.splitter.setSizes([300, 400, 300])
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        self.search_button = QPushButton("Search")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        
        # Add widgets to main layout
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_actions(self):
        """Create actions for menus and toolbars."""
        # File actions
        self.action_new_folder = QAction("New Folder", self)
        self.action_new_folder.setStatusTip("Create a new folder")
        
        self.action_rename = QAction("Rename", self)
        self.action_rename.setStatusTip("Rename selected file or folder")
        
        self.action_delete = QAction("Delete", self)
        self.action_delete.setStatusTip("Delete selected files or folders")
        
        self.action_exit = QAction("Exit", self)
        self.action_exit.setStatusTip("Exit the application")
        
        # View actions
        self.action_view_icons = QAction("Icons", self)
        self.action_view_icons.setStatusTip("View files as icons")
        
        self.action_view_list = QAction("List", self)
        self.action_view_list.setStatusTip("View files as list")
        
        self.action_view_details = QAction("Details", self)
        self.action_view_details.setStatusTip("View files with details")
        
        # Tools actions
        self.action_show_console = QAction("Show Console", self)
        self.action_show_console.setStatusTip("Show command console")
        
        # Help actions
        self.action_about = QAction("About", self)
        self.action_about.setStatusTip("Show the application's About box")
    
    def _create_menu(self):
        """Create the menu bar."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.action_new_folder)
        file_menu.addAction(self.action_rename)
        file_menu.addAction(self.action_delete)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.action_view_icons)
        view_menu.addAction(self.action_view_list)
        view_menu.addAction(self.action_view_details)
        
        # Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")
        tools_menu.addAction(self.action_show_console)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.action_about)
    
    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.action_new_folder)
        toolbar.addAction(self.action_rename)
        toolbar.addAction(self.action_delete)
        toolbar.addSeparator()
        toolbar.addAction(self.action_view_icons)
        toolbar.addAction(self.action_view_list)
        toolbar.addAction(self.action_view_details)
        toolbar.addSeparator()
        toolbar.addAction(self.action_show_console)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Directory tree signals
        self.dir_tree.clicked.connect(self._on_dir_tree_clicked)
        
        # File list signals
        self.file_list.clicked.connect(self._on_file_list_clicked)
        self.file_list.doubleClicked.connect(self._on_file_list_double_clicked)
        
        # Action signals
        self.action_new_folder.triggered.connect(self._on_new_folder)
        self.action_rename.triggered.connect(self._on_rename)
        self.action_delete.triggered.connect(self._on_delete)
        self.action_exit.triggered.connect(self.close)
        
        self.action_view_icons.triggered.connect(self._on_view_icons)
        self.action_view_list.triggered.connect(self._on_view_list)
        self.action_view_details.triggered.connect(self._on_view_details)
        
        self.action_show_console.triggered.connect(self._on_show_console)
        
        self.action_about.triggered.connect(self._on_about)
        
        # Search signals
        self.search_button.clicked.connect(self._on_search)
        self.search_input.returnPressed.connect(self._on_search)
        
        # File operations signals
        self.file_ops.operation_completed.connect(self._on_operation_completed)
        
        # Command console signals
        self.command_console.directory_changed.connect(self._on_console_directory_changed)
    
    def _set_initial_directory(self):
        """Set the initial directory to the user's home directory."""
        home_dir = os.path.expanduser("~")
        self.dir_tree.setCurrentIndex(self.fs_model.index(home_dir))
        self.file_list.setRootIndex(self.fs_model.index(home_dir))
        self.command_console.set_directory(home_dir)
        self.status_bar.showMessage(f"Location: {home_dir}")
    
    @pyqtSlot(QModelIndex)
    def _on_dir_tree_clicked(self, index):
        """Handle directory tree item click."""
        path = self.fs_model.filePath(index)
        self.file_list.setRootIndex(self.fs_model.index(path))
        self.command_console.set_directory(path)
        self.status_bar.showMessage(f"Location: {path}")
    
    @pyqtSlot(QModelIndex)
    def _on_file_list_clicked(self, index):
        """Handle file list item click."""
        path = self.fs_model.filePath(index)
        self.preview_panel.preview_file(path)
    
    @pyqtSlot(QModelIndex)
    def _on_file_list_double_clicked(self, index):
        """Handle file list item double click."""
        path = self.fs_model.filePath(index)
        if os.path.isdir(path):
            self.file_list.setRootIndex(index)
            self.dir_tree.setCurrentIndex(index)
            self.command_console.set_directory(path)
            self.status_bar.showMessage(f"Location: {path}")
    
    @pyqtSlot()
    def _on_new_folder(self):
        """Handle new folder action."""
        current_dir = self.fs_model.filePath(self.file_list.rootIndex())
        
        folder_name, ok = QInputDialog.getText(
            self, "New Folder", "Enter folder name:"
        )
        
        if ok and folder_name:
            path = os.path.join(current_dir, folder_name)
            self.file_ops.create_directory(path)
    
    @pyqtSlot()
    def _on_rename(self):
        """Handle rename action."""
        indexes = self.file_list.selectedIndexes()
        if not indexes:
            return
        
        index = indexes[0]  # Get the first selected item
        path = self.fs_model.filePath(index)
        old_name = os.path.basename(path)
        
        new_name, ok = QInputDialog.getText(
            self, "Rename", "Enter new name:", QLineEdit.EchoMode.Normal, old_name
        )
        
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            self.file_ops.rename_item(path, new_path)
    
    @pyqtSlot()
    def _on_delete(self):
        """Handle delete action."""
        indexes = self.file_list.selectedIndexes()
        if not indexes:
            return
        
        paths = [self.fs_model.filePath(index) for index in indexes]
        
        if len(paths) == 1:
            message = f"Are you sure you want to delete '{os.path.basename(paths[0])}'?"
        else:
            message = f"Are you sure you want to delete {len(paths)} items?"
        
        reply = QMessageBox.question(
            self, "Confirm Deletion", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for path in paths:
                self.file_ops.delete_item(path)
    
    @pyqtSlot()
    def _on_view_icons(self):
        """Switch to icon view mode."""
        self.file_list.setViewMode(QListView.ViewMode.IconMode)
        self.file_list.setGridSize(QSize(80, 80))
    
    @pyqtSlot()
    def _on_view_list(self):
        """Switch to list view mode."""
        self.file_list.setViewMode(QListView.ViewMode.ListMode)
        self.file_list.setGridSize(QSize(0, 0))
    
    @pyqtSlot()
    def _on_view_details(self):
        """Switch to details view mode."""
        self.file_list.setViewMode(QListView.ViewMode.ListMode)
        # Show all columns
        for i in range(1, self.fs_model.columnCount()):
            self.file_list.setColumnHidden(i, False)
    
    @pyqtSlot()
    def _on_show_console(self):
        """Show the command console tab."""
        self.right_panel.setCurrentWidget(self.command_console)
    
    @pyqtSlot()
    def _on_search(self):
        """Handle search action."""
        query = self.search_input.text().strip()
        if not query:
            return
        
        current_dir = self.fs_model.filePath(self.file_list.rootIndex())
        self.status_bar.showMessage(f"Searching for '{query}' in {current_dir}...")
        
        # Simple search implementation
        results = []
        for root, dirs, files in os.walk(current_dir):
            for name in files:
                if query.lower() in name.lower():
                    results.append(os.path.join(root, name))
        
        if results:
            # Navigate to the directory of the first result
            first_result = results[0]
            parent_dir = os.path.dirname(first_result)
            
            self.file_list.setRootIndex(self.fs_model.index(parent_dir))
            self.dir_tree.setCurrentIndex(self.fs_model.index(parent_dir))
            
            # Select the first result
            self.file_list.setCurrentIndex(self.fs_model.index(first_result))
            self.preview_panel.preview_file(first_result)
            
            self.status_bar.showMessage(f"Found {len(results)} matches for '{query}'")
        else:
            QMessageBox.information(
                self, "Search Results", f"No results found for '{query}'."
            )
            self.status_bar.showMessage("No results found")
    
    @pyqtSlot()
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Simple File Explorer",
            "A simple file explorer application with command console built with PyQt6."
        )
    
    @pyqtSlot(bool, str)
    def _on_operation_completed(self, success, message):
        """Handle file operation completion."""
        if success:
            self.status_bar.showMessage(message)
        else:
            QMessageBox.warning(self, "Operation Failed", message)
            self.status_bar.showMessage("Operation failed")
        
        # Refresh the view
        self.fs_model.refresh()
    
    @pyqtSlot(str)

    def _on_console_directory_changed(self, directory):
        """Handle directory change from console."""
        index = self.fs_model.index(directory)
        self.file_list.setRootIndex(index)
        self.dir_tree.setCurrentIndex(index)
        self.status_bar.showMessage(f"Location: {directory}")
