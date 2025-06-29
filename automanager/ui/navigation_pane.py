import os
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt6.QtCore import pyqtSignal, QDir, Qt, QStandardPaths, QSize # QStandardPaths is correct
from PyQt6.QtGui import QIcon

logger = logging.getLogger("automgr.ui.navigation_pane")

class NavigationPane(QWidget):
    path_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("NavigationPane initialized.")
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.shortcut_list = QListWidget()
        self.shortcut_list.setIconSize(QSize(24,24)) # For icons
        layout.addWidget(self.shortcut_list)

        self._populate_shortcuts()
        self.shortcut_list.itemClicked.connect(self._on_item_clicked)

    def _populate_shortcuts(self):
        shortcuts = [
            ("Home", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation), "go-home"),
            ("Documents", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation), "folder-documents"),
            ("Downloads", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation), "folder-download"),
            ("Pictures", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation), "folder-pictures"),
            # VVVVVV THIS IS THE CORRECTED LINE VVVVVV
            ("Videos", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation), "folder-videos"), 
            # ^^^^^^ QStandardPaths (no underscore) ^^^^^^
            ("Music", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation), "folder-music"),
            ("Computer", QDir.rootPath(), "drive-harddisk")
            # Consider adding Desktop:
            # ("Desktop", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation), "user-desktop"),
        ]

        for name, path, icon_name in shortcuts:
            # Ensure path is not None or empty (QStandardPaths can return empty string if location doesn't exist/isn't set up)
            if path and ( (os.path.exists(path) and os.path.isdir(path)) or name == "Computer" ):
                item = QListWidgetItem(name)
                # Try to get themed icon
                icon = QIcon.fromTheme(icon_name) 
                # If you have custom icons in an assets folder and a Qt resource file:
                # if icon.isNull(): 
                #    icon = QIcon(f":/assets/icons/{icon_name.replace('-', '_')}.png") # Example resource path
                item.setIcon(icon)
                item.setData(Qt.ItemDataRole.UserRole, path) # Store the actual path in the item's data
                self.shortcut_list.addItem(item)
                logger.debug(f"Added shortcut: {name} -> {path}")
            else:
                logger.warning(f"Shortcut path '{path}' for '{name}' is invalid, non-existent, or not a directory. Skipping.")


    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole) # Retrieve the path stored in the item
        if path:
            logger.info(f"Navigation item '{item.text()}' clicked. Emitting path: {path}")
            self.path_selected.emit(path)