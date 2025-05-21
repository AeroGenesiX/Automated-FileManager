import os
import mimetypes
from datetime import datetime

class MetadataExtractor:
    """Extracts metadata from files."""

    def get_metadata(self, file_path):
        """Extract metadata from the given file path."""
        if not os.path.exists(file_path):
            return None
        
        metadata = {}
        metadata['name'] = os.path.basename(file_path)
        metadata['size'] = os.path.getsize(file_path)
        metadata['size_human'] = self._human_readable_size(metadata['size'])
        metadata['mime_type'], _ = mimetypes.guess_type(file_path)
        
        stat = os.stat(file_path)
        metadata['modified'] = datetime.fromtimestamp(stat.st_mtime)
        metadata['created'] = datetime.fromtimestamp(stat.st_ctime)
        
        # For images, get dimensions if possible
        if metadata['mime_type'] and metadata['mime_type'].startswith('image/'):
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    metadata['dimensions'] = f"{img.width}x{img.height}"
            except ImportError:
                metadata['dimensions'] = "PIL not installed"
            except Exception:
                metadata['dimensions'] = "Unknown"
        
        return metadata

    def _human_readable_size(self, size, decimal_places=2):
        """Convert size in bytes to a human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.{decimal_places}f} {unit}"
            size /= 1024.0
        return f"{size:.{decimal_places}f} PB"
