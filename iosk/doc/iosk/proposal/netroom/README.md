# IOSK Netroom Implementation Plan

This document outlines the detailed, actionable steps for implementing the IOSK Netroom architecture as specified in the proposal documents. This plan follows a logical order, starting with core system modifications and progressively adding networking features and user-facing commands.

When implementing the Netroom feature set, refer to the detailed specifications in the `doc/iosk/proposal/netroom/` subdirectory as the primary source of truth for each component.

---

## Implementation Order

### 1. Update the Command-Line Entry Point

-   **File to Modify:** `src/iosk/cmd.py`
-   **Action:** Simplify the main entry point to exclusively launch the `root` console session, removing previous sub-commands and options.
-   **Reference:** `doc/iosk/proposal/netroom/cmd.md`

### 2. Create the Core Networking Subsystem

-   **File to Create:** `src/iosk/port.py`
-   **Action:** Implement the `PortManager` class. This class will encapsulate all low-level WebSocket server logic, connection handling, and message routing.
-   **Reference:** `doc/iosk/proposal/netroom/port.md`

### 3. Refactor the Chat Subsystem

-   **File to Modify:** `src/iosk/chat.py`
-   **Action:** Rework the `AIMessenger` class to function as a kernel-managed subsystem. It will handle local room state and logic, and interact with the `PortManager` for network communication.
-   **Reference:** `doc/iosk/proposal/netroom/chat.md`

### 4. Integrate Subsystems into the Kernel

-   **File to Modify:** `src/iosk/kernel.py`
-   **Action:** Update the `IOSK` kernel to instantiate, own, and manage the `PortManager` and `AIMessenger` subsystems. Add state management for network users/rooms and modify the system lifecycle to include the new components.
-   **Reference:** `doc/iosk/proposal/netroom/kernel.md`

### 5. Implement Networking and Room Commands

Create the new user-facing commands that provide the interface for managing networking, rooms, and remote execution.

#### 5.1. Implement `port` Command

-   **File to Create:** `/bin/port.py`
-   **Action:** Create the command to start, stop, and check the status of the network listener service.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.2. Implement `mesh` Command

-   **File to Create:** `/bin/mesh.py`
-   **Action:** Create the command to establish outbound connections to other IOSK systems and view the status of the network mesh.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.3. Implement `room` Command

-   **File to Create:** `/bin/room.py`
-   **Action:** Create the command to open and manage the single active chat room on the local system.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.4. Implement `clroom` Command

-   **File to Create:** `/bin/clroom.py`
-   **Action:** Create the command to close the active chat room.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.5. Implement `rooms` Command

-   **File to Create:** `/bin/rooms.py`
-   **Action:** Create the command to list all locally created (persistent) rooms.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.6. Implement `on` Command

-   **File to Create:** `/bin/on.py`
-   **Action:** Create the command to execute a command on a remote, connected host and stream the output back.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.7. Implement `where` Command

-   **File to Create:** `/bin/where.py`
-   **Action:** Create the command to display a list of all known users across the entire network mesh and their host location.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

#### 5.8. Implement `whereami` Command

-   **File to Create:** `/bin/whereami.py`
-   **Action:** Create the command to display the configured hostname of the local IOSK system.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

### 6. Create Supporting Configuration Files

-   **File to Create:** `/etc/hostname`
-   **Action:** Add the default configuration file required by the new commands and subsystems to store the system's network hostname.
-   **Reference:** `doc/iosk/proposal/netroom/commands.md`

