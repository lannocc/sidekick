# Groups

**Status**: Proposed.

### Introduction

The current IOSK environment treats all logged-in users as participants in a single, system-wide chat session. While this is effective for a small, open system, it lacks the necessary mechanisms for private collaboration, access control, and project-based organization. As IOSK evolves into a more capable multi-user environment, we need a robust model for security and context separation.

This proposal introduces the concept of **Groups** as persistent security principals and **Rooms** as ephemeral chat sessions. A "room" is a temporary, private chat channel associated with a "group." Users can be members of multiple groups but can only be "active" in one room at a time. Entry into these rooms is by invitation or explicit switching, creating a secure and context-rich environment for collaboration between humans and AI agents.

This system moves IOSK from a single-room chat server to a true multi-tenant collaborative OS, laying the groundwork for project management, team-based AI interactions, and a comprehensive file permission system, while maintaining the flexibility of ephemeral communication channels.

### Core Concepts

1.  **Groups as Persistent Security Principals**: A "group" is a persistent entity, defined by its name. When a group is first referenced, its associated shared workspace is created under `/home/groups/`. These groups and their workspaces persist even when no users are actively in their associated chat room.
2.  **Rooms as Ephemeral Chat Sessions**: A "room" is an active, private chat channel. A room comes into existence implicitly when the first user enters a specific group's context. The room disappears when the last user leaves. Chat messages are confined to members of the current room.
3.  **Shared Workspaces**: Every group is associated with a unique directory at `/home/groups/<group_name>`. This directory serves as a shared, persistent workspace for all members of that group.
4.  **Invitation and Switching-Based Membership**: Users can join a group's room either by being invited (using `attach`) or by explicitly switching to it (using `chroom`). These actions implicitly create a room if one doesn't already exist for that group.
5.  **Path-Based Access Control**: Security is enforced based on a file's path. The kernel will prevent users from accessing files inside a group's workspace (e.g., `/home/groups/project-x/`) unless their current `io.group` context matches that group. This provides robust security without needing a complex file permission metadata system.

### Implementation Strategy

#### 1. Filesystem Layout Changes

To accommodate both private user data and shared group data, the `/home` directory will be restructured:
*   `/home/` -> `/home/users/`: All existing user home directories will be conceptually moved here. New home directories will be created at `/home/users/<user>/`.
*   `/home/groups/`: A new top-level directory will house the shared workspaces for each group. For a group named `project-x`, its workspace will be at `/home/groups/project-x/`.
*   `/etc/motd/`: A new directory for Message of the Day files. The default login message will be `/etc/motd/lobby`. Custom MOTD files for specific groups will be placed here, named after the group (e.g., `/etc/motd/project-x`).

#### 2. Kernel and Context Modifications

The core logic for managing groups, rooms, and enforcing security will reside in the kernel and the user `Context`.

**`src/iosk/kernel.py` - `IOSK` Class:**
*   **`self.groups`**: A new dictionary will be added: `self.groups = {}`. This will map group names (strings) to a simple metadata object or dictionary storing the `name` and `owner`.
*   **`self.active_rooms`**: A new dictionary `self.active_rooms = {}` will map group names to a list of active `io` contexts currently in that group's room. This represents the ephemeral chat session.
*   **`login()` Method**: Upon login, a user will be placed in the `lobby` group's room. Their home directory will be created under `/home/users/<user>/` if it doesn't exist.
*   **File Operations (`get`, `create`, `copy`, etc.)**: These methods will be updated to be group-aware. Before any file operation, the kernel will check if the target path is within a group workspace (i.e., starts with `/home/groups/`). If so, it will verify that the user's `io.group` matches the group in the path. If not, the operation will fail with a "permission denied" error.

**`src/iosk/io.py` - `Context` Class:**
*   **`self.group`**: An attribute will be added to each `Context` instance to track the user's current group name. Defaults to `lobby`.
*   **Prompt Modification**: The `interactive()` loop in `kernel.py` will be modified to display the current group in the user's prompt, e.g., `[beta@project-x] >>`.

**`src/iosk/chat.py` - `AIMessenger` Class:**
*   The `send()` method will be changed. Instead of broadcasting to all `self.os.users`, it will determine the sender's group from their `io.group` attribute, then retrieve the list of room members from `self.os.active_rooms[sender_group]` and send the message only to them.

