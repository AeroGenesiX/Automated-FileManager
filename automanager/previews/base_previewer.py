from PyQt6.QtWidgets import QWidget
import abc # Abstract Base Classes

class AbstractPreviewer(QWidget):
    @abc.abstractmethod
    def __init__(self, parent=None):
        super().__init__(parent)

    @abc.abstractmethod
    def can_preview(self, file_path: str, mime_type: str) -> bool:
        """
        Check if this previewer can handle the given file.
        Returns True if it can, False otherwise.
        """
        pass

    @abc.abstractmethod
    def load_preview(self, file_path: str):
        """
        Load and display the preview for the file.
        This method will be called if can_preview returned True.
        """
        pass

    @abc.abstractmethod
    def clear_preview(self):
        """
        Clear the current preview content.
        """
        pass