# Proposal: Filesystem Overlay for IOSK Workspaces

**Status**: Proposed

### Introduction

Currently, the IOSK system runs by targeting its own source directory as the root filesystem (e.g., `iosk iosk`). This model is simple for development but inflexible for deployment and user customization. It treats the core system files and the user's runtime data as a single, monolithic entity.

This proposal outlines a filesystem overlay mechanism that separates the core IOSK **Distribution** (the immutable set of system files like `/bin`, `/etc`, etc.) from a user-provided **Workspace** (a writable directory for user files, logs, and customizations).

When IOSK is started against a workspace directory, it will present a merged, virtual view of the filesystem. Files in the workspace will take precedence over, or "overlay," the files in the base distribution. This allows users to run IOSK in any directory, customize its behavior by adding or replacing files, and keep their work cleanly separated from the core system, all without modifying the original distribution.

### Core Concepts

1.  **Distribution (Base Layer)**: This is the read-only, canonical set of IOSK system files (`/bin`, `/sbin`, `/etc`, etc.). This layer will be bundled with the installed Python package, making it easily locatable and preventing accidental modification.

2.  **Workspace (Top Layer)**: This is a user-specified directory on the host filesystem. It is fully writable. Any files created or modified by the user or by IOSK commands during a session are stored here.

3.  **Merged View**: IOSK's internal filesystem commands (`ls`, `cat`, `cd`, etc.) will operate on a virtual, merged view of the distribution and the workspace.
    *   **For reading files**: If a path exists in the workspace (e.g., `workspace/bin/echo.py`), it is used. If not, the system falls back to the corresponding path in the distribution (`dist/bin/echo.py`).
    *   **For listing directories**: The contents of the workspace directory and the distribution directory are merged, with workspace files replacing distribution files of the same name.
    *   **For writing files**: All write operations (`touch`, `mkdir`, `cp` destination, etc.) *always* target the workspace, ensuring the distribution remains pristine.

### Bundling the Distribution

To make the distribution easily and reliably accessible in a system-agnostic way, we will leverage Python's packaging infrastructure.

-   **Package Data**: The core IOSK directories (`bin`, `sbin`, `etc`, `doc`, `src/iosk/dev`) will be included in the `sk` package distribution as `package_data`. This is configured in `pyproject.toml` or `setup.cfg`.
-   **Runtime Location**: When the `sk` package is installed via `pip`, these files are placed within the `site-packages` directory. We can use Python's standard `importlib.resources` library to get the filesystem path to this "distribution" root at runtime, regardless of the operating system or environment.

This approach avoids hardcoded paths and the complexity of managing separate `tar` archives. The distribution is self-contained within the installed package.

### Implementation Strategy

#### 1. Kernel (`IOSK`) Initialization

The `IOSK` class constructor in `src/iosk/kernel.py` will be modified.

-   **`__init__(self, workspace_root: str)`**: The constructor will now accept a single path to the user's workspace.
-   **Path Discovery**: Inside `__init__`, it will perform two key actions:
    1.  Store the absolute path to the provided `workspace_root`.
    2.  Use `importlib.resources` to find the path to the bundled distribution data and store it as `self.dist_root`.

    ```python
    # Conceptual change in src/iosk/kernel.py
    import os
    from importlib.resources import files

    class IOSK:
        def __init__(self, workspace_root: str):
            self.workspace_root = os.path.abspath(workspace_root)

            # 'sk.iosk.dist' would be a package containing the data files
            # Requires adding an __init__.py to the distribution root.
            # For this example, we'll assume the data is alongside the 'iosk' package.
            # A more realistic path might be found relative to a known module.
            # Let's assume the data is bundled within a submodule `sk.dist`.
            try:
                self.dist_root = str(files('sk') / 'dist') # Example path
            except ModuleNotFoundError:
                # Fallback for development environments
                # This logic can be refined.
                self.dist_root = os.path.abspath(os.path.dirname(__file__) + '/../..')


            self.started = None
            # ... rest of __init__
    ```

#### 2. Modifying `kernel.box()` for Read Operations

The `box()` method is the heart of the virtual filesystem. It will be updated to implement the overlay logic for read operations.

```python
# In src/iosk/kernel.py

def box(self, virtual_path_input: str, io_context=None) -> str:
    # (Existing logic to resolve virtual_path_input to an absolute virtual path)
    # ...
    # normalized_virtual_path is the result (e.g., '/bin/ls.py')

    path_relative_to_root = normalized_virtual_path.lstrip('/')
    path_components = path_relative_to_root.split('/')

    # 1. Check Workspace first (top layer)
    workspace_host_path = os.path.join(self.workspace_root, *path_components)
    if os.path.exists(workspace_host_path):
        return os.path.abspath(workspace_host_path)

    # 2. Fallback to Distribution (base layer)
    dist_host_path = os.path.join(self.dist_root, *path_components)
    # We return this path even if it doesn't exist, letting the caller handle "not found".
    return os.path.abspath(dist_host_path)
```