#### 3. New and Modified Commands

A suite of new commands is required for group and room management, and several existing commands must be updated.

**New Commands:**
*   **`chroom <group_name>`**: Allows a user to switch their active context to a different group's room.
    *   If `<group_name>` does not exist in `self.groups`, a new group is created, `/home/groups/<group_name>` is created, and the current user becomes its owner.
    *   The user's `io.group` is updated.
    *   The user is moved between lists in the kernel's `self.active_rooms` dictionary.
    *   Upon switching, the MOTD from `/etc/motd/<group_name>` is displayed if it exists.
*   **`groups`**: Lists all available groups on the system (by reading keys from `self.groups`). An extended form, `groups -r`, could list the active rooms and their members.

**Modified Commands:**
*   **`attach <user>`**: Now has context-sensitive behavior for inviting users into rooms.
    *   When executed, the kernel moves the target `<user>` into the *inviter's current group's room*. The target user will receive a notification and see the room's MOTD.
    *   An optional `-g <group_name>` flag could be added to invite a user to a specific group's room directly.
*   **`users`**: This command will now only list users in the *current room*. A new flag, `users -a`, will be added to list all connected users across all rooms.

#### 4. MOTD Handling

*   When a user logs in, the contents of `/etc/motd/lobby` are displayed.
*   When a user runs `chroom <group_name>` or is `attach`ed to it, the system checks for `/etc/motd/<group_name>`. If the file exists, its content is displayed. If not, no specific MOTD is displayed for that room.

### Use Case Scenario

1.  User `alpha` logs in and is placed in the `lobby` group's room. The contents of `/etc/motd/lobby` are displayed. Their prompt is `[alpha@lobby] >>`.
2.  `alpha` executes `$ chroom project-titan`.
    *   The kernel creates a new group `project-titan`, and the directory `/home/groups/project-titan/`.
    *   `alpha`'s `io.group` attribute is updated to `project-titan`. `alpha` is moved to the `self.active_rooms['project-titan']` list.
    *   `alpha`'s prompt becomes `[alpha@project-titan] >>`.
3.  Meanwhile, user `beta` and the AI agent `openai` log in and are in the `lobby` room.
4.  From the `project-titan` room, `alpha` invites `beta` by running `$ attach beta`.
    *   `beta`'s `io.group` is updated to `project-titan` and they are moved into the same room as `alpha`.
    *   `beta` receives the message `:: alpha has brought you into room: project-titan`.
    *   `beta`'s prompt changes to `[beta@project-titan] >>`.
5.  `alpha` now invites the AI agent: `$ attach openai`. The `openai` agent is moved into the `project-titan` room.
6.  `alpha` runs `$ users`. The output is `alpha beta openai`.
7.  `beta` creates a file in the current directory: `$ touch plan.md`. The kernel resolves the path to `/home/groups/project-titan/plan.md`.
8.  Another user, `gamma`, logs in to the `lobby`. `gamma` cannot see the chat in `project-titan`. If `gamma` tries `$ cat /home/groups/project-titan/plan.md`, the kernel will see that `gamma`'s group (`lobby`) does not match the path's group (`project-titan`) and will return a "permission denied" error.
9.  Later, `alpha`, `beta`, and `openai` all `$ chroom lobby`.
    *   `self.active_rooms['project-titan']` becomes empty. The room effectively disappears.
    *   **Crucially, the `project-titan` group persists, and the workspace `/home/groups/project-titan/` with `plan.md` remains intact.**
10. `alpha` or `beta` can later `$ chroom project-titan` to reactivate the room and resume work.

### Benefits

*   **Security and Privacy**: Confines conversations and files to intended participants.
*   **Contextual Collaboration**: AI agents can be brought into specific project rooms, scoping their context and file access to the task at hand.
*   **Persistent Organization**: Groups provide a clear and intuitive way to organize projects and their associated data.
*   **Simplified Access Control**: Implements a robust, group-based permission model via filesystem paths, which is a foundational element for a multi-user OS that fits the existing architecture.
*   **Scalability**: Allows the system to scale to more users and projects without creating a chaotic, single-channel communication environment.
