# Proposal: Connections & Box Context Menus

**Author:** LANNOCC
**Date:** 12/17/2025
**Status:** Draft

## 1. Introduction & Motivation

The SKYBOARD taskbar currently features two primary action buttons: a yellow "Dash" button (`&mdash;`) and a green "Context Quick View" button (`&#9632;`). While functional, their utility is limited. The Dash is a powerful feature but better suited to a keyboard-centric workflow, and the Quick View provides minimal context.

This proposal outlines a plan to overhaul these two buttons, transforming them into powerful, context-aware menus that streamline common user workflows and provide at-a-glance visibility into the state of the SideKick environment.

1.  The **yellow Dash button** will become a **Connections Menu**, providing a centralized dashboard for managing bridge-launched `iosk` processes and active frontend connections.
2.  The **green Quick View button** will become a **Box Menu**, acting as a dynamic "start menu" for the currently active workspace (Box), offering quick access to its tools and, for `iosk` boxes, a live view of its collaborative state.

These changes will significantly enhance the usability of SKYBOARD by making process management more accessible and creating a tighter, more intuitive link between a Box and its associated tools and resources. Foundational to this work is a refactoring of `iosk` connection management into a centralized, persistent service, a concept detailed in the next section.

## 2. Architectural Shift: Centralized Connection Management

To support persistent `iosk` sessions and provide a single source of truth for connection state across the entire UI, the underlying connection management logic will be refactored and centralized. Currently, each `IoskConsole` instance manages its own WebSocket connection. This will be changed so that connections are managed globally, and UI components like `IoskConsole` act as viewers or interfaces to these managed connections.

This architectural shift allows a user to close an `IoskConsole` window without terminating the underlying session. They can later open a new console and re-attach to the still-running session, complete with its command history and output buffer. This creates a more robust, flexible, and user-friendly experience for managing `iosk` connections, fully realizing the goal of a persistent, session-based environment.

## 3. The New Connections Menu (Yellow Button)

The yellow button will be repurposed to open a "Connections Menu". This menu serves as a quick-access control panel for all `iosk`-related activities, both backend and frontend. The "Dash" functionality will remain fully accessible via its existing keyboard shortcut (`Alt/Meta + Escape`).

The menu will be organized into two distinct sections:

### 3.1. Managed IOSK Processes

This section lists all `iosk` processes launched and managed by the SKYBRIDGE backend, sourced from the `$runningProcesses` store.

*   **Display**: Each entry will show:
    *   The associated Box name (e.g., "AI Agent Testbed").
    *   The process ID (PID).
    *   A colored status indicator (`Running`, `Paused`).
*   **Actions**: Each entry will have quick-action buttons for lifecycle management:
    *   **Pause/Resume**: A toggle button to send a `SIGSTOP`/`SIGCONT` signal to the process.
    *   **Stop**: A button to gracefully terminate the process (`SIGTERM`). This will be the primary action. A long-press or right-click could offer a "Kill" (`SIGKILL`) option for unresponsive processes.
*   **Footer**: A button to "Open Process Manager" which launches the full `Processes` board.

### 3.2. Active Frontend Connections

This section lists all active `IoskConsole` WebSocket connections currently open in the SKYBOARD UI. This is crucial for managing connections to remote or non-managed `iosk` instances.

*   **Display**: Each entry will show:
    *   The connection string (e.g., `root@ws://10.0.1.5:4209`).
    *   The title of the `IoskConsole` tab where the connection is active.
*   **Actions**:
    *   **Focus**: Clicking the entry will focus the corresponding `IoskConsole` window and tab.
    *   **Disconnect**: A button to programmatically close the WebSocket connection for that console.

## 4. The New Box Menu (Green Button)

The green button will be repurposed as a context-aware "Box Menu". Its content changes based on the currently active virtual desktop (`$currentBox`). It replaces the previous "Context Quick View" entirely.

### 4.1. For All Box Types

*   **Header**: Displays the name of the current Box (e.g., "My Project").
*   **Quick Launchers**: Buttons to launch core tools scoped to the Box's context path (`box.context`):
    *   **Files**: Opens a `LocalFileExplorer` with `initialPath` set to the box's path.
    *   **Terminal**: Opens a `LocalTerminal` with `initialPath` set to the box's path.

