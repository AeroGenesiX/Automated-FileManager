import logging
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QFontInfo
import os

logger = logging.getLogger("automgr.previews.text")

class TextPreviewWidget(QTextEdit):
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB limit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        # Try to find a common monospace font
        font = QFont("Consolas", 10) # Good on Windows
        if not QFontInfo(font).exactMatch():
            font = QFont("Monaco", 10) # Good on macOS
        if not QFontInfo(font).exactMatch():
            font = QFont("DejaVu Sans Mono", 10) # Good on Linux
        if not QFontInfo(font).exactMatch():
            font = QFont("Monospace", 10) # Generic fallback
        self.setFont(font)
        self.setPlaceholderText("Text/Code Preview Area")
        logger.debug("TextPreviewWidget initialized.")


    def load_text(self, file_path):
        self.clear_preview()
        logger.debug(f"Loading text file: {file_path}")
        try:
            # Determine encoding (very basic, can be improved with chardet library)
            encoding = 'utf-8'
            # try:
            #     with open(file_path, 'rb') as f_test_enc:
            #         f_test_enc.read(1024).decode('utf-8') # Try utf-8
            # except UnicodeDecodeError:
            #     encoding = 'latin-1' # Fallback for many Western encodings
            #     logger.debug(f"UTF-8 decode failed for {file_path}, trying {encoding}")


            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                # Check file size before reading full content
                f.seek(0, 2) # Go to end of file
                file_size = f.tell()
                f.seek(0) # Reset to beginning

                if file_size > self.MAX_FILE_SIZE_BYTES:
                    content_sample = f.read(self.MAX_FILE_SIZE_BYTES)
                    self.setPlainText(content_sample + f"\n\n--- File truncated (actual size: {file_size // 1024} KB) ---")
                    logger.info(f"Text file {file_path} truncated for preview (size: {file_size} bytes).")
                else:
                    content_sample = f.read()
                    self.setPlainText(content_sample)
            # TODO: Add syntax highlighting using QSyntaxHighlighter or Pygments
        except Exception as e:
            self.setPlainText(f"Error reading text file:\n{os.path.basename(file_path)}\n\n{e}")
            logger.error(f"Error reading text file {file_path}: {e}", exc_info=True)


    def clear_preview(self):
        self.clear() # Clears text content
        # self.setPlaceholderText("Text/Code Preview Area") # Placeholder re-appears automatically
        logger.debug("Text preview cleared.")