#### 3. Handling Write Operations

Any kernel method that performs a write operation must be modified to *unambiguously* target the workspace. This is a critical rule: **never write to the distribution**.

```python
# In src/iosk/kernel.py

# A new helper method for write paths
def _box_for_write(self, virtual_path_input: str, io_context=None) -> str:
    # (Logic to resolve to normalized_virtual_path)
    # ...
    path_relative_to_root = normalized_virtual_path.lstrip('/')
    path_components = path_relative_to_root.split('/')
    # Always join with the workspace root
    return os.path.abspath(os.path.join(self.workspace_root, *path_components))

# Example modification in a write method
async def create_dir(self, io:Context, path:str, parents=False):
    """Create new directory."""
    folder = self._box_for_write(path, io_context=io) # Use the write-specific boxer
    if exists(folder):
        await io.error(f'!! path already exists: {path}')
        return False
    # ... rest of the method
```
This pattern would be applied to `create`, `copy` (for the destination path), `move` (destination), `remove`, `rmdir`, `mkdir`, and any file handles opened for writing.

#### 4. Merging Directory Listings

Commands like `ls` and `tree` rely on `os.listdir`. The kernel's `list_dir` method must be updated to present the merged view.

```python
# In src/iosk/kernel.py

async def list_dir(self, io: Context, path: str) -> list:
    """Lists the merged contents of a directory from the workspace and distribution."""
    # Resolve paths for both layers
    workspace_dir = self._box_for_write(path, io_context=io) # Path in workspace
    dist_dir = os.path.join(self.dist_root, path.lstrip('/')) # Path in distribution

    merged_items = {} # Use dict to handle overwrites naturally

    # 1. List items from the distribution (base layer)
    if os.path.isdir(dist_dir):
        for item_name in sorted(os.listdir(dist_dir)):
            merged_items[item_name] = {'source': 'dist', 'name': item_name, ...}

    # 2. List items from the workspace (top layer), overwriting if names conflict
    if os.path.isdir(workspace_dir):
        for item_name in sorted(os.listdir(workspace_dir)):
            merged_items[item_name] = {'source': 'workspace', 'name': item_name, ...}

    # 3. Return a sorted list of the final values
    return sorted(list(merged_items.values()), key=lambda x: x['name'])
```

#### 5. Updating the Launcher

The entry point in `src/iosk/cmd.py` will be changed to accept the workspace directory.

```python
# In src/iosk/cmd.py
def run(args=sys.argv[1:]):
    # ...
    if len(args) != 1 or args[0].startswith('-'):
        print("Usage: iosk <workspace_directory>") # Updated usage
        sys.exit(1)

    workspace_directory = args[0]
    # ...
    kernel = UNIX(root=workspace_directory) # The 'root' is now the workspace
    # ...
```

### Use Case Scenario

1.  A user wants to start a new project.
    ```bash
    host$ mkdir my-project
    host$ iosk my-project
    ```
2.  IOSK starts. The kernel sets `workspace_root` to the absolute path of `my-project` and finds the `dist_root` inside the installed `sk` package. The user is logged in.
3.  The user lists the `/bin` directory.
    ```
    [root /] $ ls /bin
    alias.py    ask.py    attach.py    ...    whoami.py    xargs.py
    ```
    The `list_dir` method found no `/bin` in `my-project`, so it listed the contents from `dist/bin`.
4.  The user decides to customize the `welcome` message.
    ```
    [root /] $ echo "#!/bin/skrip\nWelcome to My Project!" > /bin/welcome
    ```
    This write operation is routed to `my-project/bin/welcome`. The original `dist/bin/welcome` is untouched.
5.  The user runs the `welcome` command.
    ```
    [root /] $ welcome
    Welcome to My Project!
    ```
    The `kernel.box('/bin/welcome')` call first checks `my-project/bin/welcome`, finds it, and returns that path for execution. The distribution version is shadowed.
6.  The user lists the project directory from the host shell after exiting.
    ```bash
    host$ ls -R my-project
    my-project:
    bin

    my-project/bin:
    welcome
    ```
    Only the custom file exists in the workspace. The rest of the system was provided virtually by the overlay.

### Benefits

*   **Clean Separation**: User data and customizations are cleanly separated from the core system files, making workspaces portable and self-contained.
*   **Immutability**: The core IOSK distribution remains untouched and can be updated via `pip` without affecting user workspaces.
*   **Customization**: Users can easily override any system script or configuration file by simply creating a file at the same path in their workspace.
*   **Ease of Use**: Starting a new, clean IOSK environment is as simple as creating an empty directory.
*   **System Agnostic**: This approach relies only on standard Python libraries (`os.path`, `importlib.resources`) and works identically across all supported operating systems.

