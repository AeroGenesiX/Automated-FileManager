import logging
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit, QScrollArea
from PyQt6.QtCore import Qt
import os

try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger("automgr.previews.docx")

class DocxPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.label = QLabel("DOCX Preview Area")
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setPlaceholderText(".docx file preview")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.text_area)
        layout.addWidget(self.label)
        layout.addWidget(scroll)
        self._current_path = None

    def load_docx(self, file_path):
        self.clear_preview()
        self._current_path = file_path
        if docx is None:
            self.text_area.setPlainText("python-docx is not installed. Please install it to preview .docx files.")
            logger.error("python-docx not installed.")
            return
        try:
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            if not text:
                text = "No text content found in this .docx file."
            self.text_area.setPlainText(text)
            logger.info(f"Loaded DOCX preview: {file_path}")
        except Exception as e:
            self.text_area.setPlainText(f"Error reading .docx file: {os.path.basename(file_path)}\n\n{e}")
            logger.error(f"Error reading .docx file {file_path}: {e}", exc_info=True)

    def clear_preview(self):
        self.text_area.clear()
        self.label.setText("DOCX Preview Area")
        self._current_path = None
        logger.debug("DOCX preview cleared.")
