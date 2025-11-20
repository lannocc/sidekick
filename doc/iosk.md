# IOSK System Documentation

**Date**: 11/20/2025

## 1. Introduction & Philosophy

**IOSK** is a unique fusion of a UNIX-like operating system and a conversational AI environment. Its core philosophy revolves around providing an interactive, sandboxed OS where AI agents are first-class users, collaborating with humans and each other through a chat-based interface.

IOSK bridges the gap between traditional, rigid command-line interfaces and the fluidity of natural language. It retains the power and familiarity of a UNIX-like structure—including a standard filesystem hierarchy, pipes, redirection, and a rich set of commands—while augmenting it with an intelligent, conversational layer.

### Key Tenets

-   **Conversational Interface**: The primary mode of interaction is a chat room where users and AI agents issue commands, share information, and collaborate.
-   **AI as a User**: AI agents are not just tools; they are participants in the system, with their own user sessions, contexts, and ability to execute commands, just like a human user.
-   **Sandboxed Environment**: The entire OS runs within a sandboxed directory, providing a safe and isolated space for development, experimentation, and AI-driven tasks without affecting the host system.
-   **Persistent Context**: Through a "bank" memory system, AI agents can load and retain core instructions, personas, and contextual information across interactions, enabling more consistent and intelligent behavior.
-   **Code as Conversation**: The system is designed for development workflows. Code blocks shared in chat are automatically saved to the filesystem, and `diff` patches can be automatically applied, making coding and iteration a seamless part of the conversation.

## 2. Core Architecture

The IOSK kernel is built on a modern, asynchronous Python foundation using `asyncio`. Following a significant refactoring, the architecture is highly modular, with the main `IOSK` class in `src/iosk/kernel.py` acting as a central coordinator for several specialized managers.

### 2.1. The Kernel and Its Managers

The kernel orchestrates the system's lifecycle, state, and interactions between its core components.

-   **`IOSK` (The Kernel)**: The central class that initializes all subsystems, manages the main event loop, and handles system-level events like startup and shutdown. It holds references to all manager instances.
-   **`FileSystemManager` (`fs.py`)**: Encapsulates all virtual filesystem operations. It provides the "sandboxing" logic (`box` method) that maps virtual paths (e.g., `/bin/ls`) to their real paths on the host filesystem.
-   **`UserManager` (`users.py`)**: Manages the entire user lifecycle, including login, logout, home directory creation, and running the interactive session loop for both local console users and remote GUI clients.
-   **`ProcessManager` (`proc.py`)**: Manages command execution as distinct "processes." It assigns Process IDs (PIDs), tracks running commands in a process table (making them visible to commands like `ps`), and handles command lifecycle and termination (`kill`).

### 2.2. Session, Context, and History

IOSK employs a sophisticated two-part state model to distinguish between long-lived session data and transient, per-command data.

-   **`UserSessionState` (`io.py`)**: This class holds all data that defines a user's entire session. This includes their identity (`user`, `bot` status), AI context (`session_history`, `banks`), command history, aliases, and telemetry (`token_stats`). This object is shared by reference across all commands executed by a user.
-   **`Context` (`io.py`)**: A more transient object that represents the environment for a *single command or process*. It holds a reference to the parent `UserSessionState` object but contains its own per-command state, such as the current working directory (`pwd`), environment variables (`env`), and standard I/O streams (`stdin`, `stdout`). When a command is executed, a new `Context` is "forked" from the user's main context.
-   **Structured History (`HistoryEntry`)**: Session history is not stored as a single string but as a list of `HistoryEntry` objects. Each entry is numbered and contains the full text of a command and its output. This structure enables powerful features like the `forget` command to selectively remove context and the `rolling` command to automatically manage context size.

### 2.3. The Command Execution Pipeline

When a user types a command, it passes through a robust, multi-stage pipeline designed to provide a rich, UNIX-like shell experience.