### 4.2. Additional Features for `iosk` Boxes

When the active Box is of type `iosk`, the menu is enhanced with tools and live data related to its managed `iosk` instance.

*   **Additional Launchers**:
    *   **IOSK Files**: Opens an `IoskFileExplorer` connected to the box's `iosk` instance.
    *   **Console**: Opens a new `IoskConsole` tab connected to the box's `iosk` instance.
*   **Live Users Panel**: A compact, embedded version of the `IoskConsole` users panel, providing a live view of the collaborative state.
    *   **User List**: Shows all human and AI agent users currently in the `iosk` room.
    *   **Status**: Displays `(paused)` status next to paused agents.
    *   **Token Stats**: For AI agents, shows basic token usage (e.g., cumulative input tokens). Hovering over the stats reveals a detailed tooltip with a full breakdown, identical to the one in `IoskConsole`.
    *   **Quick Actions**:
        *   Clicking a user's name opens a private chat (`IoskPrivateChat`).
        *   A "pause/resume" icon appears next to agents, allowing for quick state toggling.
        *   An "inspect" icon appears, which launches the `IoskUserInspector` for that user.

## 5. IOSK Box Configuration Enhancements

To support these new features and provide more granular control, the `IOSK` configuration tab within the `Boxes` board will be extended.

1.  **Port**: A new setting to control the network port for the `iosk` instance. This will be passed to the `iosk` process via the `-p` command-line flag.
    *   **Managed (Default)**: The SKYBRIDGE backend automatically finds and assigns a unique, available port when the process starts.
    *   **Custom**: The user specifies a fixed port number. The backend will attempt to use it but will fail if it's unavailable.
    *   **None**: No `-p` flag is passed, and `iosk` uses its own internal default.
2.  **Default Username**: A text field to specify the default username to use when connecting to this `iosk` instance via the "Console" quick-launcher in the Box Menu.

## 6. Implementation Plan

### 6.1. Backend (`sk/bridge.py`)

1.  **Database Schema**:
    *   Modify the `iosk` table in `skybridge.db` to include `port_mode TEXT`, `port_number INTEGER`, and `default_username TEXT`.
    *   Modify the `process` table to include `port INTEGER`.
2.  **Process Launching (`handle_start_iosk`)**:
    *   When a `start_iosk` message is received, query the new `iosk` table columns.
    *   Implement port selection logic:
        *   If `port_mode` is `managed`, find an open port on the host system.
        *   If `port_mode` is `custom`, use `port_number`.
    *   If a port is determined, add the `-p <port>` argument to the `iosk` subprocess command.
    *   Save the chosen port number into the new `port` column of the `process` table when creating the process record.
3.  **API Expansion**:
    *   Update the `update_iosk_config` handler to accept and save the new `port_mode`, `port_number`, and `default_username` fields.
    *   Update `get_iosk_config` to return these new fields.
    *   Modify the `running_processes_list` broadcast to include the `port` from the `process` table.

### 6.2. Frontend (`sv/`)

The core of the frontend work is centralizing all WebSocket connection logic into `sv/iosk.js`. All other components will be refactored to interface with this new service.

1.  **`sv/iosk.js` (The Connection Hub)**
    *   **New Store (`$activeIoskConnections`)**: A new writable store will track all active connections. This will be a map where keys are a unique `connectionId` (e.g., `root@ws://localhost:4209`) and values are objects containing the full state of that connection:
        *   The `WebSocket` instance itself.
        *   Connection status (`connecting`, `connected`, `error`, `disconnected`).
        *   All state previously held by `IoskConsole`: `output`, `commandHistory`, `currentPrompt`, `roomName`, `roomTopic`, `motd`, `roomParticipants`, `userColors`, `userTokenStats`, etc.
    *   **New Management Functions**:
        *   `initiateConnection(url, username)`: Creates a new WebSocket, adds a state object to `$activeIoskConnections`, and attaches event listeners. The `onmessage` handler will parse incoming `SK1:` messages and update the relevant connection's state in the store, and dispatch events to other stores (`privateMessages`, `fileSystemResponses`) with the `connectionId` included in the payload.
        *   `disconnect(connectionId)`: Gracefully closes the specified WebSocket and removes its entry from the `$activeIoskConnections` store.
        *   `sendCommand(connectionId, command)`: Sends a command string through the specified connection's WebSocket.
        *   `sendRequest(connectionId, request)`: A generic function for sending structured requests (like `fs_list` from `IoskFileExplorer` or `exec_command` from `IoskWatch`).

