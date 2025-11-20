# Sidekick System Documentation

**Date**: 11/20/2025

## 1. Introduction & Philosophy

**Sidekick** is a powerful, command-line-native AI assistant designed to integrate seamlessly into a developer's local workflow. It acts as a bridge between the advanced reasoning capabilities of large language models and the user's local filesystem and desktop environment.

The core philosophy of Sidekick is to provide tangible, actionable results. It is not just a chatbot; it is a tool that can read your project files, understand your intent, generate code, and even apply those changes directly or operate your desktop GUI. It achieves this through two primary modes of operation: an interactive Q&A mode (`ask`) and an autonomous agent mode (`task`).

### Key Tenets

-   **Context is King**: Sidekick excels at consuming local context. It can package entire directory trees, individual files, or screen captures to provide the AI with the necessary information to generate relevant and accurate responses.
-   **Action-Oriented**: Through its "Work Mode" (`ask -w`) and its `task` command, Sidekick is designed to produce and apply changes. It can automatically write new files, patch existing ones, and perform complex multi-step actions using a suite of specialized agents.
-   **Developer-First Workflow**: Features like automated diff application, code extraction, and transcript logging are built specifically to accelerate development cycles.
-   **Extensible Agent Framework**: Sidekick's agent system is modular, allowing for the easy addition of new capabilities. A meta-agent intelligently delegates tasks to specialized agents responsible for areas like browser control, file manipulation, and speech.
-   **Local Integration with a Web UI**: Through the `sk local` command, Sidekick exposes its core functionality over a WebSocket server, enabling a rich, graphical user experience via the **SKYBOARD** frontend while the core logic runs locally.

## 2. Core Architecture

Sidekick is built in Python and organized around a central command-line dispatcher (`sk/cmd.py`) that routes requests to one of two main workflows: `ask` or `task`.

### 2.1. The `ask` Workflow: Conversational Q&A

The `ask` command (`ask_question` in `sk/cmd.py`) is designed for interactive sessions where the user provides a prompt and receives a text-based answer from an AI.

1.  **Context Aggregation**: Before sending a prompt, `ask` gathers context from several sources:
    -   **File/Directory Packaging**: If file or directory paths are provided as arguments, the `package_directory` utility (`sk/util.py`) creates a comprehensive text representation, including a file tree and the full contents of all non-binary files.
    -   **Screenshot Attachment (`-s`)**: Takes a full-screen screenshot and prepares it for vision-enabled models.
    -   **File Attachment (`-a`)**: Attaches a single (potentially binary) file.
2.  **Input & Tokenization**: The user's prompt is read from `stdin`, allowing for both interactive multi-line input and piped data. The `tiktoken` library is used to calculate and display the total input size in bytes and tokens, giving the user immediate feedback on context size.
3.  **AI Interaction**: The aggregated context and prompt are sent to the configured AI provider (Google Gemini or OpenAI, selected via the `--openai` flag). This is handled by the AI abstraction layer in `sk/ai/`.
4.  **Response Handling**: The AI's response is streamed to the console.

#### 2.1.1. The "Work" Subsystem (`sk/worker.py`)

The most powerful feature of `ask` is its Work Mode, enabled with the `-w` flag. This mode activates the `sk/worker.py` module, which processes the AI's response to perform actions on the local filesystem.

