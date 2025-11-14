# Proposal: Real-Time Filesystem Events and Streaming for SKYBOARD

**Author:** LANNOCC
**Date:** November 14, 2025
**Status:** Draft

## 1. Introduction & Motivation

The SKYBOARD interface provides a powerful window into the sandboxed IOSK environment. However, its current file system interactions are static and follow a request-response model. When a user opens a directory in `IoskFileExplorer`, they see a snapshot in time. Any subsequent changes made by an AI agent or another user—such as creating a log file or updating a script—are invisible until the user manually refreshes the view. Similarly, `IoskFileViewer` loads an entire file into memory, which is inefficient for large files and provides no way to monitor files that are actively being written to, such as logs.

This proposal outlines a plan to introduce a dynamic, event-driven layer to SKYBOARD's file system components. We will implement features for:
1.  **Live Directory Watching:** To see file changes in `IoskFileExplorer` as they happen.
2.  **Live File Tailing:** To stream appended content in `IoskFileViewer`, similar to `tail -f`.
3.  **Incremental File Loading:** To efficiently view and inspect large files by loading them in chunks on demand.

These enhancements will transform SKYBOARD from a static file browser into a live monitoring and diagnostics tool, making it significantly more useful for development, debugging, and observing AI agent activity.

## 2. Core Requirements

1.  **Directory Watching:**
    *   An opt-in "Watch" feature in `IoskFileExplorer` shall be implemented.
    *   When active, the view must update in real-time to reflect file/directory creations, deletions, and modifications within the currently viewed directory.
2.  **File Tailing:**
    *   An opt-in "Follow" feature in `IoskFileViewer` shall be implemented.
    *   When active, the viewer must automatically scroll and display new content as it is appended to the file, making it ideal for monitoring log files.
3.  **Chunked File Loading:**
    *   `IoskFileViewer` must be modified to load large files incrementally.
    *   An initial chunk of the file will be loaded, and subsequent chunks will be fetched on demand as the user scrolls. This applies to both text and hex view modes.
4.  **Backend Efficiency:**
    *   The backend implementation must be efficient, using asynchronous tasks and modern libraries to handle potentially numerous watchers and tailers without blocking the main kernel loop.
    *   Resources (watchers, tasks) must be automatically cleaned up when a client disconnects.

## 3. Proposed Architecture

The implementation will involve adding a new backend dependency, extending the WebSocket protocol between IOSK and SKYBOARD, and updating the relevant Svelte components.

### 3.1. Backend (IOSK Kernel)

The core of the backend changes will be managed within `iosk/port.py`, as it is responsible for client connections.

#### 3.1.1. New Dependency: `watchdog`

To monitor the filesystem efficiently, we will introduce the `watchdog` library as a new Python dependency. It provides a cross-platform, high-performance API for observing filesystem events.

#### 3.1.2. FS Watch & Tail Management

The `PortManager` will be extended to manage filesystem watchers and file tailing tasks.
*   **Registries:** Two new dictionaries will be added to `PortManager`:
    *   `self.active_watchers`: Maps a tuple `(websocket, path)` to a `watchdog` observer instance.
    *   `self.active_tailers`: Maps a tuple `(websocket, path)` to an `asyncio.Task` instance.
*   **Lifecycle Management:** The `_cleanup_and_propagate_disconnect` method will be updated to iterate through these registries and terminate any observers or tasks associated with the disconnected websocket.

#### 3.1.3. New & Modified WebSocket Protocol

We will introduce new message types for controlling these features. All messages will be sent over the existing `SK1:` protocol.

**Client-to-Server Messages:**

*   `{"type": "fs_watch_start", "path": "/path/to/dir"}`: Initiates watching on a directory. The backend will start a `watchdog` observer.
*   `{"type": "fs_watch_stop", "path": "/path/to/dir"}`: Stops the watcher for the given path.
*   `{"type": "fs_tail_start", "path": "/path/to/file"}`: Initiates "tailing" on a file. The backend will spawn an `asyncio` task to monitor the file for appends.
*   `{"type": "fs_tail_stop", "path": "/path/to/file"}`: Stops the tailing task.
*   `{"type": "fs_read", "path": "/path", "offset": 0, "length": 16384}`: The existing `fs_read` message will be enhanced with optional `offset` and `length` parameters for chunked reading.

