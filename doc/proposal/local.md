# Proposal: Local Function Integration in SKYBOARD

**Author:** LANNOCC
**Date:** November 13, 2025
**Status:** Implemented

## 1. Introduction & Motivation

The SideKick web interface provides a powerful, multi-user, sandboxed environment through the IOSK kernel. This environment is intentionally isolated and designed for AI agent collaboration, script execution, and interaction within a secure virtual filesystem.

However, as a primary developer and operator interface, its utility can be greatly enhanced by providing seamless access to the user's *local* machine. Currently, switching between the web UI for IOSK tasks and a local terminal or file browser for development work is a disjointed experience.

This proposal outlines a strategy to integrate local system functions directly into the SideKick web UI, which we will henceforth refer to as **SKYBOARD**.

The core principle of this proposal is to maintain the strict separation and integrity of the IOSK sandbox. The IOSK backend will **not** be modified. Instead, we will introduce a new, parallel service that bridges the SKYBOARD frontend with the local host environment.

## 2. Core Requirements

The initial implementation will focus on two essential local functions:

1.  **Local Terminal:** A terminal window component within SKYBOARD that provides a direct shell session (e.g., `bash`) on the user's local machine.
2.  **Local File Browser:** A file explorer component within SKYBOARD for browsing, viewing, and potentially managing files on the user's local filesystem.

## 3. Proposed Architecture

We will introduce a new backend service, the `sk-local-agent`, which runs on the user's machine and communicates with the SKYBOARD frontend over a dedicated WebSocket connection, entirely separate from the IOSK connection.

### 3.1. Backend: `sk-local-agent`

This will be a new Python-based service responsible for exposing local resources securely.

-   **WebSocket Server:** The agent will start a WebSocket server on a distinct port (e.g., `localhost:4210`) to avoid conflicts with IOSK. Access will be restricted to `localhost` by default for security.
-   **Local Terminal Implementation:**
    -   Upon a request from the frontend, the agent will use Python's `pty` module to spawn a pseudo-terminal.
    -   A user-specified shell (defaulting to `bash`) will be launched as a child process of the pty.
    -   The agent will then act as a bidirectional bridge, relaying data between the WebSocket and the pty file descriptor, effectively creating a fully interactive terminal session in the browser.
-   **Local File System API:**
    -   The agent will expose a simple JSON-based API over the WebSocket for filesystem operations. This avoids exposing a raw shell and provides a structured interface.
    -   Example messages:
        -   **List:** `{"type": "fs_list", "path": "/path/to/dir"}`
        -   **Read:** `{"type": "fs_read", "path": "/path/to/file"}`
    -   The backend will use standard Python libraries (`os`, `pathlib`) to interact with the filesystem, running with the permissions of the user who launched the agent.

### 3.2. Frontend: SKYBOARD (Svelte)

-   **New Components:** We will create `LocalTerminal.svelte` and `LocalFileExplorer.svelte` components. These will be integrated into our existing windowing system (`windows.js`), allowing them to be opened, moved, and managed like any other window.
-   **Connection Management:** The frontend will be updated to manage a second WebSocket connection to the `sk-local-agent`. A connection manager will route messages to the appropriate component (IOSK or Local).
-   **UI Integration:** New options will be added to the "Start Menu" in the `Taskbar` to launch the "Local Terminal" and "Local Files" windows.

This architecture is illustrated below:

```
+-------------------------------------------------------------+
|                     SKYBOARD (Web Browser)                    |
| +---------------------+      +----------------------------+ |
| | LocalTerminal.svelte|      | IoskConsole.svelte         | |
| +---------|-----------+      +-------------|--------------+ |
+-----------|--------------------------------|----------------+
            | (ws://localhost:4210)          | (ws://localhost:4209)
            |                                |
+-----------V-----------+      +-------------V--------------+
|   sk-local-agent      |      |   sk-iosk (IOSK Kernel)    |
|  (Python Service)     |      |    (Python Service)        |
| +-------------------+ |      +--------------------------+ |
| | pty bridge (bash) | |      | Sandboxed Filesystem     | |
| | Local FS API      | |      | AI Agent Engagements     | |
| +-------------------+ |      +--------------------------+ |
+-----------|-----------+      +----------------------------+
            |
+-----------V-----------+
|  Local Host System    |
| (Filesystem, Shell)   |
+-----------------------+
```

## 4. Security Considerations

The `sk-local-agent` provides powerful access to the user's machine. Security is paramount.

-   **Localhost Binding:** The WebSocket server will bind to `127.0.0.1` by default, preventing any access from the network.
-   **User Permissions:** The agent runs with the permissions of the logged-in user. It cannot perform any action that the user could not already perform in a standard terminal. No privilege escalation is involved.
-   **No Authentication:** For a `localhost`-only service, explicit authentication is not required for the initial implementation.

## 5. Future Vision: The SKYBOARD Platform

The name **SKYBOARD** reflects our vision for this interface: a central command center for developers and AI agents. The "SK" links it to SideKick, "cyborg" hints at the human-AI integration, and "board" signifies its role as the ultimate dashboard.

With the local integration architecture in place, we can expand SKYBOARD's capabilities:

-   **`ask` and `task` Integration:**
    -   A dedicated panel or window type can provide a GUI for the `ask` and `task` commands.
    -   Users could type a prompt and use the new Local File Explorer to visually select files or directories to package with the `-p` option.
    -   The `sk-local-agent` would execute the `sk ask` or `sk task` command as a subprocess and stream the results back to the SKYBOARD UI for display.

-   **"Installing" on SKYBOARD:**
    The concept of "installing" on SKYBOARD does not refer to traditional applications. It means extending the SKYBOARD environment itself with new, SideKick-centric functionality.
    -   **Agent Scripts:** Users could "install" agent scripts—collections of prompts, configurations, and helper files. These would appear as new, one-click actions in the `task` UI, abstracting away complex command-line invocations for repeatable tasks.
    -   **Local Tool Plugins:** We can design a simple plugin architecture for the `sk-local-agent`. A user could "install" a new tool by providing a Python backend script and a Svelte component. For example, a system monitoring tool could use `psutil` on the backend and display real-time graphs in a new SKYBOARD window type. Installation would simply mean placing these files in a designated local directory that the agent scans at startup.

## 6. Conclusion

By introducing a dedicated `sk-local-agent`, we can significantly enhance the SKYBOARD interface without compromising the integrity of the IOSK sandbox. This proposal provides a clear path to integrating essential local tools like a terminal and file browser, and establishes a foundation for transforming SKYBOARD into a truly comprehensive and extensible platform for AI-assisted development and operations.

