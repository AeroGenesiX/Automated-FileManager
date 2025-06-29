import logging
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit, QScrollArea
from PyQt6.QtCore import Qt
import os

try:
    import olefile
except ImportError:
    olefile = None

logger = logging.getLogger("automgr.previews.doc")

def extract_doc_text(file_path):
    # Minimal .doc text extraction using olefile (does not support all cases)
    if olefile is None:
        return "olefile is not installed. Please install it to preview .doc files."
    try:
        if not olefile.isOleFile(file_path):
            return "Not a valid OLE .doc file."
        ole = olefile.OleFileIO(file_path)
        if not ole.exists('WordDocument'):
            return "No WordDocument stream found."
        stream = ole.openstream('WordDocument')
        data = stream.read()
        # This is a very basic and partial extraction (for demo only)
        text = data.decode(errors='ignore')
        # Filter to printable chars
        import string
        printable = set(string.printable)
        text = ''.join(filter(lambda x: x in printable, text))
        return text[:10000] if text else "No readable text found."
    except Exception as e:
        logger.error(f"Error reading .doc file {file_path}: {e}", exc_info=True)
        return f"Error reading .doc file: {os.path.basename(file_path)}\n\n{e}"

class DocPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.label = QLabel("DOC Preview Area")
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setPlaceholderText(".doc file preview")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.text_area)
        layout.addWidget(self.label)
        layout.addWidget(scroll)
        self._current_path = None

    def load_doc(self, file_path):
        self.clear_preview()
        self._current_path = file_path
        text = extract_doc_text(file_path)
        self.text_area.setPlainText(text)
        logger.info(f"Loaded DOC preview: {file_path}")

    def clear_preview(self):
        self.text_area.clear()
        self.label.setText("DOC Preview Area")
        self._current_path = None
        logger.debug("DOC preview cleared.")
