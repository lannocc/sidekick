# Proposal: Mounted Media Mode for IOSK Workspaces

**Status**: Implemented

### Introduction

The existing filesystem overlay provides a robust separation between the core IOSK **Distribution** and a writable **Workspace**. However, this model still combines the user's project files and IOSK's own runtime state (logs, caches, tombstones for system files) within a single workspace directory.

This proposal introduces an optional "Mounted Media Mode" (3M) that further refines this separation. By specifying a virtual mount point, users can treat their workspace directory as a clean, mounted volume within IOSK. All of IOSK's internal state changes will be transparently redirected to a hidden subdirectory, keeping the user's primary directory pristine and free of system-specific metadata.

The command syntax will be extended to: `iosk <workspace_directory> [<mount_point>]`. When the optional `<mount_point>` is provided, 3M is enabled.

### Core Concepts

This mode builds upon the existing overlay by splitting the single "Workspace" layer into two distinct writable locations on the host filesystem.

1.  **Distribution (Base Layer)**: Unchanged. This remains the read-only, canonical set of IOSK system files (`/bin`, `/etc`, etc.) bundled with the Python package.

2.  **User Media (The Workspace Directory)**: This is the user-provided `<workspace_directory>` on the host filesystem. In 3M, it is virtually "mounted" at the specified `<mount_point>`. It serves as the destination for all write operations that occur **at or below** the virtual mount point.

3.  **System Workspace (Sub-Workspace)**: This is a new, hidden directory named `.iosk` created inside the User Media directory (e.g., `<workspace_directory>/.iosk`). It serves as the destination for all write operations that occur **outside** the virtual mount point. This includes system logs, caches, temporary files, and tombstones for non-mounted system files.

4.  **Merged View**: The filesystem presented to the user is a merged view of all layers.
    *   **Split Writes**: Write operations are intelligently routed based on the target virtual path.
        *   A write to `/mnt/foo/my_file.txt` (assuming a mount point of `/mnt/foo`) will be directed to the User Media.
        *   A write to `/var/log/system.log` (outside the mount point) will be directed to the System Workspace.
    *   **Layered Reads**: For read operations, the filesystem checks for a file's existence in a specific order of precedence:
        1.  If the path is under the mount point, the **User Media** is checked first. If not found, quit here (for paths under the mount point).
        2.  The **System Workspace** is checked next for all paths.
        3.  Finally, the system falls back to the base **Distribution**.
    *   **Merged Directories**: Directory listings combine the contents from all relevant layers, with files in higher-precedence layers shadowing those in lower ones.

### Use Case Scenario

1.  A user has a project folder on their host machine and wants to work on it within IOSK without polluting it.
    ```bash
    host$ mkdir my_project
    host$ echo "This is my data." > my_project/data.txt
    host$ iosk ./my_project /media/project
    ```
2.  IOSK starts in 3M. The kernel sets:
    *   User Media (`workspace_root`): `./my_project`
    *   Mount Point: `/media/project`
    *   System Workspace: `./my_project/.iosk`
3.  The user lists the contents of their mounted project.
    ```
    [root /] $ ls /media/project
    data.txt
    ```
    This correctly lists the contents of the `./my_project` directory from the host.
4.  The user creates a new file within their project and modifies a system configuration file.
    ```
    [root /] $ touch /media/project/new_file.txt
    [root /] $ echo "new_hostname" > /etc/hostname
    ```
5.  The user also "deletes" a default system command.
    ```
    [root /] $ rm /bin/ls.py
    ```
6.  After the user exits IOSK, they inspect their project directory on the host.
    ```bash
    host$ ls -aR my_project
    my_project:
    .
    ..
    .iosk
    data.txt
    new_file.txt
    
    my_project/.iosk:
    .
    ..
    bin
    etc
    var
    
    my_project/.iosk/bin:
    .
    ..
    .iosk.rm.ls.py
    
    my_project/.iosk/etc:
    .
    ..
    hostname
    
    my_project/.iosk/var:
    ... (log files, cache, etc.) ...
    ```
    The user's directory `my_project` remains clean, containing only the files they explicitly created there. All system modifications and metadata (the new hostname file, the tombstone for `ls.py`, and any logs) are neatly contained within the hidden `.iosk` subdirectory.

