# Proposal: Codebase Refactoring and Reorganization

**Status**: Proposed

### Introduction

The IOSK codebase has grown to support a rich set of features, including a virtual filesystem, process management, multi-user chat, and a sophisticated networking mesh. As the system evolves, it is crucial to maintain a high standard of code quality to ensure long-term maintainability, readability, and ease of understanding for both human developers and AI agents that interact with the code.

This proposal outlines a series of refactoring initiatives aimed at improving the internal structure of the codebase. The core principle of this effort is to **make these changes without altering any existing functionality**. The goals are to reduce code duplication, improve logical cohesion by grouping related functionality, and decompose large, monolithic classes into smaller, more focused components. These changes will result in a cleaner, more modular, and more efficient codebase.

### Core Refactoring Areas

#### 1. Centralized Utility Module (`src/iosk/util.py`)

Several pieces of common, reusable logic are currently duplicated across multiple command files. We propose creating a new utility module, `src/iosk/util.py`, to centralize this code.

*   **ANSI Color Codes**: The ANSI color maps (`COLOR_MAP`, `REVERSE_COLOR_MAP`) are defined in both `bin/color.py` and `bin/colors.py`. These will be moved to `src/iosk/util.py` and imported by the commands that need them.

*   **Time Formatting**: The commands `bin/ps.py`, `bin/top.py`, and `bin/uptime.py` each contain slightly different helper functions for formatting `timedelta` objects into human-readable strings. These will be consolidated into a single, robust function within the new utility module.

*   **Remote Command Dispatching**: The commands `bin/attach.py`, `bin/detach.py`, `bin/pause.py`, and `bin/unpause.py` share an identical block of code for parsing `user.host` arguments and dispatching the command to a remote peer if necessary. This logic will be extracted into a single helper function, `dispatch_remote_if_needed`, within `src/iosk/util.py`. The commands will call this helper, and if it returns `True` (indicating the command was dispatched), they will exit; otherwise, they will proceed with local execution.

#### 2. Decomposing Core Kernel and PortManager Classes

The `src/iosk/kernel.py` and `src/iosk/port.py` files have become excessively large, handling too many distinct responsibilities. This violates the single-responsibility principle and makes the code difficult to navigate and understand.

*   **Kernel Decomposition (`src/iosk/kernel.py`)**: We propose breaking the `IOSK` class into a primary coordinator class that composes several smaller, focused manager classes.
    *   `src/iosk/fs.py`: A new `FileSystemManager` class will encapsulate all virtual filesystem operations (`box`, `exists`, `get`, `copy`, `move`, `create`, `remove`, etc.).
    *   `src/iosk/users.py`: A new `UserManager` class will handle the user lifecycle, including `login`, `logout`, and the `interactive` session loop.
    *   `src/iosk/proc.py`: A new `ProcessManager` class will manage the process table, PID assignment, and the command execution lifecycle (`_execute_single_command`).
    The main `IOSK` class will instantiate these managers (e.g., `self.fs = FileSystemManager(...)`) and delegate calls accordingly.

*   **PortManager Decomposition (`src/iosk/port.py`)**: The `PortManager` class contains a large number of `_handle_...` methods for different client message types.
    *   We will move these handlers into a dedicated `src/iosk/port_handlers.py` module. The main `_dispatch_message` method in `PortManager` will become a simple router that calls the appropriate function from the new handlers module, making the primary class focus purely on connection lifecycle and routing.

#### 3. Consolidating Redundant Logic

*   **User Pause/Unpause Commands**: The commands `bin/pause.py` and `bin/unpause.py` are nearly identical, differing only in the boolean value they set and the confirmation message.
    *   **Proposal**: We will create a single internal helper function, `async def set_user_pause_state(io, target_user_str, should_pause: bool)`, which will contain all the shared logic (remote dispatch, user validation, state change, broadcasting). The `pause.py` and `unpause.py` scripts will be reduced to simple one-line calls to this new helper function, eliminating ~90% of the duplicated code.

*   **User Session Initialization**: The logic for creating home directories, copying the `.skrc` file from `/etc/skel`, displaying the MOTD, and initializing user colors is currently duplicated with minor variations across `kernel.login` (for local console users) and `kernel.login_network_user` (for remote client users).
    *   **Proposal**: We will create a single, unified internal method, `async def _initialize_user_context(self, io: Context)`, within the `UserManager` (from decomposition step 3). This method will perform all common setup tasks. Both the local and network login functions will call this helper after creating the user's `Context` object, ensuring a consistent and DRY setup process for all user types.

### Benefits

Implementing these refactoring changes will yield significant benefits:
*   **Improved Maintainability**: With reduced duplication and better organization, future changes will be easier and safer to implement.
*   **Enhanced Readability**: Smaller, single-responsibility modules are easier for developers and AI agents to read, understand, and reason about.
*   **Reduced Code Footprint**: Eliminating boilerplate files and redundant logic will decrease the overall size of the codebase.
*   **Increased Consistency**: Centralizing common logic (e.g., user setup, remote dispatch) ensures that all parts of the system behave consistently.

