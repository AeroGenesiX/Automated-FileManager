import os
import logging
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QImageReader # Using QImageReader for better format support and error handling
from PyQt6.QtCore import Qt, QSize

logger = logging.getLogger("automgr.previews.image")

class ImagePreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Image Preview Area")
        self.setMinimumSize(QSize(100,100))
        self._original_pixmap = None # Store the full-resolution pixmap
        self._current_image_path = None

    def load_image(self, image_path):
        self.clear_preview() # Clear previous
        self._current_image_path = image_path
        logger.debug(f"Loading image: {image_path}")

        reader = QImageReader(image_path)
        if not reader.canRead():
            error_msg = reader.errorString() if reader.errorString() else "Unsupported image format or file corrupted."
            self.setText(f"Cannot load image:\n{os.path.basename(image_path)}\n{error_msg}")
            logger.warning(f"Cannot read image {image_path}: {error_msg}")
            self._original_pixmap = None
            return
        
        # Optionally set quality for formats like JPEG
        # reader.setQuality(100) 
        
        # For large images, consider QImageReader.setScaledSize() to load a pre-scaled version
        # to save memory if the display area is much smaller.
        # However, for best quality on resize, load full then scale.
        image = reader.read()
        if image.isNull():
            self.setText(f"Failed to read image data:\n{os.path.basename(image_path)}")
            logger.error(f"Failed to read image data from {image_path}")
            self._original_pixmap = None
            return

        self._original_pixmap = QPixmap.fromImage(image)
        if self._original_pixmap.isNull(): # Should not happen if image was valid
            self.setText(f"Error converting QImage to QPixmap for {os.path.basename(image_path)}")
            logger.error(f"Error converting QImage to QPixmap for {image_path}")
            self._original_pixmap = None
            return

        self._display_scaled_pixmap()


    def _display_scaled_pixmap(self):
        if self._original_pixmap and not self._original_pixmap.isNull():
            # Scale pixmap to fit the label while maintaining aspect ratio
            # Use self.size() which is the current size of the QLabel
            scaled_pixmap = self._original_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
        else:
            # If no original pixmap, clear the display or show placeholder
            current_text = self.text() # Preserve text if it was an error message
            self.clear() # Clears pixmap
            if "Cannot load image" not in current_text and "Failed to read" not in current_text:
                self.setText("Image Preview Area") # Reset placeholder if no error
            else:
                self.setText(current_text) # Keep error message


    def clear_preview(self):
        self.clear() # Clears both text and pixmap
        self.setText("Image Preview Area")
        self._original_pixmap = None
        self._current_image_path = None
        logger.debug("Image preview cleared.")

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        # When the widget is resized, re-scale the original pixmap to the new size
        if self._original_pixmap and not self._original_pixmap.isNull():
            self._display_scaled_pixmap()