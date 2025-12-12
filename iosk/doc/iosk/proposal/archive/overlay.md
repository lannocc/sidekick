# Proposal: Filesystem Overlay for IOSK Workspaces

**Status**: Implemented

### Introduction

Currently, the IOSK system runs by targeting its own source directory as the root filesystem (e.g., `iosk iosk`). This model is simple for development but inflexible for deployment and user customization. It treats the core system files and the user's runtime data as a single, monolithic entity.

This proposal outlines a filesystem overlay mechanism that separates the core IOSK **Distribution** (the immutable set of system files like `/bin`, `/etc`, etc.) from a user-provided **Workspace** (a writable directory for user files, logs, and customizations).

When IOSK is started against a workspace directory, it will present a merged, virtual view of the filesystem. Files and directories in the workspace will augment or take precedence over items in the base distribution. This allows users to run IOSK in any directory, customize its behavior by adding or replacing files, and keep their work cleanly separated from the core system, all without modifying the original distribution.

### Core Concepts

1.  **Distribution (Base Layer)**: This is the read-only, canonical set of IOSK system files (`/bin`, `/sbin`, `/etc`, etc.). This layer will be bundled with the installed Python package, making it easily locatable and preventing accidental modification.

2.  **Workspace (Top Layer)**: This is a user-specified directory on the host filesystem. It is fully writable. Any files created or modified by the user or by IOSK commands during a session are stored here.

3.  **Merged View**: IOSK's internal filesystem commands (`ls`, `cat`, `cd`, etc.) operate on a virtual, merged view of the distribution and the workspace.
    *   **File Shadowing**: For read operations, if a file exists in the workspace, it is always used, effectively "shadowing" or "masking" any file with the same name in the distribution. If the file is not in the workspace, the system falls back to the distribution.
    *   **Directory Merging**: For directory listings, the contents of the workspace and distribution directories at the same virtual path are combined. The final view contains all items from both, with workspace files shadowing distribution files of the same name. An empty directory in the workspace does *not* hide the contents of the corresponding distribution directory.
    *   **Workspace-Only Writes**: All write operations (`touch`, `mkdir`, `cp` destination, etc.) *always* target the workspace, ensuring the distribution remains pristine.

4.  **Masking Deletions**: Since the distribution is read-only, deleting a distribution file cannot physically remove it. Instead, a "tombstone" file is created in the workspace. For example, `rm /bin/echo.py` would create an empty file at `workspace/bin/.rm.echo.py`. The kernel's directory listing logic will then hide `echo.py` from the merged view, making it appear deleted.

### Bundling the Distribution

To make the distribution easily and reliably accessible in a system-agnostic way, we will leverage Python's packaging infrastructure. The core system directories (`bin`, `sbin`, `etc`, `dev`) will be kept in their current location but explicitly included in the final package.

*   **Package Data**: The `setup.py` file will be configured with a `package_data` entry. This explicitly tells `setuptools` to find the `bin`, `sbin`, `etc`, and `dev` directories and bundle them into the package distribution (wheel/sdist). This avoids the need to move the source files into a special `dist` subdirectory.

*   **Runtime Location**: When the `sk` package is installed via `pip`, we can use Python's `importlib.resources` to locate the bundled distribution files dynamically at runtime. This approach avoids hardcoded paths and ensures the system works identically in a dev environment or an installed environment.

### A Note on Developer Workflow

The overlay system is designed to be flexible. For developers working directly on the IOSK distribution, the workflow remains straightforward. We always specify a workspace, and in this case, it can be the project's source root itself.

When `iosk` is launched with the source root as the workspace, the distribution and workspace layers become one and the same. The kernel's `dist_root` and `workspace_root` will point to the same directory. The overlay logic handles this gracefully: any changes made are written directly to the source files, as they are part of both the 'base' and 'writable' layers. This allows for direct, live editing of the core distribution files.

### Implementation Strategy

#### 1. Kernel (`IOSK`) Initialization

The `IOSK` class constructor in `src/iosk/kernel.py` will be modified to accept the `workspace_root`. It will use `importlib.resources` (or a relative path fallback) to locate the bundled `dist_root`.

#### 2. Modifying `fs.py` (The Overlay Engine)

The `FileSystemManager` class in `src/iosk/fs.py` is the primary location for this logic.

