# IOSK Kernel Modifications for Netroom Architecture

### 1. Introduction

This document details the necessary modifications to the IOSK Kernel (`src/iosk/kernel.py`) to support the proposed networking and multi-room architecture ("Netroom"). As outlined in `netroom.md`, this evolution introduces a clear separation between the core OS and its networking capabilities. The kernel's primary role remains the management of the local filesystem, users, and command execution, but it will be extended to manage network state and delegate all network I/O to a dedicated `PortManager` component.

### 2. High-Level Architectural Changes

The kernel's architecture will be modified to embrace a client-server model for networking.

*   **Delegation of Networking**: All low-level networking logic (WebSocket server, connection management, message serialization) will be encapsulated within a new `PortManager` class (`src/iosk/port.py`), as specified in `doc/iosk/proposal/netroom/port.md`.
*   **Kernel as Service Provider**: The `IOSK` kernel will instantiate and own the `PortManager`, making it available at `self.port`. The kernel will interact with it through a high-level API (e.g., `port.start()`), and in turn, the `PortManager` will use the kernel's fundamental methods (e.g., `login`, `call`) to provide services to network users.
*   **Centralized State Management**: The kernel will become the source of truth for the local system's state (hostname, local users) and a cache for the state of the wider network (remote users and rooms). It will own and manage its core subsystems, including `AIMessenger` (`self.chat`).

### 3. New Kernel State Attributes

The `IOSK` class in `src/iosk/kernel.py` will be augmented with the following attributes in its `__init__` method:

*   `self.port` (`PortManager`): An instance of the `PortManager` class, responsible for all network communication. Initialized to `None`.
*   `self.chat` (`AIMessenger`): An instance of the `AIMessenger` class, responsible for all chat room logic. Initialized to `None`.
*   `self.hostname` (str): The unique name of the local IOSK system on the network (e.g., `lannocc.novamente`). This is read from `/etc/hostname` at startup.
*   `self.network_users` (dict): A cache of all known users across the network mesh, mapping a unique address (`user.host`) to user metadata. This is the data source for the `where` command.
*   `self.network_rooms` (dict): A cache of all known active rooms across the network, mapping a unique room address (`room.host`) to room metadata.

### 4. System Lifecycle Modifications

The kernel's startup and shutdown sequences must be updated to manage its subsystems.

*   **`IOSK.start()`**:
    *   After the filesystem is verified, the kernel will read the contents of `/etc/hostname` to populate `self.hostname`. If the file doesn't exist, the hostname will be derived from the name of the `root` directory.
    *   The kernel's subsystems will be instantiated: `self.port = PortManager(self)` and `self.chat = AIMessenger(self)`.

*   **`IOSK.run()`**:
    *   The shutdown sequence within the `run` loop (after `self.halt.wait()`) must be updated to gracefully shut down the network service *before* logging out users.
    *   A new line `await self.port.stop()` will be added at the beginning of the shutdown logic.

### 5. Network User Management

The kernel's user management logic will be extended to differentiate between local (device-attached) users and network (client-attached) users.

*   **`IOSK.login()` and `IOSK.logout()`**:
    *   These methods will be modified to announce user state changes to the network.
    *   After a local user successfully logs in, the kernel will call `await self.port.broadcast_to_peers({'type': 'user_update', ...})`.
    *   Similarly, upon logout, a `user_update` message with `action: 'logout'` will be broadcast.

*   **New Method: `async login_network_user(self, username, websocket)`**:
    *   This method is called exclusively by the `PortManager` upon a successful client (`skh`) handshake.
    *   It performs the same initial login steps as the standard `login` method (creating a `Context`, home directory, running `.skrc`, etc.).
    *   **Crucially**, it does *not* associate the user with a `/dev/` path. Instead, the `io.dev` attribute will be set to a special identifier, like `network:<websocket_id>`. The `PortManager` is responsible for routing I/O between the user's `Context` and the client's websocket.
    *   It finishes by broadcasting a `user_update` to all peers.

*   **New Method: `async logout_network_user(self, username)`**:
    *   Called by the `PortManager` when a client's websocket connection is closed.
    *   This method will find the user's `Context` and call the standard `self.logout(io)`.

### 6. Command Execution and Interactive Prompt

#### 6.1. Local Network Commands

The `iocall` for the new network management commands will invoke specific methods on the `PortManager` and `AIMessenger` instances.

*   **`port on [port_num]`**: Calls `await self.port.start(port_num)`.
*   **`mesh <host>`**: Calls `await self.port.connect_to_peer(host)`.
*   **`room <room_name>`**: Delegates to the chat subsystem by calling `await self.chat.open_room(io, room_name)`.
*   **`clroom`**: Delegates to the chat subsystem by calling `await self.chat.close_room(io)`.

#### 6.2. Remote Command Execution (`on`)

The kernel acts as both a client and a server for remote execution, with the `PortManager` handling all transit.

*   **Originating an `on` command**:
    1.  The `on` command's `iocall` validates its arguments (`host`, `command`).
    2.  It uses `self.port.route_message(target_host, {'type': 'remote_exec_request', ...})` to send the request.
    3.  It then awaits response chunks (`remote_exec_response`) from the `PortManager` and streams them to the user's local `io` context, prefixed with `[<host>]: `.

*   **Receiving a remote execution request**:
    1.  The `PortManager`, upon receiving a `remote_exec_request` message, will create a temporary `root` context for the execution (`exec_io = self.system.fork()`).
    2.  It will redirect the `exec_io`'s I/O to in-memory buffers or custom writers that stream output back to the `PortManager`.
    3.  It will then invoke the kernel's universal command processor: `await self.call(exec_io, command_str)`. The kernel's `call` method is unaware that the command is from a remote source.
    4.  As output is generated, it is captured and sent back by the `PortManager` as `remote_exec_response` messages.

#### 6.3. Interactive Prompt Management
The kernel's `interactive()` method, which manages the command loop for a user, will be updated. Before displaying the prompt, it will check the status of the chat subsystem to determine the correct prompt character:
```python
if self.chat and self.chat.active_room:
    prompt_char = '>>'
else:
    prompt_char = '$'
prompt = f'[{io.user} {io.pwd}] {prompt_char} '
```
This ensures the user's prompt dynamically reflects whether a chat room is active.

### 7. Message Routing and Chat Integration

The `AIMessenger` and `PortManager` work together to handle room-based and direct messages, with the kernel acting as a facilitator rather than a router.

*   **Outbound Messages**: The `AIMessenger.send()` method is responsible for determining if a message is local or remote. If remote, it calls the `PortManager` directly (e.g., `self.os.port.route_message(...)`) to send the message.
*   **Inbound Messages**: The `PortManager` receives all network messages. For chat-related messages (`direct_message`, `room_message`), it passes them to the chat subsystem for processing via `self.kernel.chat.handle_network_message(...)`.
*   **Client Input Handling**: The `PortManager` will receive `client_input` messages from `skh` clients. It will call a kernel method, `async handle_client_input(self, username, data)`, which will find the user's `Context` and feed the `data` into their `interactive` loop as if it came from a local device.

