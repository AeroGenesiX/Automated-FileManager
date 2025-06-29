"""
Main entry point for the Simple File Explorer application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from file_explorer import FileExplorerWindow

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Automated File-Manager")
    
    window = FileExplorerWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