-   **Code Block Extraction**: The worker scans the AI's answer for Markdown code blocks.
-   **Filename Inference**: For each code block, it uses a sophisticated multi-stage heuristic to determine the target filename:
    1.  **Language Info Line**: Checks for a path in the info string (e.g., `` ```python:path/to/file.py``).
    2.  **`>>> BEGIN` Markers**: Looks for custom markers like `>>> BEGIN FILE: path/to/file.py` immediately preceding the block.
    3.  **Markdown Headings**: Scans for headings like `## Modifications for `path/to/file.py``.
    4.  **Contextual Cues**: Searches for backticked filenames in the text before the code block.
    5.  **In-Code Comments**: As a final fallback, it looks for filenames mentioned in comments inside the code itself (e.g., `# file: path/to/file.py`).
-   **File Operations**:
    -   If the block is a `diff` or `patch`, the worker extracts the target file from the diff content and applies it using the system's `patch` command.
    -   For any other code block, it is treated as the full file content and is written to the inferred target file.
-   **Safety and Reporting**: Before modifying or overwriting a file, a backup (`.bak`) is created. The worker generates a "WORK SUMMARY" detailing all actions taken (WROTE, PATCHED, SKIPPED, FAILED), which is printed to the console and appended to a detailed transcript log file saved in a temporary directory.

### 2.2. The `task` Workflow: Autonomous Agents

The `task` command (`do_task` in `sk/cmd.py`) invokes Sidekick's autonomous agent system. The user provides a high-level objective, and the system formulates and executes a multi-step plan to achieve it.

This workflow is built on a two-layer AI decision architecture:

1.  **Meta-Agent / Orchestrator (`sk/agent/__init__.py`)**:
    -   When `task` is run, the user's prompt is first sent to a "meta-agent" via the `prompt_for_agent` function.
    -   This meta-agent's sole purpose is to analyze the prompt and break it down into a sequence of steps, delegating each step to the most appropriate specialized agent.
    -   It returns a JSON list representing the plan, e.g., `[{"agent": "browser", "prompt": "find the current price of gold"}, {"agent": "speech", "prompt": "report the price found"}]`.
2.  **Specialized Agents (`sk/agent/*.py`)**:
    -   Each specialized agent is an expert in a specific domain. When invoked by the orchestrator, it receives its sub-prompt.
    -   It uses its own `prompt_for_action` function to convert the sub-prompt into a sequence of concrete, machine-executable actions (e.g., `{"action": "click", "what_to_click": "the search button"}`).
    -   The core agents include:
        -   `browser`: Interacts with the web and desktop GUI using `pyautogui`. It leverages AI vision to locate elements on the screen based on natural language descriptions ("click the login button").
        -   `control`: Manages workflow logic like delays and loops.
        -   `speech`: Provides text-to-speech capabilities using platform-specific libraries.
        -   `file`: (Stubbed) Intended for filesystem operations.
        -   `wild`: A general-purpose catch-all for prompts that don't map to other agents.

### 2.3. The Action Framework (`sk/action/__init__.py`)

This framework provides the runtime for executing the action plans generated by specialized agents.

-   **`ActionsBase`**: A base class that takes a list of actions, finds the corresponding `do_<action_name>` method within the agent's `Actions` class, and executes them in sequence.
-   **`Context` & `FileResult`**: A `Context` object is passed through the entire chain of actions for a single `task`. It holds state, most importantly the `last_result`, which is a `FileResult` object. This allows agents to chain operations; for example, the `browser` agent might take a screenshot and save it to a file, passing the `FileResult` to the `speech` agent, which then describes the image content.

## 3. The `sk local` Backend

Sidekick includes a built-in WebSocket server, launched with the `sk local` command, that serves as a local backend for the SKYBOARD web UI. This component (`sk/local.py`) bridges the gap between the browser and the user's local machine.

### Key Features:

-   **Local Terminal**: Provides a full pseudo-terminal (`pty`) to SKYBOARD on POSIX-compliant systems, allowing users to run shell commands on their local machine from the web UI.
-   **Filesystem Bridge**: Handles `fs_list` and `fs_read` requests, enabling SKYBOARD's file explorer to browse the local filesystem.
-   **`ask` Command Gateway**: It exposes the `sk ask` command over the WebSocket. The SKYBOARD `Ask` application can send a prompt and file attachments; the server executes `ask` as a local subprocess and streams the output back to the UI in real-time.
-   **Pre-flight Stats Calculation**: Offers an `ask_stats` endpoint that calculates the byte and token count for a potential prompt and its attachments *before* submission. This allows the UI to provide instant feedback to the user about context size and potential cost.

## 4. Command Reference

Sidekick is invoked through three main entry points: `sk`, `ask`, and `task`.

### `ask [options] [path...]`

Interactively ask a question or provide a prompt.

-   `[path...]`: Optional. One or more local file or directory paths to be packaged as context.
-   `-w`, `--work`: Enables "Work Mode" to automatically apply code and patches from the response.
-   `-s`: Attaches a screenshot as context.
-   `-a <filename>`: Attaches a single file as context.
-   `-e <lang> <file>`: Extracts the first Markdown code block of `<lang>` from the response and saves it to `<file>`.
-   `--openai`: Use OpenAI models instead of the default Google Gemini.
-   `-1`, `-2`, `-3`: Select AI model quality/speed tier (e.g., Flash vs. Pro, or Mini vs. main model).
-   `-q`: Quiet mode (reduces boilerplate output).
-   `-c`: Chatter mode (prints detailed AI interaction logs).

### `task [options] <prompt>`

Execute a prompt using the autonomous agent framework. The prompt should be a high-level goal. Options are similar to `ask`.

### `sk <sub-command> [args...]`

The main dispatcher for administrative and utility commands.

-   `help`: Displays help for `sk` sub-commands.
-   `agent`: Sub-commands for inspecting agents (e.g., `sk agent list`).
-   `action`: Sub-commands for inspecting agent actions.
-   `tree`: Prints a textual representation of a directory tree, with options for Markdown output and token counting.
-   `ticket`: A utility to fetch and display ticket information from a Phabricator database.
-   `local`: Starts the WebSocket server for SKYBOARD integration.
-   `md`: A utility to extract a code block from text piped via `stdin`.

## 5. Configuration

-   **API Keys**: Sidekick requires API keys to be set as environment variables:
    -   `GEMINI_API_KEY` for Google AI services.
    -   `OPENAI_API_KEY` for OpenAI services.
-   **Ignore Files**: You can control which files are included during directory packaging by creating a `.skignore` file in a directory. Its format is identical to `.gitignore`. By default, common temporary files and dotfiles are ignored.
-   **User Data**: Sidekick uses the `appdirs` library to store user-specific configuration in standard locations (e.g., `~/.config/sidekick` on Linux). This is used for database credentials and other settings.