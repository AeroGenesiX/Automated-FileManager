import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QScrollArea,
                             QStackedWidget, QGroupBox, QFormLayout, QLineEdit,
                             QApplication, QSizePolicy, QFrame, QSplitter) # Added QSplitter, QHBoxLayout
from PyQt6.QtCore import Qt, QFileInfo, pyqtSignal, QTimer, QUrl, QMimeDatabase
from PyQt6.QtGui import QIcon, QCloseEvent # Added QCloseEvent

# Import your custom preview widgets
from ..previews.image_preview_widget import ImagePreviewWidget
from ..previews.text_preview_widget import TextPreviewWidget
from ..previews.pdf_preview_widget import PdfPreviewWidget
from ..previews.video_preview_widget import VideoPreviewWidget
from ..previews.docx_preview_widget import DocxPreviewWidget
from ..previews.doc_preview_widget import DocPreviewWidget
# TODO: from ..previews.archive_preview_widget import ArchivePreviewWidget

logger = logging.getLogger("automgr.ui.preview_metadata")

class PreviewMetadataPane(QWidget):
    metadata_updated_for_file = pyqtSignal(str)

    def __init__(self, metadata_service=None, parent=None):
        super().__init__(parent)
        self.metadata_service = metadata_service
        self.current_file_path = None
        logger.debug("PreviewMetadataPane initialized.")

        # Main layout for this pane will now be a QHBoxLayout to hold the splitter
        outer_layout = QHBoxLayout(self) # Changed from QVBoxLayout
        self.setLayout(outer_layout)
        outer_layout.setContentsMargins(0,0,0,0) # Remove outer margins if splitter handles it

        # Create a QSplitter with Horizontal orientation
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self) # Changed orientation

        # --- Preview Section (will go into the splitter) ---
        self.preview_group = QGroupBox("Preview") # Keep GroupBox for title
        preview_group_layout = QVBoxLayout(self.preview_group) # Layout for inside the groupbox

        self.preview_stack = QStackedWidget()
        self.preview_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.no_preview_widget = QLabel("Select a file to preview.")
        self.no_preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_preview_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.no_preview_widget.setWordWrap(True)

        self.image_preview_widget = ImagePreviewWidget()
        self.text_preview_widget = TextPreviewWidget()
        self.pdf_preview_widget = PdfPreviewWidget()
        self.video_preview_widget = VideoPreviewWidget()
        self.docx_preview_widget = DocxPreviewWidget()
        self.doc_preview_widget = DocPreviewWidget()

        self.preview_stack.addWidget(self.no_preview_widget)
        self.preview_stack.addWidget(self.image_preview_widget)
        self.preview_stack.addWidget(self.text_preview_widget)
        self.preview_stack.addWidget(self.pdf_preview_widget)
        self.preview_stack.addWidget(self.video_preview_widget)
        self.preview_stack.addWidget(self.docx_preview_widget)
        self.preview_stack.addWidget(self.doc_preview_widget)

        preview_group_layout.addWidget(self.preview_stack)
        # self.preview_group will be added to the splitter


        # --- Metadata Section (will go into the splitter) ---
        self.metadata_group = QGroupBox("Metadata") # Keep GroupBox for title
        metadata_group_layout = QVBoxLayout(self.metadata_group)

        metadata_scroll_area = QScrollArea()
        metadata_scroll_area.setWidgetResizable(True)
        metadata_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        metadata_widget_container = QWidget()
        self.metadata_form_layout = QFormLayout(metadata_widget_container)
        self.metadata_form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.metadata_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.lbl_name = QLineEdit()
        self.lbl_name.setReadOnly(True)
        self.lbl_name.setFrame(False)

        self.lbl_path = QTextEdit()
        self.lbl_path.setReadOnly(True)
        self.lbl_path.setFrameShape(QFrame.Shape.NoFrame)
        self.lbl_path.setFixedHeight(45)
        self.lbl_path.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.lbl_path.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.lbl_size = QLabel()
        self.lbl_type = QLabel()
        self.lbl_created = QLabel()
        self.lbl_modified = QLabel()

        self.metadata_form_layout.addRow("Name:", self.lbl_name)
        self.metadata_form_layout.addRow("Path:", self.lbl_path)
        self.metadata_form_layout.addRow("Size:", self.lbl_size)
        self.metadata_form_layout.addRow("Type:", self.lbl_type)
        self.metadata_form_layout.addRow("Created:", self.lbl_created)
        self.metadata_form_layout.addRow("Modified:", self.lbl_modified)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Comma-separated tags (e.g., work, important)")
        self.tags_edit.editingFinished.connect(self._save_current_tags)
        self.metadata_form_layout.addRow("Tags:", self.tags_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add custom notes here...")
        self.notes_edit.setFixedHeight(100)
        self._notes_save_timer = QTimer(self)
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.setInterval(1500)
        self._notes_save_timer.timeout.connect(self._save_current_notes)
        self.notes_edit.textChanged.connect(self._notes_save_timer.start)
        self.metadata_form_layout.addRow("Notes:", self.notes_edit)

        metadata_scroll_area.setWidget(metadata_widget_container)
        metadata_group_layout.addWidget(metadata_scroll_area)
        # self.metadata_group will be added to the splitter

        # Add the GroupBoxes (which contain the actual content) to the QSplitter
        self.splitter.addWidget(self.preview_group)
        self.splitter.addWidget(self.metadata_group)

        # Set initial sizes for the splitter panes (optional, adjusts proportionally)
        # For a horizontal splitter, these are widths.
        # Example: Make preview take 2/3 and metadata 1/3 of the available width initially
        total_width = self.width() if self.width() > 0 else 800 # Estimate if not yet shown
        self.splitter.setSizes([int(total_width * 0.6), int(total_width * 0.4)])
        # Or you can set fixed minimum sizes if preferred
        # self.preview_group.setMinimumWidth(300)
        # self.metadata_group.setMinimumWidth(200)


        # Add the splitter to the main layout of PreviewMetadataPane
        outer_layout.addWidget(self.splitter)


    # ... rest of the methods (_clear_all_previews, update_preview, _clear_metadata_display_fields, etc.)
    # remain the same as the last fully correct version you had.
    # I'm only showing the __init__ method changes here for brevity.
    # Ensure to copy the full class content from your last working version and only modify __init__.

    def set_metadata_service(self, service):
        self.metadata_service = service

    def _clear_all_previews(self):
        logger.debug("Clearing all preview widgets before switching.")
        for i in range(self.preview_stack.count()):
            widget = self.preview_stack.widget(i)
            if hasattr(widget, 'clear_preview'): 
                try:
                    widget.clear_preview()
                except Exception as e:
                    logger.error(f"Error calling clear_preview on {widget.__class__.__name__}: {e}", exc_info=True)
            elif isinstance(widget, QLabel) and widget == self.no_preview_widget:
                widget.setText("Select a file to preview.")


    def update_preview(self, selected_paths: list[str]):
        logger.debug(f"Update preview/metadata requested for {len(selected_paths)} paths. First: {selected_paths[0] if selected_paths else 'None'}")

        new_selected_file = selected_paths[0] if selected_paths else None
        if self.current_file_path and self.current_file_path != new_selected_file:
            if self._notes_save_timer.isActive():
                self._notes_save_timer.stop() 
                self._save_current_notes()   

        self._clear_all_previews() 

        if not selected_paths: 
            self.current_file_path = None
            self.preview_stack.setCurrentWidget(self.no_preview_widget)
            self._clear_metadata_display_fields() 
            self.notes_edit.clear()
            self.notes_edit.setEnabled(False)
            self.tags_edit.clear()
            self.tags_edit.setEnabled(False)
            return

        path_to_preview = selected_paths[0]
        self.current_file_path = path_to_preview 

        if len(selected_paths) > 1:
            self.no_preview_widget.setText(f"{len(selected_paths)} items selected.\nPreview and detailed metadata are shown for single selections only.")
            self.preview_stack.setCurrentWidget(self.no_preview_widget)
            self._display_metadata_summary(selected_paths) 
            self.notes_edit.clear()
            self.notes_edit.setPlaceholderText("Notes are available for single item selection.")
            self.notes_edit.setEnabled(False)
            self.tags_edit.clear()
            self.tags_edit.setPlaceholderText("Tags are available for single item selection.")
            self.tags_edit.setEnabled(False)
        else: 
            self.no_preview_widget.setText("Select a file to preview.") 
            self._display_single_item_metadata(path_to_preview)             
            self.notes_edit.setEnabled(True)
            self.tags_edit.setEnabled(True)
            self._load_notes_and_tags(path_to_preview)

            file_info = QFileInfo(path_to_preview)
            ext = file_info.suffix().lower()
            
            mime_db = QMimeDatabase()
            mime_type = mime_db.mimeTypeForFile(path_to_preview) 
            logger.debug(f"Previewing single file: '{path_to_preview}', Extension: '{ext}', MIME Type: '{mime_type.name()}'")

            preview_loaded_successfully = False
            
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'ico']:
                self.image_preview_widget.load_image(path_to_preview)
                self.preview_stack.setCurrentWidget(self.image_preview_widget)
                preview_loaded_successfully = True
            elif ext == 'pdf':
                self.pdf_preview_widget.load_pdf(path_to_preview)
                self.preview_stack.setCurrentWidget(self.pdf_preview_widget)
                preview_loaded_successfully = True
            elif ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'mpeg', 'mpg', 'ogv', '3gp']:
                self.video_preview_widget.load_video(path_to_preview)
                self.preview_stack.setCurrentWidget(self.video_preview_widget)
                preview_loaded_successfully = True
            elif ext in ['docx', 'doc']:
                if ext == 'docx':
                    self.docx_preview_widget.load_docx(path_to_preview)
                    self.preview_stack.setCurrentWidget(self.docx_preview_widget)
                else:
                    self.doc_preview_widget.load_doc(path_to_preview)
                    self.preview_stack.setCurrentWidget(self.doc_preview_widget)
                preview_loaded_successfully = True
            elif mime_type.name().startswith("text/") or \
                 ext in ['py', 'js', 'json', 'md', 'log', 'ini', 'xml', 'html', 'css', 'csv', 'sh', 
                          'bat', 'conf', 'yaml', 'yml', 'c', 'cpp', 'h', 'java', 'cs', 'rb', 'php', 'go', 'rs', 'swift', 'kt', 'kts', 'gradle']:
                self.text_preview_widget.load_text(path_to_preview)
                self.preview_stack.setCurrentWidget(self.text_preview_widget)
                preview_loaded_successfully = True
            elif not preview_loaded_successfully and mime_type.isValid():
                if mime_type.name().startswith("image/"):
                    self.image_preview_widget.load_image(path_to_preview)
                    self.preview_stack.setCurrentWidget(self.image_preview_widget)
                    preview_loaded_successfully = True
                elif mime_type.name().startswith("video/"): 
                    self.video_preview_widget.load_video(path_to_preview)
                    self.preview_stack.setCurrentWidget(self.video_preview_widget)
                    preview_loaded_successfully = True
                
            if not preview_loaded_successfully:
                mime_name_display = mime_type.name() if mime_type.isValid() else "Unknown/Binary"
                self.no_preview_widget.setText(f"No preview available for:\n'{os.path.basename(path_to_preview)}'\n(Type: {mime_name_display})")
                self.preview_stack.setCurrentWidget(self.no_preview_widget)
                
    def _clear_metadata_display_fields(self):
        self.lbl_name.setText("")
        self.lbl_path.setText("")
        self.lbl_size.setText("")
        self.lbl_type.setText("")
        self.lbl_created.setText("")
        self.lbl_modified.setText("")

    def _display_metadata_summary(self, paths: list[str]):
        self._clear_metadata_display_fields()
        self.lbl_name.setText(f"{len(paths)} items selected")
        
        total_size = 0
        file_count = 0
        folder_count = 0
        for p in paths:
            if os.path.exists(p):
                if os.path.isfile(p):
                    total_size += QFileInfo(p).size()
                    file_count += 1
                elif os.path.isdir(p):
                    folder_count +=1
        
        size_text = f"Total size (files): {self._format_size(total_size)}" if file_count > 0 else "No files selected"
        self.lbl_size.setText(size_text)
        self.lbl_type.setText(f"{file_count} file(s), {folder_count} folder(s)")


    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 0: return "N/A"
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        size_kb = size_bytes / 1024
        if size_kb < 1024:
            return f"{size_kb:.2f} KB"
        size_mb = size_kb / 1024
        if size_mb < 1024:
            return f"{size_mb:.2f} MB"
        size_gb = size_mb / 1024
        return f"{size_gb:.2f} GB"

    def _display_single_item_metadata(self, path: str):
        if not os.path.exists(path):
            self._clear_metadata_display_fields()
            self.lbl_name.setText(f"Path does not exist: {os.path.basename(path)}")
            logger.warning(f"Metadata display requested for non-existent path: {path}")
            return
            
        file_info = QFileInfo(path)
        self.lbl_name.setText(file_info.fileName())
        self.lbl_path.setText(file_info.filePath()) 
        self.lbl_size.setText(self._format_size(file_info.size()) if file_info.isFile() else "--- (Folder)")
        
        mime_db = QMimeDatabase()
        mime_type = mime_db.mimeTypeForFile(path)
        
        type_description = ""
        if file_info.isDir():
            type_description = "Folder"
        elif mime_type.isValid():
            type_description = mime_type.comment() if mime_type.comment() else mime_type.name()
            if not type_description or type_description == "application/octet-stream":
                if file_info.suffix():
                    type_description = f"{file_info.suffix().upper()} File"
                else:
                    type_description = "File"
        else: 
            if file_info.suffix(): type_description = f"{file_info.suffix().upper()} File"
            else: type_description = "File (Unknown Type)"

        self.lbl_type.setText(type_description)
        
        birth_time = file_info.birthTime()
        self.lbl_created.setText(birth_time.toString("yyyy-MM-dd hh:mm:ss") if birth_time.isValid() else "N/A")
        
        last_modified_time = file_info.lastModified()
        self.lbl_modified.setText(last_modified_time.toString("yyyy-MM-dd hh:mm:ss") if last_modified_time.isValid() else "N/A")

    def _load_notes_and_tags(self, file_path: str):
        self.notes_edit.blockSignals(True)
        self.tags_edit.blockSignals(True)

        if self.metadata_service and file_path:
            meta = self.metadata_service.get_metadata(file_path)
            if meta:
                self.notes_edit.setPlainText(meta.get('notes', ""))
                self.tags_edit.setText(", ".join(meta.get('tags', [])))
                logger.debug(f"Loaded metadata for '{file_path}': Tags={meta.get('tags', [])}, Notes present={'Yes' if meta.get('notes') else 'No'}")
            else: 
                self.notes_edit.clear()
                self.tags_edit.clear()
                logger.debug(f"No metadata found in DB for '{file_path}'. Cleared notes/tags fields.")
        else: 
            self.notes_edit.clear()
            self.tags_edit.clear()
            logger.debug("Metadata service not available or no file path. Cleared notes/tags fields.")

        self.notes_edit.blockSignals(False)
        self.tags_edit.blockSignals(False)

    def _save_current_notes(self):
        if self.metadata_service and self.current_file_path and self.notes_edit.isEnabled():
            note_text = self.notes_edit.toPlainText()
            self.metadata_service.save_metadata(self.current_file_path, note_text=note_text)
            self.metadata_updated_for_file.emit(self.current_file_path) 
            logger.info(f"Notes saved for '{self.current_file_path}'.")

    def _save_current_tags(self):
        if self.metadata_service and self.current_file_path and self.tags_edit.isEnabled():
            tags_str = self.tags_edit.text()
            tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            self.metadata_service.save_metadata(self.current_file_path, tags=tags_list)
            self.metadata_updated_for_file.emit(self.current_file_path) 
            
            self.tags_edit.blockSignals(True) 
            self.tags_edit.setText(", ".join(tags_list)) 
            self.tags_edit.blockSignals(False)
            logger.info(f"Tags saved for '{self.current_file_path}': {tags_list}")

    def closeEvent(self, a0: QCloseEvent | None):
        if self._notes_save_timer.isActive():
            logger.debug("Close event: Forcing save of pending notes.")
            self._notes_save_timer.stop()
            self._save_current_notes()
        super().closeEvent(a0)