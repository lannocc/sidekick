# Proposal: IOSK Networking and Rooms

**Status**: Proposed (General First Draft -- see `netroom/` subdirectory for updated and specific details)

### 1. Introduction

This proposal outlines the next generation of the IOSK architecture, evolving it from a single, isolated instance into a networked federation of systems. The core idea is to introduce a clear separation between the base OS (kernel and console) and its collaborative features (chat rooms and networking). This will be achieved through a new "port" service for inter-system communication, a "room" concept for chat, remote command execution, and a new rich terminal client for user access.

This evolution will transform IOSK into a distributed, multi-user, multi-system environment, laying the foundation for more complex and powerful collaborative AI workflows.

### 2. Core Architectural Changes

Each running IOSK instance, or "system," will be composed of four primary components:

*   **Kernel**: The core running process that manages the filesystem, users, and command execution. This is always active.
*   **Console**: The primary interface for the `root` user. Every IOSK system will start with a `root` console, providing an initial administrative entry point.
*   **Port**: An optional WebSocket service that opens a network port, allowing the system to communicate with other IOSK systems, rich terminals, and web clients.
*   **Room**: An optional, transient chat service that can be started on a system. Only one room can be active at a time per system.

#### 2.1. Startup Process

The command-line interface for starting IOSK will be simplified:

*   The `sk iosk` command will be removed. The primary entry point will be a standalone `iosk` command.
*   The command will only take the root directory as an argument: `iosk <root_directory>`.
*   Upon startup, the system will always launch a console for the `root` user, with a home directory of `/root`.

#### 2.2. Console Prompt

The `root` console prompt will dynamically reflect the system's state:
*   `[root /current/path] $ `: The standard prompt when no chat room is active. Commands are accepted.
*   `[root /current/path] >> `: The prompt when a chat room is active. Both commands (`$ ...`) and chat messages are accepted.

### 3. Networking Model

The `port` component enables IOSK systems to form a simple, mesh-like network.

*   **Communication**: The service uses WebSockets for all network communication. The default port is `4209`.
*   **Connectivity**: Systems can connect to each other to share state and route messages. The network will be responsible for synchronizing the list of connected users and their locations.
*   **User Addressing**: To support cross-system communication, a new user addressing scheme will be adopted: `user.host` (e.g., `lannocc.novamente`). Usernames themselves cannot contain dots. This format will be supported by direct messages (`@user.host`) and the `send -u user.host` command.

### 4. New and Modified Commands

To manage this new architecture, several commands will be introduced or modified.

*   `mesh [host[:port]]`:
    *   With no arguments, displays the status of the current system's network connections.
    *   With a `host`, attempts to connect to another IOSK system's port.

*   `room <room_name>`:
    *   Starts a new chat room on the local system, giving it the specified name. If a room is already active, this command will fail. The console prompt will change from `$` to `>>` to indicate chat is active.

*   `on <host> <command...>`:
    *   Executes a command on a remote, connected host. This is the primary mechanism for remote administration and interaction. For example: `on gemini2 attach google gamma`.

*   `where`:
    *   Displays a list of all known users across the entire mesh, showing their username and the host they are connected to.

*   `@<user.host>` and `send -u <user.host>`:
    *   These commands will be updated to recognize the `user.host` format, allowing for direct messaging to users on remote systems.

### 5. The Rich Terminal Client (`skh`)

To provide a dedicated and enhanced user experience, a new command-line client, `skh` (SideKick Host), will be created.

*   **Purpose**: `skh` will be the standard way for non-root users to log into an IOSK system. It will connect to the target system's `port` service.
*   **Usage**: The command will function similarly to `ssh`:
    *   `skh <user>`: Connects to `localhost:4209` as `<user>`.
    *   `skh <user.host>`: Connects to `<host>:4209` as `<user>`.
    *   `skh <user.host:port>`: Connects to `<host>:<port>` as `<user>`.
*   **Features**: While the full feature set will be defined in a future proposal, `skh` is envisioned as a rich terminal providing a superior experience to the basic `root` console, with features like persistent command history, tab completion, and better line editing.

### 6. Deprecations

*   **`sk iosk` command**: This will be fully replaced by the `iosk` and `skh` commands.
*   **`dev/terminal.py`**: This experimental module will be removed, as its role is superseded by the new `skh` client and `port` service architecture.

### 7. Example Workflow

This workflow demonstrates how the new components interact, starting from a standard bash shell.

```bash
# Start a new iosk system in the 'iosk' directory.
# A root console appears.
$ iosk iosk
[root /root] $

# Start a local chat room named 'dispatch'. Prompt changes to indicate chat mode.
[root /root] $ room dispatch
:: room 'dispatch' opened
[root /root] >>

# Connect to another running iosk system named 'gemini2' on the default port.
[root /root] >> $ mesh gemini2
:: connected to gemini2:4209

# Remotely start a chat room named 'IT3' on the 'gemini2' system.
[root /root] >> $ on gemini2 room IT3
:: on gemini2: room 'IT3' opened

# Remotely attach the 'google' device as user 'gamma' on the 'gemini2' system.
[root /root] >> $ on gemini2 attach google gamma
:: on gemini2: root attached user 'gamma' to device '/dev/google'

# Send a direct message to the newly created remote user.
[root /root] >> @gamma.gemini2 Hello gamma!
```

### 8. Security Considerations

For this initial implementation phase, security features such as authentication, authorization, and encryption are explicitly out of scope. The IOSK network is assumed to be deployed in a trusted, protected local environment. Future proposals will address securing the `port` service and implementing user access controls.

### 9. Future Considerations

This proposal lays the groundwork for several future enhancements:

*   **WebSocket API Specification**: A detailed protocol for `port` communication will need to be defined to standardize interactions between systems, terminals, and web clients.
*   **`skh` Rich Terminal Features**: A full specification for the rich terminal, including features like cross-session history and network-aware tab completion.
*   **Federated Rooms**: A mechanism to link rooms across different systems, allowing users in `roomA.host1` to chat with users in `roomB.host2`.
*   **Network Discovery**: An automated discovery protocol to allow IOSK systems to find each other on the local network without manual `mesh` commands.