2.  **`sv/board/IoskConsole.svelte`**:
    *   Refactor heavily to be a "dumb" viewer for a centrally managed connection.
    *   It will take a `connectionId` prop and derive its entire display reactively from the corresponding entry in the `$activeIoskConnections` store.
    *   It will no longer hold a `ws` instance or manage its own state.
    *   The initial screen will show a list of active connections (from `$activeIoskConnections`) to attach to, plus an option to establish a new one.
    *   UI actions ("Connect", "Disconnect", command input) will now call the centralized functions in `sv/iosk.js` (`initiateConnection`, `disconnect`, `sendCommand`).
    *   Refactor the user list UI into a separate, reusable component (`IoskUsersList.svelte`) for use in the Box Menu.

3.  **`sv/board/IoskUserInspector.svelte`**:
    *   Refactor to remove the `consoleWs` prop and replace it with a `connectionId` prop.
    *   All functions that currently send data over the WebSocket (e.g., `togglePause`, `sendInspectorCommand`) will be updated to call `iosk.sendCommand(connectionId, command)`.
    *   The `onDestroy` logic will be simplified; it will no longer need to send an `ui_context_unsubscribe` message, as this can be managed by `sv/iosk.js` based on how many components are inspecting a given user.

4.  **`sv/board/IoskPrivateChat.svelte`**:
    *   Refactor to remove the `consoleId` prop and replace it with a `connectionId` prop.
    *   The `sendMessage` function will be updated to call `iosk.sendCommand(connectionId, command)` instead of setting the `consoleCommands` store.

5.  **`sv/board/IoskWatch.svelte`**:
    *   Refactor to remove the `consoleId` prop and replace it with a `connectionId` prop.
    *   The `sendWatchRequest` function will be updated to call `iosk.sendRequest(connectionId, request)` instead of setting the `fileSystemRequests` store.

6.  **`sv/board/Boxes.svelte`**:
    *   On the "IOSK" tab, add new UI controls: radio buttons for `port_mode`, a number input for `port_number`, and a text input for `default_username`.
    *   Update `handleConfigChange` to bundle these new values into the `update_iosk_config` message.
    *   Enhance the status display to show the assigned port number for running processes.

7.  **`sv/apps.js`**:
    *   Launchers for `newLocalFileExplorer` and `newLocalTerminal` can be used directly.
    *   Launchers for all `iosk`-related apps (`IoskConsole`, `IoskFileExplorer`, `IoskUserInspector`, `IoskPrivateChat`, `IoskWatch`) will be updated to accept a `connectionId` to interface with the correct session.

8.  **`sv/Taskbar.svelte`**:
    *   **Connections Menu (Yellow Button)**:
        *   Create a new dropdown component subscribing to `$runningProcesses` for the "Managed Processes" list and `$activeIoskConnections` for the "Active Connections" list.
        *   The "Disconnect" action will call `iosk.disconnect(connectionId)`.
        *   The "Focus" action will check if a console window is already viewing that `connectionId`. If so, it focuses it. If not, it launches a new `IoskConsole` with the `connectionId` prop set, attaching a new viewer to the existing session.
    *   **Box Menu (Green Button)**:
        *   Create a new dropdown component reactive to `$currentBox`.
        *   Implement quick-launch buttons calling launchers from `sv/apps.js`.
        *   For `iosk` Boxes, determine the active `connectionId` by finding the running process for the box in `$runningProcesses` and constructing the connection URL from its `port`.
        *   Refactor the user list from `IoskConsole.svelte` into a reusable component that takes its props from the relevant entry in `$activeIoskConnections`.