*   **`box(virtual_path)` (Read/General)**: This method currently maps a virtual path to a host path. It must be updated to check the Workspace first. If the file exists there, return the workspace path. Otherwise, return the Distribution path.
*   **`box_for_write(virtual_path)` (New)**: A new helper that *always* resolves to the Workspace path, regardless of whether the file exists.
*   **`list_dir`**: Must be rewritten to list both layers, merge the results (deduplicating keys), and filter out items that have a corresponding `.rm.<name>` tombstone file in the workspace.
*   **`remove`**: Must check the layer. If in Workspace, delete physically. If only in Distribution, create a tombstone in Workspace.
*   **`create`, `create_dir`, `copy`**: Must explicitly use the write-resolution logic to ensure they only affect the Workspace.

#### 3. Updating the Launcher

The entry point in `src/iosk/cmd.py` will be updated to accept the workspace directory argument and pass it to the Kernel.

### Implementation Plan (Batch Jobs)

This transition is divided into three logical batches for AI agents to process.

#### Job 1: The Overlay Engine (Core Logic)
**Goal:** Implement the virtual filesystem logic, tombstone handling, and kernel initialization.
**Files:**
1.  `iosk/src/iosk/kernel.py` (Update `__init__` to locate dist root vs workspace root).
2.  `iosk/src/iosk/fs.py` (Heavily modify `box`, `list_dir`, `remove`, `create`, `exists` to handle the 2-layer logic).
3.  `iosk/src/iosk/cmd.py` (Update arguments to accept workspace path).

#### Job 2: Packaging & Distribution Structure
**Goal:** Configure the packaging to bundle the core system directories without altering the source tree layout.
**Files:**
1.  `setup.py`: Add the `package_data` argument to explicitly include the `bin`, `sbin`, `dev`, and `etc` directories within the `sk` package's data. This ensures they are correctly bundled when the package is built and installed.

#### Job 3: Command Auditing & verification
**Goal:** Ensure core commands respect the new overlay logic. Most commands rely on `io.os.get` or `io.os.list_dir` (which call `fs.py`), so they should work automatically. However, commands that perform specific checks or file writes need verification.
**Files:**
1.  `iosk/bin/ls.py` (Verify it displays merged views correctly).
2.  `iosk/bin/rm.py` (Verify it handles tombstones/masking).
3.  `iosk/bin/touch.py` (Verify it writes to workspace).
4.  `iosk/bin/cp.py` (Verify destination is workspace).
5.  `iosk/bin/describe.py` (Verify it resolves the correct file layer).
6.  `iosk/bin/grep.py` (Verify recursive search works across merged layers).

### Use Case Scenario

1.  A user starts a new project.
    ```bash
    host$ mkdir my-project
    host$ iosk my-project
    ```
2.  IOSK starts. The kernel sets `workspace_root` to `my-project` and `dist_root` to the bundled package data.
3.  The user lists the `/bin` directory.
    ```
    [root /] $ ls /bin
    alias.py    ask.py    attach.py    ...    whoami.py    xargs.py
    ```
    The `list_dir` method found no `/bin` in `my-project` and listed the contents from the bundled distribution.
4.  The user decides to customize the `welcome` message by shadowing the distribution file.
    ```
    [root /] $ echo "#!/bin/skrip\nWelcome to My Project!" > /bin/welcome
    ```
    This write operation is routed to `my-project/bin/welcome`. The original distribution `welcome` file is untouched.
5.  The user now "deletes" a command they don't want.
    ```
    [root /] $ rm /bin/ask.py
    ```
    The system sees that `/bin/ask.py` exists only in the distribution and creates a tombstone file at `my-project/bin/.rm.ask.py`.
6.  The user lists `/bin` again to see the merged and masked result.
    ```
    [root /] $ ls /bin
    alias.py    attach.py    ...    welcome    whoami.py    xargs.py
    ```
    The `list_dir` method has merged the directory contents. `ask.py` is now hidden because of the tombstone, and `welcome` is listed (representing the shadowed file from the workspace).
7.  The user lists the project directory from the host shell after exiting.
    ```bash
    host$ ls -aR my-project
    my-project:
    bin

    my-project/bin:
    .rm.ask.py
    welcome
    ```
    The workspace contains only the user's modifications: the shadowed `welcome` file and the tombstone for `ask.py`. The rest of the system was provided virtually by the overlay.

### Benefits

*   **Clean Separation**: User data and customizations are cleanly separated from the core system files, making workspaces portable and self-contained.
*   **Immutability**: The core IOSK distribution remains untouched and can be updated via `pip` without affecting user workspaces.
*   **Customization**: Users can easily override any system script or configuration file by simply creating a file at the same path in their workspace.
*   **Ease of Use**: Starting a new, clean IOSK environment is as simple as creating an empty directory.
*   **System Agnostic**: This approach relies only on standard Python libraries and works identically across all supported operating systems.
