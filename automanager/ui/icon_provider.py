from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo

class IconProvider(QFileIconProvider):
    """
    A custom icon provider that uses the system's icon theme but allows
    for specific overrides or fallbacks.
    """
    def icon(self, type: QFileIconProvider.IconType | QFileInfo):
        if isinstance(type, QFileInfo):
            fileInfo = type
            # For directories, always use the theme's folder icon.
            if fileInfo.isDir():
                return QIcon.fromTheme("folder")

            # Get the file extension.
            ext = fileInfo.suffix().lower()

            # Create a map for common extensions to Freedesktop icon names.
            # This helps in cases where the default provider might be too generic.
            ext_map = {
                'pdf': 'application-pdf',
                'zip': 'application-zip',
                'rar': 'application-vnd.rar',
                'tar': 'application-x-tar',
                'gz': 'application-gzip',
                '7z': 'application-x-7z-compressed',
                'txt': 'text-plain',
                'md': 'text-markdown',
                'py': 'text-x-python',
                'js': 'application-javascript',
                'html': 'text-html',
                'css': 'text-css',
                'json': 'application-json',
                'xml': 'application-xml',
                'sh': 'application-x-shellscript',
                'doc': 'application-msword',
                'docx': 'application-vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls': 'application-vnd.ms-excel',
                'xlsx': 'application-vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'ppt': 'application-vnd.ms-powerpoint',
                'pptx': 'application-vnd.openxmlformats-officedocument.presentationml.presentation',
                'png': 'image-png',
                'jpg': 'image-jpeg',
                'jpeg': 'image-jpeg',
                'gif': 'image-gif',
                'svg': 'image-svg+xml',
                'mp3': 'audio-mpeg',
                'wav': 'audio-x-wav',
                'ogg': 'audio-ogg',
                'mp4': 'video-mp4',
                'avi': 'video-x-msvideo',
                'mkv': 'video-x-matroska',
            }

            icon_name = ext_map.get(ext)
            
            if icon_name:
                icon = QIcon.fromTheme(icon_name)
                # If a specific icon was found and it's not null, use it.
                if not icon.isNull():
                    return icon

        # If no specific icon is found in our map, or the theme doesn't have it,
        # fall back to the default provider's behavior. This is crucial.
        # The default provider is excellent at handling MIME types and other metadata.
        return super().icon(type)
