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

*   **AI Prompt Formatting Constants**: The string literals used to structure parts of the AI's context, such as the banking/memory section, are currently hardcoded in multiple locations (`src/iosk/chat.py`, `src/iosk/kernel.py`, and `src/iosk/io.py`). This includes markers like `=== CORE RULES/MEMORY BEGIN ===`, `THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS REMEMBER:`, and `=== END   CORE RULES/MEMORY ===`. Any change to this formatting requires finding and updating all instances, which is error-prone. These will be consolidated into named constants within `src/iosk/util.py` to ensure consistency and ease of modification.

#### 2. Decomposing Core Kernel and PortManager Classes

The `src/iosk/kernel.py` and `src/iosk/port.py` files have become excessively large, handling too many distinct responsibilities. This violates the single-responsibility principle and makes the code difficult to navigate and understand.

*   **Kernel Decomposition (`src/iosk/kernel.py`)**: We propose breaking the `IOSK` class into a primary coordinator class that composes several smaller, focused manager classes.
    *   `src/iosk/fs.py`: A new `FileSystemManager` class will encapsulate all virtual filesystem operations (`box`, `exists`, `get`, `copy`, `move`, `create`, `remove`, etc.).
    *   `src/iosk/users.py`: A new `UserManager` class will handle the user lifecycle, including `login`, `logout`, and the `interactive` session loop.
    *   `src/iosk/proc.py`: A new `ProcessManager` class will manage the process table, PID assignment, and the command execution lifecycle (`_execute_single_command`).
    The main `IOSK` class will instantiate these managers (e.g., `self.fs = FileSystemManager(...)`) and delegate calls accordingly.

*   **PortManager Decomposition (`src/iosk/port.py`)**: The `PortManager` class contains a large number of `_handle_...` methods for different client message types.
    *   We will move these handlers into a dedicated `src/iosk/web.py` module. The main `_dispatch_message` method in `PortManager` will become a simple router that calls the appropriate function from the new handlers module, making the primary class focus purely on connection lifecycle and routing.

#### 3. Consolidating Redundant Logic

*   **User Pause/Unpause Commands**: The commands `bin/pause.py` and `bin/unpause.py` are nearly identical, differing only in the boolean value they set and the confirmation message.
    *   **Proposal**: We will create a single internal helper function, `async def set_user_pause_state(io, target_user_str, should_pause: bool)`, which will contain all the shared logic (remote dispatch, user validation, state change, broadcasting). The `pause.py` and `unpause.py` scripts will be reduced to simple one-line calls to this new helper function, eliminating ~90% of the duplicated code.

*   **User Session Initialization**: The logic for creating home directories, copying the `.skrc` file from `/etc/skel`, displaying the MOTD, and initializing user colors is currently duplicated with minor variations across `kernel.login` (for local console users) and `kernel.login_network_user` (for remote client users).
    *   **Proposal**: We will create a single, unified internal method, `async def _initialize_user_context(self, io: Context)`, within the `UserManager` (from decomposition step 3). This method will perform all common setup tasks. Both the local and network login functions will call this helper after creating the user's `Context` object, ensuring a consistent and DRY setup process for all user types.

#### 4. Explicit User Session State (`src/iosk/io.py`)

The `Context` class in `src/iosk/io.py` currently mixes two distinct types of data: long-lived, session-wide state that should be shared across all commands for a user, and transient, per-command state that is often unique to a single command or pipeline segment. This distinction is managed implicitly within the `Context.fork()` method, making it difficult to reason about data ownership and lifecycle.

*   **Problem**: When a command is executed, `io.fork()` is called. In the current implementation, some attributes like `env` are copied (`child.env = self.env.copy()`), making them unique to the child context. Others, like `aliases` and `history`, are shared by reference (`child.aliases = self.aliases`), meaning a child's modification affects the parent. This implicit behavior is subtle and error-prone. A "user session" is not a first-class concept in the code.

*   **Proposal**: We will introduce a new class, `UserSessionState`, to explicitly manage all shared, long-lived data for a user's session. The `Context` class will be refactored to hold a reference to this session state object and will only contain transient, per-command data.

    1.  **Create `UserSessionState` Class**: A new class will be created in `src/iosk/io.py`. It will contain all attributes that define a user's session.
        *   **Attributes to Move**: The following attributes will be moved from `Context` to `UserSessionState`:
            *   User Identity: `user`, `su`, `bot`, `paused`, `login_time`
            *   AI Context: `session_history`, `prompt_number`, `rolling_config`, `preamble_cache`
            *   User State: `banks`, `history` (command history), `aliases`
            *   Display/Telemetry: `user_colors`, `color_idx`, `token_stats`

    2.  **Refactor `Context` Class**: The `Context` class will be simplified to manage only per-command or transient state.
        *   **Attributes to Keep**:
            *   A new reference: `self.session: UserSessionState`
            *   System/Instance State: `os`, `dev`, `log`, `parent`, `cid`
            *   Per-Command State: `pwd`, `env`
            *   I/O State: `stdin`, `stdout`
            *   Staging State: `stage`, `pre`, `post`, `banking`

    3.  **Update `kernel.login()`**: When a user logs in, the `kernel` will create a single `UserSessionState` instance for that user. The user's "base" `Context` object will hold the first reference to it.

    4.  **Simplify `Context.fork()`**: The `fork()` method will become much simpler. It will create a new `Context`, pass the *same reference* to the parent's `UserSessionState` object, and perform a deep copy only for truly per-context attributes like `env`.

    5.  **Update Access Patterns**: Code throughout the system that accesses session-state will be updated to use the new pattern. For example, `io.history` will become `io.session.history`, and `io.user` will become `io.session.user`. Per-context state like `io.pwd` and `io.env` will remain unchanged.

*   **Benefits of this Change**:
    *   **Clarity**: The separation of concerns becomes explicit. It is immediately obvious whether a piece of data belongs to the entire session or just the current command.
    *   **Robustness**: Eliminates the possibility of bugs where a forked context accidentally modifies a parent's state that should have been isolated, or vice-versa.
    *   **Maintainability**: Adding new session-level features (e.g., session-wide settings) becomes a simple matter of adding a field to the `UserSessionState` class, without needing to modify the complex `fork()` logic.

### Benefits

Implementing these refactoring changes will yield significant benefits:
*   **Improved Maintainability**: With reduced duplication and better organization, future changes will be easier and safer to implement.
*   **Enhanced Readability**: Smaller, single-responsibility modules are easier for developers and AI agents to read, understand, and reason about.
*   **Reduced Code Footprint**: Eliminating boilerplate files and redundant logic will decrease the overall size of the codebase.
*   **Increased Consistency**: Centralizing common logic (e.g., user setup, remote dispatch) ensures that all parts of the system behave consistently.