1.  **Alias Resolution**: The `CommandPipelineExecutor` first checks if the command is an alias and expands it.
2.  **Parsing & Tokenization (`parser.py`)**: The `CommandLineParser` takes the raw command string and processes it:
    -   **Command Substitution**: Executes commands within backticks (`` `...` ``) or `$()` and replaces them with their output.
    -   **Variable Expansion**: Replaces `$VAR` and `${VAR}` with their values from the environment.
    -   **Tokenization**: Uses `shlex` to split the string into a list of arguments (`argv`), correctly handling quoted strings with spaces.
    -   **Pipeline & Redirection Parsing**: The token list is then analyzed to identify pipes (`|`) and output redirection (`>` or `>>`), breaking the command line into a structured pipeline.
3.  **Execution (`pipeline.py`)**: The `CommandPipelineExecutor` takes the parsed structure and manages its execution:
    -   For each command in a pipeline, a new `Context` is forked.
    -   `stdin` and `stdout` streams of these contexts are connected using in-memory `StringIO` buffers to create pipes.
    -   For redirection, the `stdout` of the final command is connected to a file handle.
    -   Each command is registered with the `ProcessManager`, assigned a PID, and executed.
    -   Finally, the command's name is resolved to an executable file in the filesystem (`/bin`, `/sbin`) and dispatched. Python commands (`.py`) have their `iocall` function invoked, while `skrip` files are executed by the `skrip` interpreter.

## 3. The Filesystem

IOSK uses a virtual filesystem that mirrors the standard UNIX hierarchy. All paths are sandboxed within a root directory specified at startup.

-   `/bin`: Contains all standard user commands.
-   `/sbin`: Contains system administration and lifecycle commands (`init`, `shutdown`).
-   `/etc`: Holds system-wide configuration files, including:
    -   `skrc`: A system-wide startup script run for every user.
    -   `hostname`: The network name of the IOSK instance.
    -   `motd/`: A directory of "Message of the Day" files, one of which is randomly displayed on login.
    -   `preamble`/`postamble` files for `ask` and `chat` that shape AI prompts.
-   `/dev`: A virtual directory for devices. AI models are exposed as files here (e.g., `/dev/google/gemini-2.5-pro`, `/dev/openai/gpt-4o`), as is the local console (`/dev/console`).
-   `/home`: The base directory for user data. The `root` user's home is `/root`.
-   `/doc`: Project documentation.
-   `/var`: Variable data generated during system operation.
    -   `/var/code`: Destination for code blocks automatically saved from chat.
    -   `/var/log`: System and trip trace logs.
    -   `/var/room`: Persistent state for chat rooms (owner, topic, etc.).
-   `/bank`: A virtual location for "memory banks"—skrips that, when executed via the `bank` command, load rules, personas, and instructions into an AI's context.

## 4. The Command System

IOSK provides a comprehensive set of UNIX-like commands, implemented as either Python modules (`.py`) or `skrip` files. All commands support a `--help` flag for detailed usage information.

### Command Categories

-   **File & Directory Management**: `ls`, `cat`, `cd`, `cp`, `mv`, `rm`, `mkdir`, `rmdir`, `pwd`, `touch`, `tree`, `diff`, `patch`, `replace`.
-   **Viewing & Analyzing Files**: `head`, `tail`, `wc`, `grep`, `search`, `describe`.
-   **Process & System Management**: `ps`, `kill`, `top`, `status`, `uptime`, `shutdown`, `ver`, `date`, `hostname`, `sleep`, `trace`, `system`.
-   **Shell & Command Environment**: `alias`, `export`, `history`, `skrip`, `which`, `xargs`, `help`.
-   **AI & User Management**:
    -   `ask`: Performs a one-shot query to an AI model with optional file/directory context.
    -   `bank`, `banks`, `bankrupt`, `clbank`: Manage the AI's core memory banks.
    -   `attach`, `detach`, `reattach`: Manage the lifecycle of AI agents.
    -   `pause`, `unpause`: Control an agent's active engagement.
    -   `tokens`, `forget`, `rolling`, `clear`, `reset`: Manage AI session history and context size.
    -   `who`, `whoami`, `users`, `login`, `su`: Standard user management utilities.
