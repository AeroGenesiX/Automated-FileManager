"""
Command interpreter for the Simple File Explorer.
"""

import os
import shlex
import logging
from datetime import datetime
from typing import List, Tuple

from file_operations import FileOperations

class CommandInterpreter:
    """Interprets and executes shell-style commands."""
    
    def __init__(self, initial_directory=None):
        self.logger = logging.getLogger(__name__)
        self.file_ops = FileOperations()
        
        # Set current directory
        if initial_directory and os.path.isdir(initial_directory):
            self.current_directory = os.path.abspath(initial_directory)
        else:
            self.current_directory = os.path.abspath(os.path.expanduser("~"))
        
        # Command history
        self.history = []
        self.history_position = 0
        
        # Register commands
        self.commands = {
            "cd": self.cmd_cd,
            "ls": self.cmd_ls,
            "dir": self.cmd_ls,  # Alias for ls
            "pwd": self.cmd_pwd,
            "mkdir": self.cmd_mkdir,
            "rm": self.cmd_rm,
            "cp": self.cmd_cp,
            "mv": self.cmd_mv,
            "cat": self.cmd_cat,
            "find": self.cmd_find,
            "help": self.cmd_help,
            "clear": self.cmd_clear,
        }
    
    def execute(self, command_line: str) -> Tuple[bool, str, List[str]]:
        """
        Execute a command line.
        Returns a tuple of (success, message, output_lines).
        """
        if not command_line.strip():
            return True, "", []
        
        # Add to history
        self.history.append(command_line)
        self.history_position = len(self.history)
        
        # Parse the command line
        try:
            args = shlex.split(command_line)
            command = args[0].lower()
            
            # Check if command exists
            if command in self.commands:
                return self.commands[command](args[1:])
            else:
                return False, f"Command not found: {command}", []
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def get_previous_command(self) -> str:
        """Get the previous command from history."""
        if self.history_position > 0:
            self.history_position -= 1
            return self.history[self.history_position]
        return ""
    
    def get_next_command(self) -> str:
        """Get the next command from history."""
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            return self.history[self.history_position]
        elif self.history_position == len(self.history) - 1:
            self.history_position = len(self.history)
            return ""
        return ""
    
    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to the current directory."""
        if not path:
            return self.current_directory
        
        # Handle home directory
        if path.startswith("~"):
            path = os.path.expanduser(path)
        
        # If path is absolute, return it
        if os.path.isabs(path):
            return path
        
        # Otherwise, resolve relative to current directory
        return os.path.normpath(os.path.join(self.current_directory, path))
    
    # Command implementations
    def cmd_cd(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Change directory."""
        if not args:
            # Default to home directory
            new_dir = os.path.expanduser("~")
        else:
            new_dir = self._resolve_path(args[0])
        
        if not os.path.exists(new_dir):
            return False, f"Directory not found: {new_dir}", []
        
        if not os.path.isdir(new_dir):
            return False, f"Not a directory: {new_dir}", []
        
        self.current_directory = new_dir
        return True, f"Changed directory to: {new_dir}", []
    
    def cmd_ls(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """List directory contents."""
        # Parse arguments
        show_hidden = "-a" in args or "--all" in args
        show_long = "-l" in args
        
        # Filter out option arguments
        path_args = [arg for arg in args if not arg.startswith("-")]
        
        # Determine directory to list
        if path_args:
            directory = self._resolve_path(path_args[0])
        else:
            directory = self.current_directory
        
        if not os.path.exists(directory):
            return False, f"Directory not found: {directory}", []
        
        if not os.path.isdir(directory):
            return False, f"Not a directory: {directory}", []
        
        try:
            # Get directory contents
            items = os.listdir(directory)
            
            # Filter hidden files if not showing all
            if not show_hidden:
                items = [item for item in items if not item.startswith(".")]
            
            # Sort items (directories first, then files)
            items.sort()
            items.sort(key=lambda x: not os.path.isdir(os.path.join(directory, x)))
            
            output = []
            for item in items:
                item_path = os.path.join(directory, item)
                
                if show_long:
                    # Get item stats
                    stat_info = os.stat(item_path)
                    size = stat_info.st_size
                    modified = stat_info.st_mtime
                    
                    # Format modified time
                    modified_str = datetime.fromtimestamp(modified).strftime("%b %d %H:%M")
                    
                    # Indicate if it's a directory
                    if os.path.isdir(item_path):
                        type_indicator = "d"
                        item = f"{item}/"
                    else:
                        type_indicator = "-"
                    
                    output.append(f"{type_indicator} {size:8d} {modified_str} {item}")
                else:
                    if os.path.isdir(item_path):
                        item = f"{item}/"
                    output.append(item)
            
            return True, f"Directory listing of {directory}:", output
        except Exception as e:
            return False, f"Error listing directory: {str(e)}", []
    
    def cmd_pwd(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Print working directory."""
        return True, "Current directory:", [self.current_directory]
    
    def cmd_mkdir(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Create directory."""
        if not args:
            return False, "Usage: mkdir <directory>", []
        
        path = self._resolve_path(args[0])
        
        if os.path.exists(path):
            return False, f"Path already exists: {path}", []
        
        try:
            os.makedirs(path)
            return True, f"Created directory: {path}", []
        except Exception as e:
            return False, f"Error creating directory: {str(e)}", []
    
    def cmd_rm(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Remove files or directories."""
        if not args:
            return False, "Usage: rm [-r] <path>", []
        
        recursive = "-r" in args or "-rf" in args
        # Filter out option arguments
        path_args = [arg for arg in args if not arg.startswith("-")]
        
        if not path_args:
            return False, "No path specified", []
        
        path = self._resolve_path(path_args[0])
        
        if not os.path.exists(path):
            return False, f"Path not found: {path}", []
        
        try:
            if os.path.isdir(path):
                if recursive:
                    self.file_ops.delete_item(path)
                    return True, f"Removed directory: {path}", []
                else:
                    return False, f"Cannot remove directory without -r option: {path}", []
            else:
                self.file_ops.delete_item(path)
                return True, f"Removed file: {path}", []
        except Exception as e:
            return False, f"Error removing path: {str(e)}", []
    
    def cmd_cp(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Copy files or directories."""
        if len(args) < 2:
            return False, "Usage: cp [-r] <source> <destination>", []
        
        source = self._resolve_path(args[0])
        destination = self._resolve_path(args[1])
        
        if not os.path.exists(source):
            return False, f"Source not found: {source}", []
        
        try:
            self.file_ops.copy_item(source, destination)
            return True, f"Copied {source} to {destination}", []
        except Exception as e:
            return False, f"Error copying: {str(e)}", []
    
    def cmd_mv(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Move files or directories."""
        if len(args) < 2:
            return False, "Usage: mv <source> <destination>", []
        
        source = self._resolve_path(args[0])
        destination = self._resolve_path(args[1])
        
        if not os.path.exists(source):
            return False, f"Source not found: {source}", []
        
        try:
            self.file_ops.move_item(source, destination)
            return True, f"Moved {source} to {destination}", []
        except Exception as e:
            return False, f"Error moving: {str(e)}", []
    
    def cmd_cat(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Display file contents."""
        if not args:
            return False, "Usage: cat <file>", []
        
        path = self._resolve_path(args[0])
        
        if not os.path.exists(path):
            return False, f"File not found: {path}", []
        
        if os.path.isdir(path):
            return False, f"Cannot display contents of a directory: {path}", []
        
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
                # Split content into lines
                lines = content.splitlines()
                
                return True, f"Contents of {path}:", lines
        except Exception as e:
            return False, f"Error reading file: {str(e)}", []
    
    def cmd_find(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Find files matching a pattern."""
        if not args:
            return False, "Usage: find <pattern>", []
        
        pattern = args[0].lower()
        directory = self.current_directory
        
        if len(args) > 1:
            directory = self._resolve_path(args[1])
        
        if not os.path.exists(directory):
            return False, f"Directory not found: {directory}", []
        
        if not os.path.isdir(directory):
            return False, f"Not a directory: {directory}", []
        
        try:
            results = []
            for root, _, files in os.walk(directory):
                for file in files:
                    if pattern in file.lower():
                        results.append(os.path.join(root, file))
            
            if results:
                return True, f"Found {len(results)} matching files:", results
            else:
                return True, "No matching files found", []
        except Exception as e:
            return False, f"Error finding files: {str(e)}", []
    
    def cmd_help(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Display help information."""
        if args:
            command = args[0].lower()
            if command in self.commands:
                # Get the docstring for the command
                doc = self.commands[command].__doc__ or "No help available."
                return True, f"Help for {command}:", [doc]
            else:
                return False, f"Command not found: {command}", []
        
        # List all available commands
        command_list = sorted(self.commands.keys())
        return True, "Available commands:", command_list
    
    def cmd_clear(self, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Clear the console."""
        return True, "CLEAR", []  # Special message to indicate clearing the console
