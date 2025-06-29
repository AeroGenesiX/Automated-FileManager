import os
import json
import requests
import logging

logger = logging.getLogger("automgr.core.llm_service")

class LLMService:
    def __init__(self, ollama_base_url="http://localhost:11434", model_name="gemma3:4b"): # Default to gemma:2b
        self.ollama_api_url = f"{ollama_base_url.rstrip('/')}/api/generate"
        self.model_name = model_name
        self.timeout = 60
        self._check_ollama_connection()
        logger.info(f"LLMService initialized. Model: '{self.model_name}', URL: '{ollama_base_url}', Timeout: {self.timeout}s.")

    def _check_ollama_connection(self):
        try:
            base_url = self.ollama_api_url.replace("/api/generate", "")
            response = requests.get(base_url, timeout=3)
            if response.status_code == 200 and "Ollama is running" in response.text:
                logger.info(f"Ollama connection test successful to {base_url}.")
                tags_url = f"{base_url}/api/tags"
                tags_response = requests.get(tags_url, timeout=3)
                if tags_response.status_code == 200:
                    models_data = tags_response.json()
                    available_models = [m.get("name") for m in models_data.get("models", [])]
                    if self.model_name in available_models:
                        logger.info(f"LLM model '{self.model_name}' is available in Ollama.")
                    else:
                        logger.warning(f"LLM model '{self.model_name}' NOT FOUND. Available: {available_models}. Pull with 'ollama pull {self.model_name}'.")
                else:
                    logger.warning(f"Could not verify Ollama models (status: {tags_response.status_code}).")
            else:
                logger.warning(f"Ollama connection test to {base_url} returned {response.status_code} or unexpected content: '{response.text[:100]}...'.")
        except requests.exceptions.ConnectionError:
            logger.critical(f"Ollama connection FAILED at '{self.ollama_api_url.replace('/api/generate', '')}'. Ensure Ollama is running.")
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama connection test timed out for '{self.ollama_api_url.replace('/api/generate', '')}'.")
        except Exception as e:
            logger.warning(f"Unexpected error during Ollama connection test: {e}", exc_info=True)

    def _construct_prompt(self, command_text: str, current_dir: str, selected_files: list[str]) -> str:
        selected_basenames = [os.path.basename(f) for f in selected_files] if selected_files else []

        prompt = f"""You are an expert AI assistant integrated into a desktop file manager.
Your goal is to translate natural language user commands into specific, executable shell commands or provide helpful file-related information.
You understand the user's current context.

Current Directory: "{current_dir}"
Selected Files/Folders (names only): {json.dumps(selected_basenames) if selected_basenames else "None"}
Full paths of selected items (for your reference, do not show to user unless asked): {json.dumps(selected_files) if selected_files else "None"}

User's Command: "{command_text}"

INSTRUCTIONS:
1.  If the command clearly maps to one or more shell commands (for a Linux-like environment such as bash), provide them.
    Prefix EACH INDIVIDUAL executable shell command on its own line with "SHELL_COMMAND:".
    Example 1 (single command):
    User: "list all python files"
    SHELL_COMMAND: find . -maxdepth 1 -type f -name "*.py"
    Example 2 (multiple commands):
    User: "create a directory called temp_stuff and then list its contents"
    SHELL_COMMAND: mkdir "temp_stuff"
    SHELL_COMMAND: ls "temp_stuff"
    Example 3 (multiple files selected by user):
    User: "compress selected files into archive.zip"
    (Assume selected_files are ["file1.txt", "/tmp/another file.docx", "my_folder"])
    SHELL_COMMAND: zip "archive.zip" "file1.txt" "/tmp/another file.docx" "my_folder"
2.  For destructive commands (e.g., `rm`, `mv` that might overwrite), you can still suggest the command. The application will handle final user confirmation. You MAY add a brief warning comment (e.g., `# This will delete files.`).
3.  If the command is to find files (e.g., "find all large images", "locate duplicate PDFs"), and you can determine the file paths, list them.
    Prefix the list with "FOUND_FILES_JSON:" followed by a JSON array of absolute file paths.
    Example:
    User: "find all text files in my home documents folder"
    FOUND_FILES_JSON: ["/home/user/Documents/report.txt", "/home/user/Documents/notes/meeting.txt"]
    (If you also provide a shell command to find them, that's fine too, but prioritize FOUND_FILES_JSON if the paths are directly known.)
4.  If the command is for general information retrieval about specific files (e.g., "summarize this document", "what type of file is this?"), provide a concise natural language response. Do NOT use "SHELL_COMMAND:" or "FOUND_FILES_JSON:" for these.
5.  If the command is ambiguous, too complex for simple shell commands or direct file listing, or requires actions beyond shell capabilities (e.g., "organize my photos by date taken into new folders"), explain what you understand and perhaps suggest a multi-step approach or state limitations.
6.  If the command seems like a general question not related to files in the current context, politely state that you are a file management assistant.
7.  Focus on commands relative to the "Current Directory" (`.`) unless absolute paths are given by the user or implied by "selected files". For selected files, use their basenames in commands if they are in the current directory. If selected files are from different directories, use their full or relative paths as appropriate for the command (e.g., `zip` can handle varied paths).
8.  Ensure file names with spaces or special characters are properly quoted in suggested shell commands (e.g., `rm "my file with spaces.txt"`). The application's terminal will handle execution.
9.  Be concise. Provide only the commands, the FOUND_FILES_JSON list, or the direct answer. Do not add conversational fluff like "Okay, here are the files/commands:" unless it's part of a non-command informational response.

Your Response:
"""
        return prompt

    def process_command(self, command_text: str, current_dir: str, selected_files: list[str]) -> str:
        prompt = self._construct_prompt(command_text, current_dir, selected_files)
        logger.info(f"Processing LLM command. Input: '{command_text[:100]}...'. Model: {self.model_name}")
        logger.debug(f"Full prompt to Ollama (first 500 chars):\n{prompt[:500]}...")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": { "temperature": 0.3, "num_ctx": 4096 }
        }
        response_obj: requests.Response | None = None

        try:
            response_obj = requests.post(self.ollama_api_url, json=payload, timeout=self.timeout)
            response_obj.raise_for_status()

            response_data = response_obj.json()
            llm_response_text = response_data.get("response", "").strip()

            if not llm_response_text:
                logger.warning("LLM returned an empty response.")
                return "LLM returned an empty response. Please try rephrasing your command."

            logger.debug(f"Raw LLM Response: {llm_response_text}")
            return llm_response_text

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ollama Connection Error: {e}", exc_info=True)
            return (f"FATAL ERROR: Could not connect to Ollama at {self.ollama_api_url}. "
                    "Ensure Ollama is running. Check logs for details.")
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s.")
            return (f"ERROR: Ollama request timed out. Model ('{self.model_name}') might be too slow "
                    f"or task too complex for timeout ({self.timeout}s).")
        except requests.exceptions.HTTPError as e:
            err_body = e.response.text[:200] if e.response else 'No response body'
            logger.error(f"Ollama HTTP Error: {e.response.status_code if e.response else 'N/A'} - {err_body}", exc_info=True)
            return f"ERROR: Ollama returned an error (Status {e.response.status_code if e.response else 'N/A'}). Detail: {err_body}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama Communication Error: {e}", exc_info=True)
            return f"ERROR: Failed to communicate with Ollama: {e}"
        except json.JSONDecodeError as e:
            raw_text = response_obj.text if response_obj else "No response object"
            logger.error(f"Ollama JSON Decode Error: {e}. Raw (first 500): {raw_text[:500]}", exc_info=True)
            return "ERROR: Could not parse LLM response (not valid JSON). Check Ollama server logs."
        except Exception as e:
            logger.critical(f"Unexpected error during LLM processing: {e}", exc_info=True)
            return f"UNEXPECTED ERROR: Internal error with LLM processing: {e}"