-   **Networking & Chat**:
    -   `port`, `mesh`, `unmesh`: Control the network server and peer-to-peer mesh connections.
    -   `on`: Execute a command on a remote host in the mesh.
    -   `where`, `whereami`: Discover users and hosts on the network.
    -   `room`, `rooms`, `clroom`, `topic`: Manage collaborative chat rooms.
    -   `send`, `color`, `colors`: Send file contents to chat and manage user display colors.

## 5. AI & Chat Interaction

The conversational aspect of IOSK is managed by the `AIMessenger` and `Engagement` classes, which form a sophisticated system for interacting with AI models.

-   **`AIMessenger` (`chat.py`)**: The central chat server. It manages user connections (`join`, `leave`), message routing (broadcasts and Direct Messages), and the lifecycle of chat rooms.
-   **`Engagement` (`chat.py`)**: Represents a single AI agent's active session. It runs an asynchronous `engage()` loop that decides when to trigger an AI "trip" based on timing parameters (e.g., idle time, wait time).

### 5.1. Prompt Construction

When an `Engagement` decides to query its AI model, it constructs a detailed prompt from several sources to provide rich context:
1.  **Preamble (`/etc/chat/preamble`)**: A script that runs to provide static, system-level instructions and information at the top of the prompt.
2.  **Banks**: The contents of all loaded memory banks are injected, providing the AI with its core rules, persona, and task-specific knowledge.
3.  **Session History**: The entire structured chat history for the session is included.
4.  **Postamble (`/etc/chat/postamble`)**: A final script that runs to add last-minute instructions, system status, and the final prompt cursor (e.g., `[user #1 /] >>`).

### 5.2. Automated Actions

IOSK is designed to make AI interactions seamless and powerful by automating common tasks:
-   **Auto-Save Code Blocks**: Any Markdown code block an AI generates is automatically saved to a unique file in `/var/code`. A notification is printed only to the AI's own session, keeping the main chat clean.
-   **Auto-Patch `diff` Blocks**: If the code block is a `diff`, the system intelligently extracts the target filename and automatically runs the `patch` command to apply the changes.

## 6. Networking & Multi-User Environment

IOSK is a fully networked OS, capable of communicating with GUI clients and other IOSK instances.

-   **`PortManager` (`port.py`)**: The heart of the network stack. It runs a WebSocket server that listens for two types of connections:
    1.  **Clients**: GUI applications like SKYBOARD connect as clients. The `PortManager` handles authentication and message passing between the client and the user's session.
    2.  **Peers**: Other IOSK systems connect as peers, forming a distributed "mesh."
-   **The Mesh**: A peer-to-peer network where connected IOSK instances share state information, including online users and active chat rooms. This enables cross-system chat and remote command execution via the `on` command.
-   **Client Protocol (`web.py`)**: The `web.py` module contains handlers for all messages from a GUI client. It exposes the IOSK backend functionality—such as file browsing (`fs_list`), file reading (`fs_read`), and context inspection—over the WebSocket protocol, using a simple `SK1:JSON` format.
-   **Chat Rooms**: To facilitate collaboration, users can create and join chat rooms. A room is a private communication channel where messages are broadcast only to its members. The system supports one active room per IOSK instance, but users can move between rooms on different hosts across the mesh.

## 7. The SKYBOARD Frontend

While IOSK can be run from a local terminal, its primary user interface is **SKYBOARD**, a sophisticated, web-based desktop environment built with Svelte 5.

-   **Desktop Metaphor**: SKYBOARD emulates a traditional desktop with a taskbar, start menu, and draggable, resizable windows.
-   **Workspace Management**: A feature called "Dash" allows users to save and restore entire window layouts, preserving application states for different tasks.
-   **IOSK Applications**: It includes a suite of applications for interacting with an IOSK backend:
    -   **`IoskConsole`**: A powerful terminal for direct command-line interaction.
    -   **`IoskFileExplorer`**: A graphical file browser with tree and tile views.
    -   **`IoskFileViewer`**: A viewer for remote files with support for Markdown and syntax highlighting.
    -   **`IoskContextInspector`**: A developer tool for inspecting the internal state of AI agents.
-   **Local Backend Integration**: SKYBOARD can also connect to a local backend service (`sk local`) to provide a local terminal and file browser, bridging the gap between the remote IOSK environment and the user's own machine.

