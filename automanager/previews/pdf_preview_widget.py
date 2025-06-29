import os
import logging
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QScrollArea, QApplication, QSizePolicy
from PyQt6.QtGui import QPixmap, QImage, QResizeEvent
from PyQt6.QtCore import Qt, QSize
import fitz  # PyMuPDF

logger = logging.getLogger("automgr.previews.pdf")

class PdfPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0,0,0,0)

        # The QLabel will display the scaled pixmap. It should expand to fill available space.
        self.image_label = QLabel("PDF Preview Area")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # No minimum size on image_label itself if we want it to scale down fully.
        # The QGroupBox in PreviewMetadataPane will provide the overall structure.
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored) # Allow it to be scaled
        
        layout.addWidget(self.image_label) # No scroll area needed if we always scale to fit
        
        self._current_pdf_path = None
        self._original_page_pixmap = None # Store the initially rendered (possibly high-res) page
        self.render_dpi = 150 # DPI for initial rendering (higher DPI = better quality when scaled)

    def load_pdf(self, pdf_path: str):
        self.clear_preview()
        self._current_pdf_path = pdf_path
        logger.debug(f"Loading PDF: '{pdf_path}' for preview.")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            doc = fitz.open(pdf_path)
            if not doc.page_count > 0:
                self.image_label.setText("PDF is empty or invalid.")
                logger.warning(f"PDF '{pdf_path}' is empty or invalid.")
                return

            page = doc.load_page(0) # Preview the first page
            
            # Render page to a high-quality QPixmap using desired DPI
            # zoom = dpi / 72 (PyMuPDF default is 72 DPI)
            zoom = self.render_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False) # alpha=False for opaque RGB

            if pix.samples is None:
                self.image_label.setText("Error generating PDF page image data.")
                logger.error(f"Fitz pixmap (samples) generation failed for '{pdf_path}'.")
                return

            # Convert PyMuPDF Pixmap to QImage
            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)

            if qimage.isNull():
                self.image_label.setText("Error converting PDF page to QImage.")
                logger.error(f"QImage conversion failed for PDF page from '{pdf_path}'.")
                return

            self._original_page_pixmap = QPixmap.fromImage(qimage) # Store this "original" render
            if self._original_page_pixmap.isNull():
                self.image_label.setText("Error creating QPixmap from PDF page.")
                logger.error(f"QPixmap conversion failed for PDF page from '{pdf_path}'.")
                self._original_page_pixmap = None # Ensure it's None
                return
            
            # Now, scale this original pixmap to fit the current label size
            self._display_scaled_pixmap()
            doc.close()

        except Exception as e:
            self.image_label.setText(f"Error loading PDF:\n{os.path.basename(pdf_path)}\nDetails: {e}")
            logger.error(f"Error loading PDF '{pdf_path}': {e}", exc_info=True)
            self._original_page_pixmap = None
        finally:
            QApplication.restoreOverrideCursor()


    def _display_scaled_pixmap(self):
        """Scales the _original_page_pixmap to fit the image_label and displays it."""
        if self._original_page_pixmap and not self._original_page_pixmap.isNull():
            if self.image_label.width() > 0 and self.image_label.height() > 0: # Ensure label has a valid size
                scaled_pixmap = self._original_page_pixmap.scaled(
                    self.image_label.size(), # Scale to the current size of the image_label
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                # Label might not have a size yet if it's not visible or layout hasn't run
                # In this case, we can set the unscaled pixmap, and resizeEvent will handle it.
                # Or, defer scaling until resizeEvent. For simplicity, set it, resizeEvent will fix.
                self.image_label.setPixmap(self._original_page_pixmap)
                logger.debug("Image_label has no size yet, setting unscaled pixmap. ResizeEvent will adjust.")
        else:
            # If no original pixmap (e.g., due to error), ensure any old pixmap is cleared
            # and placeholder text is shown.
            current_text = self.image_label.text()
            self.image_label.setPixmap(QPixmap()) # Clear pixmap
            if "PDF Preview Area" not in current_text and "Error" not in current_text: # Avoid overwriting error messages
                 self.image_label.setText("PDF Preview Area")


    def clear_preview(self):
        self.image_label.clear() # Clears both text and pixmap
        self.image_label.setText("PDF Preview Area")
        self._current_pdf_path = None
        self._original_page_pixmap = None
        logger.debug("PDF preview cleared.")

    def resizeEvent(self, a0: QResizeEvent | None): # Renamed event to a0 for Pylance
        """Called when the widget (and thus image_label) is resized."""
        super().resizeEvent(a0) # Call base class implementation
        logger.debug(f"PdfPreviewWidget resizeEvent to: {self.size()}. Label size: {self.image_label.size()}")
        # When the widget is resized, re-scale the original_page_pixmap to the new size of image_label
        if self._original_page_pixmap and not self._original_page_pixmap.isNull():
            self._display_scaled_pixmap()