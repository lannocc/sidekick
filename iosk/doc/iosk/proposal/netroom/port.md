# IOSK Port System: A Detailed Specification

### 1. Introduction

This document provides a detailed specification for the IOSK Port system, the dedicated networking layer for the IOSK operating system. All networking functionality, including the WebSocket server, connection management, and message routing, will be encapsulated within a new `PortManager` class, to be located in `src/iosk/port.py`.

This design decouples the complex, asynchronous logic of network communication from the core OS kernel. The kernel will interact with the Port system through a clean, high-level API, delegating all socket-level operations and protocol management. This results in a more modular, maintainable, and testable architecture.

### 2. The `PortManager` Class

The `PortManager` class will be the central component of the `src/iosk/port.py` module. It is responsible for the entire lifecycle of the system's network presence.

**Initialization**:
`__init__(self, kernel)`
*   The `PortManager` is initialized with a reference to the main `IOSK` kernel instance. This allows it to access and modify kernel state (e.g., user lists, room status) and invoke the kernel's fundamental methods (e.g., `login`, `call`).

**Core Responsibilities**:
*   Start and stop the main WebSocket server (`port on`/`off`).
*   Handle all new incoming network connections.
*   Perform a handshake protocol to identify connections as either a peer IOSK system or a client (`skh`).
*   Manage the lifecycle and state of all active network connections.
*   Maintain a list of connected peers to form the network mesh.
*   Receive, parse, and dispatch all incoming network messages.
*   Route messages between the local kernel, remote peers, and connected clients.

### 3. State Management

The `PortManager` will own and manage all network-related state. The kernel will not track this directly.

**`PortManager` Instance Attributes**:
*   `self.kernel` (`IOSK`): The reference to the IOSK kernel.
*   `self.server_task` (`asyncio.Task`): The asyncio task running the main WebSocket server loop. `None` if the port is closed.
*   `self.port` (int): The port number the server is listening on.
*   `self.active_connections` (dict): A dictionary mapping `websocket` connection objects to a `Connection` dataclass instance, which stores metadata like `type` (`peer` or `client`), `hostname`, and associated `username`.
*   `self.peers` (dict): A dictionary mapping a remote peer's `hostname` to its `websocket` connection object for efficient message routing.

### 4. Public API (Kernel-Facing)

These are the methods that the kernel will invoke on its `PortManager` instance.

*   `async start(self, port_num)`:
    *   Called by the `port on` command's `iocall`.
    *   Starts the WebSocket server on the given `port_num`.
    *   Stores the server task in `self.server_task`.
    *   Returns `True` on success.

*   `async stop(self)`:
    *   Called by the `port off` command's `iocall`.
    *   Gracefully closes the server and all active connections.
    *   Clears all peer-related state.

*   `async broadcast_to_peers(self, message)`:
    *   Used by subsystems (like `chat`) to propagate local state changes to all other connected systems.
    *   Serializes the `message` dictionary to JSON and sends it to every peer in `self.peers`.

*   `async route_message(self, target_host, message)`:
    *   A generic routing method used for targeted messages like DMs or remote execution requests.
    *   Looks up the `target_host` in `self.peers` and sends the `message`.

### 5. Internal Logic and Connection Handling

The `PortManager` encapsulates the entire connection lifecycle.

*   `async _server_loop(self, port_num)`:
    *   The primary coroutine that uses `websockets.serve` to listen for new connections, passing each to `_connection_handler`.

*   `async _connection_handler(self, websocket, path)`:
    *   The entry point for every new connection.
    *   It immediately calls `_handshake` to identify the connection.
    *   If the handshake is successful, it enters a `_message_loop` to process incoming messages from that connection until it closes.
    *   A `finally` block ensures cleanup, such as removing the connection from state dictionaries and calling `self.kernel.logout_network_user` if it was a client connection.

*   `async _handshake(self, websocket)`:
    *   Waits for the first message from a new connection.
    *   This message must be a JSON object with a `type: 'handshake'` field and additional metadata.
        *   **Peer Handshake**: `{'type': 'handshake', 'id': 'peer', 'hostname': 'gemini2'}`. If successful, the `PortManager` adds the peer to `self.peers`, registers the connection, and initiates a state exchange (user lists, room status).
        *   **Client Handshake**: `{'type': 'handshake', 'id': 'client', 'user': 'gamma'}`. If successful, the `PortManager` calls a fundamental kernel method: `await self.kernel.login_network_user('gamma', websocket)` to create a new user session backed by this network connection.
    *   Returns the `Connection` metadata object on success, or raises an exception on failure.

*   `async _message_loop(self, connection_metadata)`:
    *   Continuously `await`s messages from the connection's websocket.
    *   Passes each received message to `_dispatch_message`.

*   `async _dispatch_message(self, connection, message_str)`:
    *   Deserializes the JSON `message_str`.
    *   Acts as a central router based on the message `type`:
        *   `user_update`, `room_update`: Calls `self.kernel.update_network_state` to update the kernel's cache of network state.
        *   `remote_exec_request`: Creates a temporary `root` context, redirects its I/O to the websocket, and invokes the kernel's universal command processor via `await self.kernel.call(...)`.
        *   `direct_message`, `room_message`: Delivers the message to the chat subsystem via `await self.kernel.chat.handle_network_message(...)`.
        *   `client_input`: For client connections, this is raw input from the user's terminal. It's passed to the kernel for the corresponding network-backed user `Context` via `await self.kernel.handle_client_input(...)`.

### 6. Network Protocol Specification

All communication is done via JSON-serialized strings. Every message must have a `type` field.

| Message Type               | Direction          | Fields                                                | Description                                                                                             |
| :------------------------- | :----------------- | :---------------------------------------------------- | :------------------------------------------------------------------------------------------------------ |
| **`handshake`**            | Client/Peer -> Sys | `id` ('peer'/'client'), `hostname` (if peer), `user` (if client) | The first message on any new connection to identify its type.                                           |
| **`handshake_ack`**        | Sys -> Client/Peer | `status` ('ok'/'error'), `hostname`, `users`, `rooms`   | System's response to a handshake, providing initial state.                                              |
| **`user_update`**          | Peer -> Peer       | `action` ('login'/'logout'), `user`, `host`             | Broadcast to peers to announce a change in a system's local user list.                                  |
| **`room_update`**          | Peer -> Peer       | `action` ('open'/'close'), `name`, `host`, `topic`      | Broadcast to peers to announce a change in a system's active room.                                      |
| **`remote_exec_request`**  | Sys -> Peer        | `origin_host`, `command_str`                          | Sent by the `on` command to request remote execution.                                                   |
| **`remote_exec_response`** | Peer -> Sys        | `stream` ('stdout'/'stderr'), `data`, `is_complete`     | A chunk of output from a remote command, streamed back to the originator.                               |
| **`direct_message`**       | Sys -> Peer        | `from_addr`, `to_user`, `content`                     | A direct message routed to a user on a remote system.                                                   |
| **`client_input`**         | Client -> Sys      | `data`                                                | Raw text input typed by a user in an `skh` client.                                                      |
| **`client_output`**        | Sys -> Client      | `data`                                                | Raw text output from the system (command output, chat messages) to be displayed in the `skh` client. |

### 7. Conclusion

By abstracting network logic into a dedicated `PortManager` class, the IOSK kernel can focus on its core responsibilities: managing users, the filesystem, and command execution. This clean separation of concerns makes the entire system more robust and easier to extend. The `PortManager` acts as the gatekeeper and router for all external communication, providing a single, well-defined interface between the internal state of an IOSK system and the wider network.

