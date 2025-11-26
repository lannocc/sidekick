# Proposal: Networked Filesystem Operations

**Status**: Proposed

### Introduction

Currently, IOSK's filesystem operations are confined to the local host's sandboxed root directory. While the network mesh allows for real-time communication between users and agents on different systems, file sharing remains a manual process, typically involving piping file contents through the `send` command. This is inefficient for collaboration and limits the potential of a distributed, multi-system environment.

This proposal introduces a networked filesystem layer that extends core utilities (`ls`, `cp`, `mv`, `mkdir`, etc.) to operate seamlessly on remote hosts within the mesh. By adopting a simple, intuitive syntax similar to `scp`, users will be able to list, read, write, and manage files across any connected IOSK instance as if it were a local directory.

Crucially, this functionality will be exposed through the same kernel APIs used by local commands, ensuring that both command-line users and the web-based GUI (`IoskFileExplorer`) can leverage networked file operations without significant changes to their existing logic. This will transform the IOSK mesh from a collection of isolated systems into a truly collaborative, distributed operating environment.

### Core Concepts

1.  **Network Path Syntax**: We will adopt a syntax familiar to users of `scp` and `rsync` to address resources on remote hosts: `hostname:/path/to/resource`.
    *   `hostname`: The name of a connected peer system in the network mesh.
    *   `:`: The separator distinguishing the host from the path.
    *   `/path/to/resource`: An absolute virtual path on the remote host. Relative remote paths will not be supported initially to ensure clarity and simplicity.
    *   Any path *without* the `hostname:` prefix is treated as a local path.

2.  **RPC-Based Operations**: All networked file operations will be modeled as Remote Procedure Calls (RPCs) brokered by the `PortManager`. Instead of a complex new file transfer protocol, we will define a set of clear, task-oriented JSON messages (e.g., `netfs_list_request`, `netfs_get_request`, `netfs_put_request`). When a user on `host-A` runs `ls host-B:/`, `host-A`'s kernel sends an RPC to `host-B`, which executes the `ls` operation locally and sends the results back.

3.  **Unified Kernel Interface**: The kernel's core filesystem methods (`copy`, `move`, `list_dir`, `get`, `create`, etc.) will become network-aware. They will be the single point of entry for all file operations. These methods will be responsible for parsing path arguments, determining if an operation is local, remote, or mixed (local-to-remote), and dispatching the request to either the local filesystem handler or the `PortManager` for remote execution. This ensures that any command or system component using these kernel APIs automatically gains network capabilities.

4.  **Web Client Proxying**: The web client's file explorer will gain network access without requiring a direct connection to every peer. The client will send its requests (e.g., list `host-B:/tmp`) to its connected IOSK server. This server will act as a proxy, forwarding the request to the appropriate peer (`host-B`) via the mesh, and then relaying the response back to the web client. This maintains a simple and secure client-server architecture.

### Implementation Strategy

#### 1. Path Parsing Utility

A new helper function, `parse_path(path_str) -> (hostname, virtual_path)`, will be added to the kernel (`IOSK` class). It will be responsible for splitting a path string into its `hostname` and `virtual_path` components. If no hostname is present, it will return `(None, virtual_path)`.

#### 2. Kernel File Operation Modifications (`kernel.py`)

The core filesystem methods in the `IOSK` class will be updated to serve as dispatchers.

**Example: `IOSK.list_dir` modification:**
```python
# Conceptual change in src/iosk/kernel.py
async def list_dir(self, io: Context, path: str, **kwargs) -> list:
    hostname, virtual_path = self.parse_path(path) # New parsing step

    if not hostname or hostname == self.hostname:
        # --- Local Operation ---
        # Delegate to the local FileSystemManager
        return await self.fs.list_dir(io, path, **kwargs)
    else:
        # --- Remote Operation ---
        if not self.port:
            await io.error("!! netfs: network subsystem is not available.")
            return None
        # Delegate to PortManager to handle the remote request
        return await self.port.remote_list_dir(hostname, virtual_path, **kwargs)
```
This pattern of parsing and dispatching will be applied to `copy`, `move`, `get`, `get_raw`, `create`, `remove`, `create_dir`, `remove_dir`, and `exists`. For two-argument operations like `copy`, both source and destination paths will be parsed to determine the operation type (local-local, local-remote, remote-local, or remote-remote).

#### 3. Network Protocol and PortManager Extensions (`port.py` and `web.py`)

The `PortManager` will handle the lifecycle of remote filesystem requests.

