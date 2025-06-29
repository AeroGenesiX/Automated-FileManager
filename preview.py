"""
Preview panel for the Simple File Explorer.
"""

import os
import mimetypes
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
from metadata import MetadataExtractor

class PreviewPanel(QWidget):
    """Panel for previewing file contents and metadata."""
    
    def __init__(self):
        super().__init__()
        self.metadata_extractor = MetadataExtractor()
        self.current_file = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setScaledContents(False)
        
        # Metadata text area
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        
        # Add widgets to layout
        layout.addWidget(self.preview_label, 2)
        layout.addWidget(self.metadata_text, 1)
        
        # Set initial text
        self.preview_label.setText("No file selected")
        self.metadata_text.setText("")
    
    def preview_file(self, file_path):
        """Preview a file and display its metadata."""
        if not file_path or not os.path.exists(file_path):
            self.preview_label.setText("File not found")
            self.metadata_text.setText("")
            return
        
        self.current_file = file_path
        
        # Extract metadata
        metadata = self.metadata_extractor.get_metadata(file_path)
        
        # Display metadata
        self._display_metadata(metadata)
        
        # Display preview based on file type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type and mime_type.startswith("image/"):
            self._preview_image(file_path)
        elif mime_type and mime_type.startswith("text/"):
            self._preview_text(file_path)
        else:
            self.preview_label.setText(f"No preview available for {os.path.basename(file_path)}")
    
    def _preview_image(self, file_path):
        """Display an image preview."""
        try:
            image = QImage(file_path)
            if image.isNull():
                self.preview_label.setText("Cannot load image")
                return
            
            # Scale image to fit preview area while maintaining aspect ratio
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(
                self.width() - 20, 
                self.height() // 2,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.preview_label.setPixmap(pixmap)
        except Exception as e:
            self.preview_label.setText(f"Error previewing image: {str(e)}")
    
    def _preview_text(self, file_path):
        """Display a text file preview."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(5000)  # Limit to first 5K characters
            
            if len(content) == 5000:
                content += "\n\n[File truncated...]"
            
            self.preview_label.setText(content)
        except Exception as e:
            self.preview_label.setText(f"Error previewing text file: {str(e)}")
    
    def _display_metadata(self, metadata):
        """Display file metadata."""
        if not metadata:
            self.metadata_text.setText("No metadata available")
            return
        
        # Format metadata as text
        lines = []
        
        # Basic file info
        lines.append(f"<b>Name:</b> {metadata.get('name', 'Unknown')}")
        lines.append(f"<b>Size:</b> {metadata.get('size_human', 'Unknown')}")
        lines.append(f"<b>Type:</b> {metadata.get('mime_type', 'Unknown')}")
        
        if 'modified' in metadata:
            lines.append(f"<b>Modified:</b> {metadata['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if 'created' in metadata:
            lines.append(f"<b>Created:</b> {metadata['created'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add specific metadata based on file type
        if 'dimensions' in metadata:
            lines.append(f"<b>Dimensions:</b> {metadata['dimensions']}")
        
        # Set the formatted metadata text
        self.metadata_text.setHtml("<br>".join(lines))