**Server-to-Client Messages:**

*   `{"type": "fs_watch_update", "path": "/path/to/dir", "event_type": "created", "affected_path": "/path/to/dir/new.txt", "is_dir": false}`: Sent when a filesystem event occurs in a watched directory.
*   `{"type": "fs_tail_update", "path": "/path/to/file", "data": "new log line\n"}`: Sent when new data is appended to a tailed file.
*   `{"type": "fs_read_response", ..., "offset": 0, "length": 16384, "total_size": 1048576}`: The response will echo the request parameters and include the total file size so the client can calculate progress.

#### 3.1.4. Implementation Sketch (in `port.py`)

*   **Tailing Task:** The async function for tailing a file will look roughly like this:
    ```python
    async def _tail_file_task(self, websocket, io_context, path):
        host_path = self.kernel.box(path, io_context=io_context)
        with open(host_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2) # Seek to end
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                # Send update to client
                payload = {"type": "fs_tail_update", "path": path, "data": line}
                await self.send_payload_to_client(io_context.user, payload)
    ```
*   **Chunked Reading:** `_handle_fs_read` will be updated to use `offset` and `length` when opening and reading the file, and will add `total_size` to the response payload.

### 3.2. Frontend (SKYBOARD)

The frontend will require UI additions and logic to manage the state of these new features.

#### 3.2.1. `IoskFileExplorer.svelte`

*   A "Watch" button will be added to the toolbar.
*   Clicking "Watch" sends the `fs_watch_start` message for the `currentPath`. The button will enter an "active" state.
*   A new WebSocket message handler (via a new `fileSystemWatchEvents` store in `ioskEvents.js`) will listen for `fs_watch_update` messages.
*   Upon receiving a relevant update, the component will simply re-trigger its `requestPath` function to refresh the entire directory listing. This is simpler and more robust than attempting to patch the local list of items.
*   Clicking the "Watch" button again will send `fs_watch_stop` and deactivate the feature.

```
+-------------------------------------------------------------+
| IoskFileExplorer.svelte UI                                  |
+-------------------------------------------------------------+
| [^] [/var/log] [Watch 👀]                                   |  <-- New "Watch" button
| ----------------------------------------------------------- |
| 🗂️ ..                                                       |
| 📄 system-2025-11-13.log                                    |
| 📄 user/root/2025-11-13.log                                 |
|                                                             |
| << An AI agent creates a new file... >>                     |
|                                                             |
| << Backend sends fs_watch_update event >>                   |
|                                                             |
| << Component re-requests /var/log >>                        |
|                                                             |
| 🗂️ ..                                                       |  <-- View updates automatically
| 📄 agent-alpha.log (new)                                    |
| 📄 system-2025-11-13.log                                    |
| 📄 user/root/2025-11-13.log                                 |
+-------------------------------------------------------------+
```

#### 3.2.2. `IoskFileViewer.svelte`

*   **Tailing:** A "Follow" button will be added to the toolbar. Clicking it sends `fs_tail_start` and `fs_tail_stop`. A new event store will deliver `fs_tail_update` messages, whose `data` will be appended to the viewer's content, with the view scrolled to the bottom.
*   **Chunking:**
    *   The file loading logic will be refactored. On mount, it will request only the first chunk (e.g., 16KB).
    *   The component will store `content_bytes`, `total_size`, and the current `loaded_size`.
    *   A scroll event listener will be attached to the content area.
    *   When the user scrolls near the end of the currently loaded content (`scrollTop + clientHeight >= scrollHeight - buffer`), and `loaded_size < total_size`, a request for the next chunk will be sent with the correct `offset`.
    *   The incoming chunk data will be appended to `content_bytes`, causing the view (both text and hex) to update.

## 4. Conclusion

Implementing real-time filesystem events and streaming will significantly enhance SKYBOARD's capabilities, evolving it from a static interface into a dynamic, responsive environment. These features are crucial for effectively monitoring logs, observing AI agent behavior, and efficiently handling large files. The proposed architecture leverages industry-standard tools like `watchdog` and robust `asyncio` patterns on the backend, while providing a clean, user-controlled experience on the frontend. This will solidify SKYBOARD's position as an indispensable tool for advanced development and operations within the SideKick ecosystem.