1.  **New Public Methods**: New methods will be added to `PortManager` for the kernel to call, such as:
    *   `async def remote_list_dir(self, host, path)`
    *   `async def remote_get_file(self, host, path)`
    *   `async def remote_put_file(self, host, path, content_b64, is_binary)`
    These methods will construct the appropriate request message, send it to the target peer using `route_message`, and wait for a response. A system of `request_id`s and pending futures will be used to match responses to their original requests.

2.  **New Message Types**: A suite of `netfs_*` message types will be defined for the peer-to-peer protocol:
    *   `netfs_list_request` / `netfs_list_response`
    *   `netfs_get_request` / `netfs_get_response` (response contains file content)
    *   `netfs_put_request` / `netfs_put_response` (request contains file content)
    *   ... and corresponding messages for `mv`, `rm`, `mkdir`, `rmdir`, `describe`.

3.  **Message Dispatcher and Handler Update**: The `_dispatch_message` method in `src/iosk/port.py` routes message types to handler functions in `src/iosk/web.py`. New `handle_netfs_*` functions will be added to `web.py`. Upon receiving a request, these handlers will call the corresponding *local* kernel method (`port_manager.os.list_dir`, `port_manager.os.get_raw`, etc.) on behalf of the remote peer, and then send the result back in a response message.

#### 4. Web Client API Updates

The WebSocket API for the web client will be extended to proxy `netfs` requests.

1.  **`IoskFileExplorer.svelte`**:
    *   The UI will be updated with a mechanism (e.g., a dropdown or editable field) to select a remote host from the current mesh.
    *   When listing a directory, it will construct its `fs_list` request with the full path, including the `hostname:` prefix if a remote host is targeted.
    *   The logic for handling drag-and-drop between two explorer windows will be updated to construct the correct local and remote paths for the resulting `cp` or `mv` command.

2.  **`web.py` (`handle_fs_list`, `handle_fs_read`)**:
    *   These handlers in `src/iosk/web.py`, which process messages from the client, will be modified. They will use the new `parse_path` utility (from the kernel) on the requested path.
    *   If the path is local, they will function as they do now by calling the local kernel FS method.
    *   If the path is remote, they will call the appropriate `PortManager.remote_*` method (e.g., `remote_list_dir`) and forward the result to the client, ensuring the response format is identical to that of a local request. This makes the proxying transparent to the client.

#### 5. Command Updates (`bin/*.py`)

Because all file operations are abstracted through the kernel (`io.os.*`), the command implementations themselves require minimal changes. The primary update will be to their docstrings to inform users of the new `hostname:/path` syntax. For example, `cp --help` will be updated to show usage like `cp <source> <destination>`, where either path can be local or remote.

### Use Case Scenarios

**1. Command-Line File Transfer**
User `alpha` on `host-A` wants to copy a configuration file to `host-B`.
```
[alpha@host-A] $ cp /etc/my_app.conf host-B:/etc/my_app.conf
```
*   `host-A`'s kernel parses the `cp` command. It identifies the source as local and the destination as remote.
*   It calls `self.get_raw('/etc/my_app.conf')` to read the local file into memory.
*   It calls `self.port.remote_put_file('host-B', '/etc/my_app.conf', ...)` to send the data.
*   `host-B` receives the `netfs_put_request`, writes the file to its local sandbox, and returns a success response.
*   `host-A` prints `:: path copied` to `alpha`'s console.

**2. GUI-Based Remote Browsing and Transfer**
*   A user opens a File Explorer, which defaults to their local filesystem on `host-A`.
*   They open a second File Explorer. In its path bar, they enter `host-B:/home/guest` and press Enter.
*   The `fs_list` request is sent to `host-A`, which proxies it to `host-B`. `host-B` returns the directory listing, which `host-A` forwards to the client. The second explorer now shows the remote directory.
*   The user drags `local_file.txt` from the first explorer and drops it into the second.
*   The frontend determines the source (`/local_file.txt`) and destination (`host-B:/home/guest/local_file.txt`). It sends a request to the backend to execute the equivalent of `cp /local_file.txt host-B:/home/guest/local_file.txt`.
*   The backend `cp` command proceeds as in the command-line scenario. Both file explorers refresh to show the result.

### Benefits

*   **Seamless Integration**: Network operations feel like a native part of the filesystem, leveraging existing commands and APIs.
*   **Centralized Logic**: The complexity is contained within the kernel and `PortManager`, keeping user-facing commands simple.
*   **Unified Experience**: Both CLI and GUI users benefit from the same underlying functionality, providing a consistent experience across interfaces.
*   **Enhanced Collaboration**: Drastically simplifies sharing and managing files across a distributed network of IOSK systems, enabling more complex multi-agent and multi-user workflows.