### Benefits

*   **Pristine User Media**: The user's primary directory is not cluttered with IOSK's state files (`/var`, `/tmp`, tombstones for system files). It only contains the files and directories the user would expect to see.
*   **Enhanced Portability**: The user's directory can be zipped, committed to Git, or used with other tools without IOSK's metadata getting in the way. The `.iosk` folder contains all the system-specific state and can be safely ignored or deleted to "reset" the IOSK environment for that project.
*   **Intuitive Mounting**: The concept mimics the behavior of mounting a disk or drive, which is a familiar paradigm for developers. The mounted directory behaves as the primary "data" volume, while the rest of the filesystem provides the "operating system."

### Implementation Strategy

#### 1. Launcher and Kernel Initialization
*   **`sk/iosk/cmd.py`**: The `run` function will be updated to parse an optional second argument for the `mount_point`. It will pass `workspace_root` and `mount_point` (or `None`) to the kernel.
*   **`sk/iosk/kernel.py`**: The `IOSK.__init__` method will be updated to `__init__(self, workspace_root, mount_point=None)`.
    *   It will store `self.mount_point`.
    *   It will introduce a new property, `self.system_workspace_root`.
    *   If `mount_point` is `None` (standard mode), `self.system_workspace_root` will point to `self.workspace_root`.
    *   If `mount_point` is set (3M mode), `self.system_workspace_root` will point to `<workspace_root>/.iosk`. The kernel will be responsible for creating this directory at startup.

#### 2. Filesystem Manager (`fs.py`) Updates
The `FileSystemManager` will be modified to handle the split writable layer.

*   **`box_for_write(virtual_path)`**: This method will contain the core routing logic for writes.
    *   If `self.os.mount_point` is set and the given `virtual_path` is at or under the mount point:
        1.  Calculate the path relative to the mount point (e.g., `/media/project/foo` -> `foo`).
        2.  Return the host path by joining this relative path with `self.os.workspace_root`.
    *   Otherwise:
        1.  Return the host path by joining the virtual path with `self.os.system_workspace_root`.

*   **`box(virtual_path)`**: The read path resolution logic will be updated to check all three potential locations in the correct order.
    1.  If in 3M mode and the path is under the mount point, check for the file within the `self.os.workspace_root`.
    2.  Check for the file within `self.os.system_workspace_root`.
    3.  If not found in either writable layer, fall back to `self.os.dist_root`.

*   **`list_dir(virtual_path)`**: The directory merging logic must be expanded.
    1.  Gather items from the base **Distribution**.
    2.  Gather items from the **System Workspace** and merge them, overwriting any distribution items with the same name.
    3.  If in 3M and the `virtual_path` is at or under the mount point, gather items from the corresponding path in the **User Media** and merge them, overwriting any items from the previous layers.
    4.  Apply tombstone filtering. The logic must check for tombstones in the location determined by the `box_for_write` logic.

### Implementation Plan (Batch Jobs)

1.  **Job 1: Update Launcher and Kernel**
    *   **Goal**: Handle the new optional `mount_point` argument and set up the necessary paths in the kernel.
    *   **Files**: `sk/iosk/cmd.py`, `sk/iosk/kernel.py`.

2.  **Job 2: Implement Write Path Splitting**
    *   **Goal**: Implement the core logic in `fs.py` to route write operations to either the User Media or the System Workspace.
    *   **Files**: `sk/iosk/fs.py` (focus on modifying `box_for_write` and ensuring `create`, `copy`, `remove`, etc., function correctly with it).

3.  **Job 3: Implement Multi-Layer Read and List Logic**
    *   **Goal**: Update read-path resolution and directory listing to account for the three-layer view (User Media, System Workspace, Distribution).
    *   **Files**: `sk/iosk/fs.py` (focus on modifying `box` and `list_dir`).

