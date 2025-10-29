# IOSK Netroom Chat System Architecture

### 1. Introduction

This document specifies the architecture of the IOSK chat subsystem, `AIMessenger`, located in `src/iosk/chat.py`. In the Netroom architecture, `AIMessenger` is a core kernel subsystem responsible for all chat-related functionality. It is instantiated by the kernel at startup and remains dormant until activated by a user via the `room` command.

The `AIMessenger` class manages the lifecycle and state of the local chat room. The kernel delegates all chat operations to this subsystem, creating a clean separation of concerns. The kernel handles core OS functions (users, files, command execution), while `AIMessenger` manages the conversational environment and interacts with the `PortManager` for network communication.

### 2. Architectural Role of `AIMessenger`

As a kernel subsystem, `AIMessenger`'s responsibilities are clearly defined:

*   **Owner of Local Room State**: It becomes the sole source of truth for the active local chat room, including its name, topic, owner, and the list of participating local users.
*   **Handler for Room Lifecycle**: It provides the backend logic for the `room`, `clroom`, and `topic` commands, managing the creation, closure, and configuration of the local chat room.
*   **Message Router**: It intelligently routes all messages originating from local users, determining whether a message is a local room broadcast, a local direct message, or a remote direct message to be passed to the `PortManager` for network transit.
*   **Network Event Sink**: It acts as the final destination for chat-related events that arrive from the network via the `PortManager`, processing incoming remote messages and delivering them to the appropriate local users.

### 3. State Management

To manage the local room, `AIMessenger` will be updated with the following attributes:

*   `self.active_room` (str or None): The name of the currently active chat room on this system. Defaults to `None`.
*   `self.room_topic` (str or None): The topic of the active room, loaded from `/var/room/<name>/topic`.
*   `self.room_owner` (str or None): The username of the user who created the room, loaded from `/var/room/<name>/owner`.
*   `self.local_room_participants` (set): A set of usernames for all local users (both console and AI agents) currently participating in the active room.

This state is ephemeral and is loaded from the persistent filesystem representation in `/var/room/` when a room is opened.

### 4. Room Lifecycle API

`AIMessenger` will expose a new set of methods to be called by the `iocall` functions of the corresponding room management commands.

*   `async open_room(self, io: Context, room_name: str) -> bool`:
    *   **Called by**: `room <room_name>` command.
    *   **Logic**:
        1.  Fails if `self.active_room` is already set.
        2.  Sets `self.active_room = room_name` and `self.room_owner = io.user`.
        3.  Initializes `self.local_room_participants = {io.user}`.
        4.  Creates the directory `/var/room/<room_name>` if it doesn't exist and writes the owner's name to `/var/room/<room_name>/owner`.
        5.  Loads the topic and MOTD from the room's directory.
        6.  Displays the MOTD to the user.
        7.  Delegates to the `PortManager` to broadcast the state change: `await self.os.port.broadcast_to_peers({'type': 'room_update', 'action': 'open', 'name': room_name, ...})`.

*   `async close_room(self, io: Context) -> bool`:
    *   **Called by**: `clroom` command.
    *   **Logic**:
        1.  Fails if `self.active_room` is `None`.
        2.  Performs a permission check (e.g., `io.user == self.room_owner` or `io.su`).
        3.  Broadcasts a "room closing" message to all `self.local_room_participants`.
        4.  Resets all room-related state attributes (`active_room`, `room_topic`, etc.) to `None` and clears the participant list.
        5.  Delegates to the `PortManager` to broadcast a `room_update` with `action: 'close'`.

*   `async add_to_room(self, target_io: Context) -> bool`:
    *   **Called by**: The `attach` command's logic when bringing another user into a room.
    *   **Logic**:
        1.  Fails if no room is active.
        2.  Adds `target_io.user` to `self.local_room_participants`.
        3.  Sends the room's MOTD to the `target_io` context.
        4.  Announces the user's arrival to other participants in the room.

*   `async remove_from_room(self, user_name: str)`:
    *   **Called by**: The `AIMessenger.leave` method when a user logs out of the system.
    *   **Logic**: Removes the `user_name` from `self.local_room_participants` if present.

### 5. Message Routing Logic (`send` method)

The `send()` method is refactored to become the central message router.

`async send(self, from_user: str, msg: str, sys: bool = False)`

*   **Step 1: Parse for Direct Messages**
    *   If the message is not from the system and starts with `@`, it's parsed to identify recipients.
    *   For each remote recipient `user.host`, `AIMessenger` calls the `PortManager` directly: `await self.os.port.route_message(target_host, {'type': 'direct_message', ...})`.
    *   For each local recipient `user`, the message is delivered directly via `uio.print()`.

*   **Step 2: Handle Room Broadcasts**
    *   If the message is not a DM and `self.active_room` is set:
        *   A formatted message (`[from_user] << content`) is prepared.
        *   The message is sent to every local user in `self.local_room_participants` (except the sender).
        *   `AIMessenger` calls the `PortManager` to relay the message to remote peers: `await self.os.port.broadcast_to_peers({'type': 'room_message', ...})`.

*   **Step 3: Handle System Messages and No-Room State**
    *   If `sys=True`, the message is a system-wide announcement and is sent to all locally connected users (`self.os.users`).
    *   If it is a regular chat message but no room is active, an error is printed to the sender (e.g., `!! No active room. Use 'room <name>' to start one.`).

### 6. Handling Network Events

The `PortManager` will pass incoming chat-related network messages to `AIMessenger` via a new handler method.

`async handle_network_message(self, message: dict)`

*   **`room_message`**:
    *   Checks if the message's room name matches `self.active_room`.
    *   If it matches, the message (`[user@host] << content`) is formatted and broadcast to all users in `self.local_room_participants`.

*   **`direct_message`**:
    *   Identifies the local recipient specified in `message['to_user']`.
    *   If the user exists, a formatted DM (`[user@host -> me] << content`) is delivered to their context.

### 7. Subsystem Interaction API

This design establishes a clear API boundary between the different IOSK subsystems.

**`AIMessenger` calls `PortManager` (via `self.os.port`):**
*   `self.os.port.route_message(target_host, payload)`: Asks the port system to send a DM or other targeted message over the network.
*   `self.os.port.broadcast_to_peers(payload)`: Asks the port system to broadcast a state change or room message to all network peers.

**Kernel calls `AIMessenger`:**
*   `self.chat.open_room(io, name)`: Fulfills the `room` command.
*   `self.chat.close_room(io)`: Fulfills the `clroom` command.
*   `self.chat.add_to_room(target_io)`: Fulfills part of the `attach` command logic.

**`PortManager` calls `AIMessenger`:**
*   `self.kernel.chat.handle_network_message(message)`: Delivers an incoming network message for processing by the chat system.

