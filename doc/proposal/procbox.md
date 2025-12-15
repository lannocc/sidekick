# ProcBox: IOSK Process Management and Box Integration

**Author**: LANNOCC
**Date**: 12/14/2025
**Status**: Proposed

## Abstract

This proposal outlines a plan to integrate the launching, management, and monitoring of `iosk` instances directly within the SKYBOARD desktop environment. Currently, `iosk` instances can be run independently and connected to, but this proposal seeks to make `iosk` a first-class, managed entity within SKYBOARD. This will be achieved by upgrading "Boxes" to represent either local directory contexts or full `iosk` sandboxes. The SKYBRIDGE backend will be enhanced to manage the lifecycle of these `iosk` processes, and the frontend will be updated with new UI components for control, monitoring, and interaction.

## Motivation

The `iosk` system provides a powerful sandboxed environment for AI agents and tasks. By integrating its management directly into SKYBOARD, we can create a more seamless and powerful workflow for users. Key benefits include:

*   **Centralized Management**: Users can start, stop, and monitor `iosk` instances directly from the SKYBOARD UI, without needing to drop to a separate terminal.
*   **Enhanced Boxes**: The "Box" concept becomes more powerful, evolving from a simple directory shortcut into a configurable, runnable sandbox environment.
*   **Process Visibility**: A dedicated "Processes" board will provide insight into what the backend is running, starting with `iosk` and extensible to other process types in the future.
*   **Improved UX**: Promoting a local directory Box to a runnable `iosk` instance becomes a simple, one-click action, lowering the barrier to entry for using `iosk`.

## Implementation Plan

The implementation will be divided into backend modifications (database and process management) and frontend UI/UX enhancements.

### 1. Backend Changes (`sk/bridge.py`)

The backend will be responsible for storing `iosk` configurations, launching/terminating processes, and relaying process information to the frontend.

#### 1.1. Database Schema Updates

We will introduce two new tables to `skybridge.db` and modify the `box` table's constraints.

1.  **Modify `box` table**: The `type` column will be updated to explicitly be one of `('local', 'iosk')`.

2.  **New Table: `iosk`**: This table will store configuration specific to `iosk` boxes, linked one-to-one with the `box` table.

    ```sql
    CREATE TABLE IF NOT EXISTS iosk (
        box_id INTEGER PRIMARY KEY,
        mount_point TEXT, -- The optional path for mounted media mode
        daemon_mode INTEGER NOT NULL DEFAULT 1, -- Boolean (0 or 1)
        enable_stdin INTEGER NOT NULL DEFAULT 0, -- Boolean (0 or 1), enables interactive stdin
        FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE
    );
    ```

3.  **New Table: `process`**: This table will track active processes launched by the bridge. It is designed to be extensible beyond just `iosk`.

    ```sql
    CREATE TABLE IF NOT EXISTS process (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        box_id INTEGER, -- Nullable for non-box-related processes
        pid INTEGER NOT NULL UNIQUE,
        type TEXT NOT NULL DEFAULT 'iosk', -- e.g., 'iosk', 'agent_task'
        start_time TEXT NOT NULL, -- ISO 8601 format
        status TEXT NOT NULL CHECK(status IN ('running', 'paused', 'stopped', 'error')),
        stdout_log_path TEXT NOT NULL,
        stderr_log_path TEXT NOT NULL,
        FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE SET NULL
    );
    ```

#### 1.2. Process Launching & Daemonization

The bridge will gain the ability to launch `iosk` as a subprocess. A key requirement is that these processes can optionally outlive the bridge itself (`daemon_mode`).

*   **Invocation**: The bridge will locate the `iosk` executable within the Python environment (similar to how it finds `ask`) and execute it. The `box.context` will be used as the `workspace_directory`.
*   **Detachment**:
    *   On POSIX systems, `subprocess.Popen` with the `start_new_session=True` argument will be used to run the process in a new session, detaching it from the bridge's lifecycle.
    *   On Windows, the `DETACHED_PROCESS` creation flag will be used to achieve a similar result.
    *   If `daemon_mode` is false, the process will be launched normally as a child of the bridge and will be terminated when the bridge exits.
*   **I/O Handling**:
    *   Standard output and error for each process will be redirected to dedicated log files in a temporary or user data directory. The bridge will tail these files to stream new output to the frontend.
    *   If the `enable_stdin` setting is true for an `iosk` process, it will be launched with its standard input connected to a pipe (`stdin=subprocess.PIPE`). The bridge will manage this pipe, writing data to it when it receives `process_stdin` messages from the frontend.

#### 1.3. WebSocket API Expansion

The following new message types will be added to the websocket protocol:

*   **Box Promotion**:
    *   `promote_to_iosk` -> `(box_id)`: Client requests to convert a 'local' box to an 'iosk' box. Backend changes `box.type` and creates a default `iosk` entry.
