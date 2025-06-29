import os
import logging
import platform
import json # For potential future structured output from terminal commands
from PyQt6.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QApplication)
from PyQt6.QtCore import pyqtSignal, QProcess, QDir, Qt, QTimer # Added QTimer if needed
from PyQt6.QtGui import QColor, QPalette, QIcon

from ..core.llm_service import LLMService

logger = logging.getLogger("automgr.ui.llm_terminal")

class LLMChatWidget(QWidget):
    command_submitted = pyqtSignal(str)
    execute_commands_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.suggested_commands_list: list[str] = []
        logger.debug("LLMChatWidget initialized.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setStyleSheet("font-family: Monospace; font-size: 10pt;")
        layout.addWidget(self.history_view, 1)

        input_area_widget = QWidget()
        input_area_layout = QVBoxLayout(input_area_widget)
        input_area_layout.setContentsMargins(0, 0, 0, 0)

        command_input_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type your command (e.g., 'list files', 'delete selected *.tmp')")
        self.input_line.returnPressed.connect(self._send_command)
        command_input_layout.addWidget(self.input_line)

        self.send_button = QPushButton("Send")
        self.send_button.setIcon(QIcon.fromTheme("mail-send", QIcon()))
        self.send_button.clicked.connect(self._send_command)
        self.send_button.setToolTip("Send command to LLM")
        command_input_layout.addWidget(self.send_button)
        input_area_layout.addLayout(command_input_layout)

        self.execute_suggestions_button = QPushButton("Execute Suggested Command(s)")
        self.execute_suggestions_button.setIcon(QIcon.fromTheme("system-run", QIcon()))
        self.execute_suggestions_button.clicked.connect(self._execute_suggestions)
        self.execute_suggestions_button.setEnabled(False)
        self.execute_suggestions_button.setToolTip("Run all commands prefixed with 'SHELL_COMMAND:' from the last LLM response")
        input_area_layout.addWidget(self.execute_suggestions_button)

        layout.addWidget(input_area_widget, 0)
        self.setLayout(layout)

    def _send_command(self):
        command_text = self.input_line.text().strip()
        if command_text:
            self.add_message_to_history("User", command_text)
            self.command_submitted.emit(command_text)
            self.input_line.clear()
            self.suggested_commands_list = []
            self.execute_suggestions_button.setEnabled(False)
            logger.debug(f"User command submitted: '{command_text[:50]}...'")

    def add_message_to_history(self, sender: str, message: str):
        if sender == "User":
            escaped_message = message.replace("&", "&").replace("<", "<").replace(">", ">")
        else:
            escaped_message = message

        formatted_message = escaped_message.replace("\n", "<br>")

        sender_color = "blue" if sender == "User" else "darkgreen"
        if "Error" in sender.upper() or "ERROR" in message.upper():
            sender_color = "red"
        elif "WARN" in message.upper():
             sender_color = "orange"

        self.history_view.append(f"<b style='color:{sender_color};'>{sender}:</b> {formatted_message}")
        self.history_view.ensureCursorVisible()
        QApplication.processEvents()

        if sender == "LLM":
            self.suggested_commands_list = []
            shell_command_prefix = "SHELL_COMMAND:"
            raw_lines = message.split('\n')

            for line in raw_lines:
                stripped_line = line.strip()
                if stripped_line.startswith(shell_command_prefix):
                    command_part = stripped_line[len(shell_command_prefix):].strip()
                    if "#" in command_part:
                        command_part = command_part.split("#", 1)[0].strip()
                    if command_part:
                        self.suggested_commands_list.append(command_part)

            if self.suggested_commands_list:
                self.execute_suggestions_button.setEnabled(True)
                if len(self.suggested_commands_list) > 1:
                    self.history_view.append(f"<i>👆 {len(self.suggested_commands_list)} commands suggested. Click button to execute all sequentially or copy to terminal.</i>")
                else:
                    self.history_view.append(f"<i>👆 1 command suggested: '{self.suggested_commands_list[0]}'. Click button to execute or copy to terminal.</i>")
                logger.info(f"LLM suggested {len(self.suggested_commands_list)} command(s): {self.suggested_commands_list}")

    def set_processing_state(self, is_processing: bool):
        self.input_line.setEnabled(not is_processing)
        self.send_button.setEnabled(not is_processing)
        if is_processing:
            self.history_view.append("<i style='color:gray;'>LLM is thinking...</i>")
            self.history_view.ensureCursorVisible()

        self.execute_suggestions_button.setEnabled(
            not is_processing and bool(self.suggested_commands_list)
        )
        logger.debug(f"LLM processing state set to: {is_processing}. Execute button enabled: {self.execute_suggestions_button.isEnabled()}")

    def _execute_suggestions(self):
        if self.suggested_commands_list:
            commands_display_list = "\n".join([f"  • {cmd}" for cmd in self.suggested_commands_list])
            num_commands = len(self.suggested_commands_list)
            confirm_title = f"Confirm Execution of {num_commands} Command{'s' if num_commands > 1 else ''}"
            confirm_text = (f"Execute the following {num_commands} command{'s' if num_commands > 1 else ''} "
                            f"sequentially in the terminal?\n\n{commands_display_list}")

            reply = QMessageBox.question(self, confirm_title, confirm_text,
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.execute_commands_requested.emit(self.suggested_commands_list)
                logger.info(f"User confirmed execution of {num_commands} LLM command(s): {self.suggested_commands_list}")
        else:
            QMessageBox.information(self, "No Suggestions",
                                    "No shell commands were suggested in the last LLM response, or they have been cleared.")
            logger.debug("Execute suggestions clicked, but no commands currently available.")


class TerminalWidget(QWidget):
    internal_directory_changed = pyqtSignal(str) # Emitted when 'cd' is successful

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("TerminalWidget initialized.")
        layout = QVBoxLayout(self)
        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setPlaceholderText("Terminal output will appear here. Enter commands below.")

        palette = self.output_view.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(43, 43, 43))
        palette.setColor(QPalette.ColorRole.Text, QColor(248, 248, 242))
        self.output_view.setPalette(palette)
        self.output_view.setStyleSheet("font-family: Monospace; font-size: 10pt; border: 1px solid #555;")

        layout.addWidget(self.output_view, 1)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter shell command and press Enter")
        self.command_input.setStyleSheet("font-family: Monospace; font-size: 10pt;")
        self.command_input.returnPressed.connect(self.run_command_from_input)
        layout.addWidget(self.command_input, 0)

        self.setLayout(layout)

        self.process: QProcess | None = None
        self.command_queue: list[str] = []
        self.current_command_executing: bool = False

        self.shell_program: str = ""
        self.shell_args_for_command: list[str] = []

        self._determine_shell()
        self.current_terminal_dir: str = QDir.homePath()
        self._update_prompt()

    def _determine_shell(self):
        system = platform.system()
        if system == "Windows":
            self.shell_program = "cmd.exe"
            self.shell_args_for_command = ["/c"]
        elif system == "Darwin":
            self.shell_program = os.environ.get("SHELL", "/bin/zsh")
            if not os.path.exists(self.shell_program): self.shell_program = "/bin/bash"
            self.shell_args_for_command = ["-c"]
        else:
            self.shell_program = os.environ.get("SHELL", "/bin/bash")
            if not os.path.exists(self.shell_program): self.shell_program = "/bin/sh"
            self.shell_args_for_command = ["-c"]
        logger.info(f"Determined shell: {self.shell_program} with args: {self.shell_args_for_command}")

    def _init_process(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            logger.warning("Attempted to init QProcess while previous one is running. Killing old process.")
            self.process.kill()
            if not self.process.waitForFinished(500):
                logger.error("Old QProcess did not finish after kill signal.")

        self.process = QProcess(self)
        self.process.setProgram(self.shell_program)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error_occurred)
        logger.debug("QProcess initialized/re-initialized.")

    def _update_prompt(self):
        prompt_dir = os.path.basename(self.current_terminal_dir) if self.current_terminal_dir else "~"
        user = os.getenv("USER", "user")
        hostname = platform.node().split('.')[0]
        self.command_input.setPlaceholderText(f"{user}@{hostname}:{prompt_dir}$ ")

    def set_current_directory(self, path: str): # Called by external sync (MainWindow/Navigation)
        q_dir = QDir(path)
        if q_dir.exists() and q_dir.isReadable():
            new_cleaned_path = QDir.cleanPath(path)
            if self.current_terminal_dir != new_cleaned_path:
                self.current_terminal_dir = new_cleaned_path
                self._update_prompt()
                self.output_view.append(f"<i style='color:gray;'>Terminal directory externally set to: {self.current_terminal_dir}</i>")
                self.output_view.ensureCursorVisible()
                logger.info(f"Terminal CWD (externally) set to: {self.current_terminal_dir}")
        else:
            logger.warning(f"Failed to set terminal CWD to non-existent/unreadable path: {path}")
            self.output_view.append(f"<i style='color:red;'>Error: Cannot change directory to '{path}'</i>")

    def run_command_from_input(self):
        command = self.command_input.text().strip()
        self.command_input.clear()
        if command:
            if self.current_command_executing:
                self.output_view.append("<i style='color:orange;'>Previous command still running. Please wait.</i>")
                logger.warning("User tried to run command while terminal was busy.")
                return
            self.output_view.append(f"<b style='color:lightgreen;'>{self.command_input.placeholderText()}</b>{command}")
            self.output_view.ensureCursorVisible()
            self.current_command_executing = True
            self.execute_command_internal(command)

    def run_command_externally(self, command_or_list: str | list):
        commands_to_run: list[str] = []
        if isinstance(command_or_list, str):
            commands_to_run = [command_or_list]
            logger.info(f"Executing single command externally: {command_or_list}")
            self.output_view.append(f"<b style='color:lightblue;'>Executing (from LLM):</b> {command_or_list}")
        elif isinstance(command_or_list, list):
            commands_to_run = command_or_list
            logger.info(f"Queueing {len(commands_to_run)} commands for external execution: {commands_to_run}")
            self.output_view.append(f"<b style='color:lightblue;'>Executing {len(commands_to_run)} commands (from LLM):</b>")
            for i, cmd_str in enumerate(commands_to_run):
                 self.output_view.append(f"  <i>{i+1}. {cmd_str}</i>")
        else:
            logger.error(f"run_command_externally received invalid type: {type(command_or_list)}")
            return

        self.output_view.ensureCursorVisible()
        self.command_queue.extend(commands_to_run)
        if not self.current_command_executing:
            self._try_execute_next_queued_command()

    def _try_execute_next_queued_command(self):
        if self.current_command_executing or not self.command_queue:
            return

        self.current_command_executing = True
        command_to_run = self.command_queue.pop(0)

        # Only echo if it's a queued command and not the very first one from a direct external call (which already echoed)
        # This logic is a bit tricky, maybe simplify: always echo what's being run from queue.
        self.output_view.append(f"<b style='color:lightgreen;'>{self.command_input.placeholderText()}</b><i>(Queued)</i> {command_to_run}")
        self.output_view.ensureCursorVisible()
        self.execute_command_internal(command_to_run)

    def execute_command_internal(self, command: str):
        if command.lower().startswith("cd ") or command.lower() == "cd":
            try:
                target_dir_part = QDir.homePath() if command.lower() == "cd" else command[3:].strip().replace("~", QDir.homePath())
                new_dir_abs = os.path.abspath(os.path.join(self.current_terminal_dir, target_dir_part) if not os.path.isabs(target_dir_part) else target_dir_part)

                q_new_dir = QDir(new_dir_abs)
                if q_new_dir.exists() and q_new_dir.isReadable():
                    old_dir = self.current_terminal_dir
                    self.current_terminal_dir = QDir.cleanPath(new_dir_abs)
                    self._update_prompt()
                    self.output_view.append(f"<i style='color:gray;'>Terminal directory changed to: {self.current_terminal_dir}</i>")
                    if old_dir != self.current_terminal_dir:
                        self.internal_directory_changed.emit(self.current_terminal_dir) # <--- EMIT
                        logger.info(f"Internal 'cd' successful. New path '{self.current_terminal_dir}' emitted for GUI sync.")
                else:
                    self.output_view.append(f"<i style='color:red;'>cd: no such file or directory: {target_dir_part} (resolved to {new_dir_abs})</i>")
                    logger.warning(f"'cd' target invalid: {target_dir_part} (resolved to {new_dir_abs})")
            except Exception as e:
                logger.error(f"Error processing 'cd' command '{command}': {e}", exc_info=True)
                self.output_view.append(f"<i style='color:red;'>Error processing cd: {e}</i>")

            self.current_command_executing = False
            self._try_execute_next_queued_command()
            return

        if not self.process or self.process.state() != QProcess.ProcessState.NotRunning:
            self._init_process()

        if self.process and self.process.state() == QProcess.ProcessState.NotRunning:
            self.process.setWorkingDirectory(self.current_terminal_dir)
            full_command_args = self.shell_args_for_command + [command]
            self.process.setArguments(full_command_args)
            logger.debug(f"Starting process: {self.shell_program} with args {full_command_args} in CWD {self.current_terminal_dir}")
            self.process.start()
            if not self.process.waitForStarted(3000):
                err_str = self.process.errorString() if self.process else "Process object is None"
                logger.error(f"Process failed to start: {err_str}")
                self.output_view.append(f"<i style='color:red;'>Error starting process: {err_str}</i>")
                self.current_command_executing = False
                self._try_execute_next_queued_command()
        else:
            msg = "<i>Error: Terminal is busy or QProcess not ready. Command not started.</i>"
            self.output_view.append(msg)
            logger.error(f"{msg} Current process state: {self.process.state() if self.process else 'None'}")
            self.current_command_executing = False
            self._try_execute_next_queued_command()

    def handle_stdout(self):
        if not self.process: return
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode(errors='replace')
        self.output_view.insertPlainText(text)
        self.output_view.ensureCursorVisible()

    def handle_stderr(self):
        if not self.process: return
        data = self.process.readAllStandardError()
        text = bytes(data).decode(errors='replace').strip()
        if text:
            self.output_view.append(f"<pre style='color:red; margin:0; padding:0;'>{text}</pre>")
            self.output_view.ensureCursorVisible()

    def process_finished(self, exitCode: int, exitStatus: QProcess.ExitStatus):
        status_str = "normally" if exitStatus == QProcess.ExitStatus.NormalExit else "with a crash"
        log_msg = f"Process finished {status_str} with exit code {exitCode}."
        logger.info(log_msg)
        self.output_view.append(f"<i style='color:gray;'>{log_msg}</i>")
        self._update_prompt()
        self.output_view.ensureCursorVisible()
        self.current_command_executing = False
        self._try_execute_next_queued_command()

    def process_error_occurred(self, error: QProcess.ProcessError):
        error_map = {
            QProcess.ProcessError.FailedToStart: "Failed to Start", QProcess.ProcessError.Crashed: "Crashed",
            QProcess.ProcessError.Timedout: "Timed Out", QProcess.ProcessError.ReadError: "Read Error",
            QProcess.ProcessError.WriteError: "Write Error", QProcess.ProcessError.UnknownError: "Unknown Error"
        }
        error_str = error_map.get(error, f"Error Code {error}")
        process_error_detail = self.process.errorString() if self.process else "QProcess object is None"
        log_msg = f"QProcess Error: {error_str}. Details: {process_error_detail}"
        logger.error(log_msg)
        self.output_view.append(f"<i style='color:red;'>{log_msg}</i>")
        self._update_prompt()
        self.output_view.ensureCursorVisible()
        self.current_command_executing = False
        self._try_execute_next_queued_command()


class LLMTerminalPane(QTabWidget):
    external_path_change_request = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("LLMTerminalPane initialized.")
        self.llm_service = LLMService() # Pane holds the LLM service instance

        self.llm_chat_widget = LLMChatWidget()
        self.addTab(self.llm_chat_widget, QIcon.fromTheme("chat-message-new", QIcon()), "LLM Chat")

        self.terminal_widget = TerminalWidget()
        self.addTab(self.terminal_widget, QIcon.fromTheme("utilities-terminal", QIcon()), "Terminal")

        self.external_path_change_request.connect(self.terminal_widget.set_current_directory)
        self.currentChanged.connect(self._on_tab_changed)
        self.setTabToolTip(0, "Chat with the LLM for file operations and suggestions.")
        self.setTabToolTip(1, "Execute shell commands directly.")

    def _on_tab_changed(self, index: int):
        current_widget = self.widget(index)
        logger.debug(f"Tab changed to: {self.tabText(index)}")
        if current_widget == self.terminal_widget:
            self.terminal_widget.command_input.setFocus(Qt.FocusReason.TabFocusReason)
        elif current_widget == self.llm_chat_widget:
             self.llm_chat_widget.input_line.setFocus(Qt.FocusReason.TabFocusReason)

    def get_llm_chat_widget(self) -> LLMChatWidget:
        return self.llm_chat_widget

    def get_terminal_widget(self) -> TerminalWidget:
        return self.terminal_widget

    def get_llm_service(self) -> LLMService: # Allow MainWindow to access this instance
        return self.llm_service
