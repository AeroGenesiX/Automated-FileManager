import logging
from PyQt6.QtWidgets import QMessageBox, QWidget # Added QWidget for typing parent

logger = logging.getLogger("automgr.core.security_service")

class SecurityService:
    def __init__(self):
        logger.info("SecurityService initialized.")

    def request_confirmation(self, title: str, message: str, 
                             informative_text: str = "", 
                             parent: QWidget | None = None,
                             default_button = QMessageBox.StandardButton.No) -> bool:
        """
        Displays a confirmation dialog with more details.
        Returns True if 'Yes' is clicked, False otherwise.
        
        Args:
            title (str): The window title of the dialog.
            message (str): The main question or statement.
            informative_text (str, optional): Additional details displayed below the main message.
            parent (QWidget | None, optional): The parent widget for the dialog.
            default_button (QMessageBox.StandardButton, optional): The button that has initial focus.
        """
        logger.info(f"Requesting user confirmation. Title: '{title}', Message: '{message[:100]}...'")
        
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if informative_text:
            msg_box.setInformativeText(informative_text)
        
        msg_box.setIcon(QMessageBox.Icon.Question) # Could be Icon.Warning for destructive actions
        
        # Standard buttons: Yes, No. You can customize further if needed.
        yes_button = msg_box.addButton(QMessageBox.StandardButton.Yes)
        no_button = msg_box.addButton(QMessageBox.StandardButton.No)
        
        msg_box.setDefaultButton(default_button) # Set which button is focused/default

        # For critical actions, you might want to ensure 'No' is the safer default.
        # if default_button == QMessageBox.StandardButton.No:
        #    msg_box.setDefaultButton(no_button)
        # else:
        #    msg_box.setDefaultButton(yes_button)

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes: # Check against the actual button object if you used addButton differently
            logger.info("User confirmed action.")
            return True
        else:
            logger.info("User cancelled action.")
            return False

    def show_warning(self, title: str, message: str, informative_text: str = "", parent: QWidget | None = None):
        """Displays a warning message box."""
        logger.warning(f"Displaying warning. Title: '{title}', Message: '{message[:100]}...'")
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if informative_text:
            msg_box.setInformativeText(informative_text)
        msg_box.exec()

    def show_error(self, title: str, message: str, informative_text: str = "", parent: QWidget | None = None):
        """Displays an error message box."""
        logger.error(f"Displaying error. Title: '{title}', Message: '{message[:100]}...'")
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if informative_text:
            msg_box.setInformativeText(informative_text)
        msg_box.exec()

    def show_information(self, title: str, message: str, informative_text: str = "", parent: QWidget | None = None):
        """Displays an information message box."""
        logger.info(f"Displaying information. Title: '{title}', Message: '{message[:100]}...'")
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if informative_text:
            msg_box.setInformativeText(informative_text)
        msg_box.exec()


# Global instance for easy access, or it can be instantiated and passed around.
# This makes it a singleton-like access pattern.
security_manager = SecurityService()