*   **IOSK Configuration**:
    *   `update_iosk_config` -> `(box_id, config)`: Client sends updated config (e.g., `mount_point`, `daemon_mode`, `enable_stdin`).
    *   `get_iosk_config` -> `(box_id)`: Client requests config for a box.
    *   `iosk_config_response` <- `(box_id, config)`: Backend sends config.
*   **Process Lifecycle**:
    *   `start_iosk` -> `(box_id)`: Client requests to start the `iosk` instance for a box.
    *   `stop_process` -> `(pid)`: Client requests to stop a running process.
    *   `pause_process` -> `(pid)`: Client requests to pause a process (SIGSTOP).
    *   `resume_process` -> `(pid)`: Client requests to resume a process (SIGCONT).
*   **Process Monitoring and Interaction**:
    *   `list_running_processes` -> `()`: Client requests a list of all managed processes.
    *   `running_processes_list` <- `(processes)`: Backend sends the list of processes from the `process` table.
    *   `process_output` <- `(pid, stream, data)`: Backend streams stdout/stderr data from a process's log file.
    *   `process_status_update` <- `(pid, status)`: Backend broadcasts status changes (e.g., 'running' -> 'stopped').
    *   `process_stdin` -> `(pid, data)`: Client sends a string of data to be written to the specified process's standard input.

### 2. Frontend Changes (`sv/`)

The frontend will be updated to expose the new process management capabilities through an intuitive user interface.

#### 2.1. Box Component (`sv/Box.svelte`)

The visual representation of a Box on the desktop will be enhanced.

*   **IOSK Badge**: A small `/iosk.png` badge will be overlaid on the corner of a Box icon if its `type` is `'iosk'`.
*   **Context Menu**:
    *   For Boxes of type `'local'`, a new context menu option "Promote to IOSK Box" will be added.
    *   This action will trigger the `promote_to_iosk` websocket message.

#### 2.2. Boxes Board (`sv/board/Boxes.svelte`)

The "Boxes" management window will be significantly updated.

*   **Tab Renaming**: The "General" tab will be renamed to "Properties".
*   **New "IOSK" Tab**:
    *   For any selected Box of type `'iosk'`, a new "IOSK" tab will appear as the first tab.
    *   The new "IOSK" tab should be the default tab for Box of type `'iosk'`.
    *   This tab will display:
        *   **Configuration**: Form fields to edit the `mount_point`, toggle `daemon_mode`, and toggle `enable_stdin`. Changes will be sent via `update_iosk_config`.
        *   **Status Display**: A section showing the current status (`Running`, `Stopped`), PID, and uptime.
        *   **Controls**: "Start" and "Stop" buttons that trigger `start_iosk` and `stop_process`.
        *   **Quick Link**: A button to "View in Process Manager" which will open the new `Processes.svelte` board and focus on this specific process.

#### 2.3. New Component: Processes Board (`sv/board/Processes.svelte`)

A new board for managing all backend-launched processes.

*   **Layout**: A two-pane layout. The left pane will list all running processes. The right pane will show details for the selected process.
*   **Process List**: Each item will show the process type (e.g., "IOSK"), associated Box name, PID, and status.
*   **Detail View**: For a selected process, this view will feature:
    *   A live, auto-scrolling terminal-like view for combined stdout/stderr. If standard input is enabled for the process, an input field will be included to allow interactive communication. Data sent from this field will be forwarded to the process's `stdin`.
    *   Detailed information (PID, start time, uptime, log file paths).
    *   Action buttons: "Pause", "Resume", "Terminate" (SIGTERM), and "Kill" (SIGKILL).

#### 2.4. Taskbar Quick-View (`sv/Taskbar.svelte`)

The currently unused green square button will be activated.

*   **Functionality**: Clicking the button will toggle a dropdown/popover menu.
*   **Content**: This menu will serve as a quick-glance dashboard, displaying:
    *   A list of all currently running `iosk` instances with their associated Box name and status.
    *   Quick action buttons next to each entry (e.g., a "Stop" button).
    *   A summary of currently open (actived) desktop (Box).
    *   A button at the bottom to "Open Process Manager".
    *   A button at the bottom to "Open Boxes Manager".

### 3. Command Line Interface (`sk/iosk/cmd.py`)

No significant changes are required for `sk/iosk/cmd.py`. It is already designed to be run as a standalone command, which fits the `subprocess.Popen` execution model perfectly. The backend will simply be responsible for constructing the correct command-line arguments (`iosk <workspace_directory> [<mount_point>]`) based on the Box's configuration.

## Future Considerations

This proposal lays the groundwork for a robust process management system. Future enhancements could include:

*   **Remote IOSK Instances**: Extending the system to manage `iosk` instances running on remote machines.
*   **Resource Monitoring**: Displaying CPU and memory usage for each managed process.
*   **Agent Process Management**: Integrating the launching and monitoring of autonomous agent tasks as managed processes.
*   **Process Templates**: Allowing users to define custom commands as "Process Templates" that can be launched and managed through the UI.
