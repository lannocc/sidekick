# IOSK Networking Commands

### 1. Introduction

This document provides a detailed specification for the commands that enable the IOSK networking and multi-room architecture, as outlined in the `netroom.md` proposal. It details the usage and state management for new and modified commands that transform IOSK into a distributed, collaborative operating system.

These commands rely on a new set of kernel services and a standardized filesystem layout for storing network and room state.

### 2. Filesystem and State Management

To support persistent room configurations and network identity, the following filesystem conventions are introduced.

#### 2.1. The `/var/room` Directory

The `/var/room` directory serves as the persistent storage for all chat rooms that have been created on the local system. This allows room configuration to persist even when a room is not active.

*   **Structure**: Each room has its own subdirectory: `/var/room/<room_name>/`
*   **State Files**: Within each room's directory, the following state files may exist:
    *   `owner`: A plain text file containing the username of the user who created the room.
    *   `topic`: A plain text file containing a short, descriptive topic for the room, which can be set by the owner.
    *   `motd`: A file containing a "message of the day" that is displayed to users when they join the room.

Chat history logs will be stored in `/var/log/room/`.

#### 2.2. The `/etc/hostname` File

A new file, `/etc/hostname`, will store the unique name of the local IOSK system on the network. This name is used for addressing and identification (e.g., `lannocc.novamente`). If this file does not exist, the system will derive its hostname from the name of its root directory.

### 3. Command Reference

The following new commands provide the interface for managing networking, rooms, and remote execution.

#### 3.1. `port` - Manage the network service

*   **Usage**:
    *   `port on [port_num]`
    *   `port off`
    *   `port`
*   **Description**: Controls the network listener service that allows other systems and clients to connect.
*   **Implementation Details**:
    *   `port on [port_num]`: Instructs the kernel to start its listener service. If `port_num` is not provided, it defaults to `4209`. The kernel will maintain its listening status.
    *   `port off`: Instructs the kernel to gracefully shut down the network service and close all active connections.
    *   `port`: Displays the current status, e.g., `:: port 4209 open` or `:: port closed`.
*   **Example**:
    ```
    $ port on 8000
    :: port 8000 opened
    ```

#### 3.2. `mesh` - Connect to other IOSK systems

*   **Usage**:
    *   `mesh <host[:port]>`
    *   `mesh`
*   **Description**: Establishes an outbound connection to another IOSK system's `port` service, adding it to the local system's network mesh.
*   **Implementation Details**:

    *   `mesh <host[:port]>`: The kernel initiates a new network connection to the specified address. Upon a successful handshake, the remote host is added to a kernel-level list of connected systems. The handshake process involves exchanging hostname and user lists to synchronize network state.
    *   `mesh`: Lists all currently connected peers, showing their hostname and connection status.
*   **Example**:
    ```
    $ mesh gemini2
    :: Connecting to gemini2:4209...
    :: Connection established.

    $ mesh
    gemini2     10.1.2.3:4209
    :: 1 peer connected
    ```

#### 3.3. `room` - Manage the local chat room

*   **Usage**:
    *   `room <room_name>`
    *   `room`
*   **Description**: Creates or displays the status of the single active chat room on the local system.
*   **Implementation Details**:
    *   `room <room_name>`:
        *   The command's `iocall` delegates to the kernel's chat subsystem via `io.os.chat.open_room(...)`.
        *   The subsystem checks if a room is already active. If so, it returns an error.
        *   It sets the specified room as the active room, creating `/var/room/<room_name>/` if it doesn't exist and writing the current user to the `owner` file.
        *   The console user's prompt changes from `$` to `>>` (this logic is handled by the kernel's `interactive` loop).
        *   A "room opened" message is broadcast to all connected network peers via the `PortManager`.
    *   `room`: If a room is active, displays its name and topic (read from `/var/room/<name>/topic`). Otherwise, indicates no room is active.
*   **Example**:
    ```
    $ room dispatch
    :: room 'dispatch' opened
    [root /root] >> $ room
    :: Current room: dispatch
    :: Topic: (not set)
    ```

#### 3.4. `clroom` - Close the active chat room

*   **Usage**: `clroom`
*   **Description**: Closes the single active chat room on the local system.
*   **Implementation Details**:
    *   This command delegates to the kernel's chat subsystem via `io.os.chat.close_room(...)`.
    *   The subsystem sets the active room to none.
    *   The prompt reverts from `>>` to `$`.
    *   A "room closed" message is broadcast to peers.
*   **Example**:
    ```
    [root /root] >> $ clroom
    :: room 'dispatch' closed
    [root /root] $
    ```

#### 3.5. `rooms` - List known local rooms

*   **Usage**: `rooms`
*   **Description**: Lists all rooms that have been created on the local system, indicating which one is currently active with "*".
*   **Implementation Details**: The command performs an `ls` on `/var/room/`. It then compares this list against the kernel's active room tracking (`io.os.chat.active_room`) to mark the active room.
*   **Example**:
    ```
    $ rooms
    *dispatch
    IT3
    general
    :: 3 rooms found
    ```

#### 3.6. `on` - Execute commands remotely

*   **Usage**: `on <host> <command...>`
*   **Description**: Executes a command on a remote host within the mesh and streams the output back.
*   **Implementation Details**:
    *   The kernel validates that `<host>` is a connected peer.
    *   It sends a remote execution request containing the command string.
    *   The remote kernel receives the message, executes the command in a `root` context, captures the output, and streams it back.
    *   The local `on` process prints the received output, prefixing each line with `[<host>]: `.
*   **Example**:
    ```
    $ on gemini2 users
    :: on gemini2:
    root
    gamma
    :: 2 users online
    ```

#### 3.7. `where` - List all users on the network

*   **Usage**: `where`
*   **Description**: Displays a list of all known users across the entire network mesh and their host location.
*   **Implementation Details**:
    *   The kernel maintains a network-wide user list, which is a dictionary mapping `user.host` to user metadata.
    *   This list is populated initially via handshake on `mesh` connection and is kept synchronized via network messages between peers.
    *   The `where` command simply formats and prints the contents of this network user list.
*   **Example**:
    ```
    $ where
    USER            HOST
    ----            ----
    root            novamente
    gamma           gemini2
    lannocc         sk_terminal_1
    ```

#### 3.8. `whereami` - Display the local hostname

*   **Usage**: `whereami`
*   **Description**: Displays the configured hostname of the local IOSK system.
*   **Implementation Details**: The command reads and prints the content of `/etc/hostname`. It serves as a simple way to identify the current system in a networked environment.
*   **Example**:
    ```
    $ whereami
    novamente
    ```

### 4. Modified Commands

#### 4.1. Direct Messaging: `@user.host` and `send -u user.host`

*   **Usage**:
    *   `@gamma.gemini2 Hello there!`
    *   `cat message.txt | send -u gamma.gemini2`
*   **Description**: The direct messaging syntax is extended to support the `user.host` format for sending messages to users on remote systems.
*   **Implementation Details**:
    *   The messaging system is updated to parse `user.host` addresses.
    *   If a `.host` is detected, the kernel identifies the appropriate peer connection.
    *   A direct message request is sent to the target host, containing the sender's full address (`from_user@from_host`), the recipient's username, and the message content.
    *   The remote kernel receives the message and delivers it to the local user.

