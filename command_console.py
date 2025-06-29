"""
Command console widget for the Simple File Explorer.
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QTextCursor, QKeyEvent

from commands import CommandInterpreter

class CommandConsole(QWidget):
    """Console widget for executing commands."""
    
    directory_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.command_interpreter = CommandInterpreter()
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(100)
        
        # Input area
        input_layout = QHBoxLayout()
        
        # Command prompt
        self.prompt_label = QLabel(">")
        
        # Command input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter command...")
        self.input_field.returnPressed.connect(self._on_command_entered)
        
        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.input_field)
        
        layout.addWidget(self.output_text)
        layout.addLayout(input_layout)
        
        # Display welcome message
        self.write_output("Welcome to the Simple File Explorer Command Console", "blue")
        self.write_output("Type 'help' for a list of available commands", "blue")
    
    def write_output(self, text, color="black"):
        """Write text to the output area with specified color."""
        self.output_text.setTextColor(QColor(color))
        self.output_text.append(text)
        
        # Scroll to bottom
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
    
    def clear_output(self):
        """Clear the output area."""
        self.output_text.clear()
    
    def set_directory(self, directory):
        """Set the current directory for the command interpreter."""
        success, message, _ = self.command_interpreter.cmd_cd([directory])
        if success:
            self.write_output(message, "green")
        else:
            self.write_output(message, "red")
    
    @pyqtSlot()
    def _on_command_entered(self):
        """Handle command entered by user."""
        command = self.input_field.text().strip()
        if not command:
            return
        
        # Display the command
        self.write_output(f"> {command}", "gray")
        
        # Clear the input field
        self.input_field.clear()
        
        # Execute the command
        success, message, output = self.command_interpreter.execute(command)
        
        # Handle special commands
        if message == "CLEAR":
            self.clear_output()
            return
        
        # Display the result
        if success:
            if output:
                for line in output:
                    self.write_output(line)
            if message:
                self.write_output(message, "green")
                
            # If directory changed, emit signal
            if command.startswith("cd "):
                self.directory_changed.emit(self.command_interpreter.current_directory)
        else:
            self.write_output(message, "red")
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if self.input_field.hasFocus():
            if event.key() == Qt.Key.Key_Up:
                # Navigate command history up
                prev_command = self.command_interpreter.get_previous_command()
                if prev_command:
                    self.input_field.setText(prev_command)
            elif event.key() == Qt.Key.Key_Down:
                # Navigate command history down
                next_command = self.command_interpreter.get_next_command()
                self.input_field.setText(next_command)
        
        super().keyPressEvent(event)
