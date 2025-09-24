# /bin/ll.py
**Description:** The `ll` command lists files and directories. It is an alias for `ls -l`. Its default behavior is to list directory contents with each entry on a new line. While it doesn't currently display full file metadata (like permissions, owner, size, or modification date), this per-line output distinguishes it from the default `ls` command, which typically prints multiple entries on a single line.

**Usage:** `/bin/ll.py [PATH...]`

**Arguments:**
*   `[PATH...]`: Optional. The path(s) to list. Defaults to the root directory (`/`).
*   `-a`: Includes directory entries whose names begin with a dot (hidden files).
*   `-l`: (Implicit by `ll`) Lists in long format, ensuring one entry per line.
*   `--help`: Displays detailed help information.

**Examples:**

1.  **Standard execution (no arguments):**
    *   Command: `$ ll`
    *   Output: Lists contents of the root directory, with each item on a new line.
        ```
        /bin/
        /dev/
        /doc/
        /etc/
        /home/
        /sbin/
        /src/
        /var/
        ```

2.  **Execution with a specific path:**
    *   Command: `$ ll /bin`
    *   Output: Lists contents of `/bin`, with each item on a new line.
        ```
        /bin/ask.py
        /bin/attach.py
        ... (etc)
        ```

3.  **Execution with `-a` flag:**
    *   Command: `$ ll -a /`
    *   Output: Lists all files in `/`, including hidden ones (`.` and `..`), with each item on a new line.
        ```
        ./
        ../
        /bin/
        /dev/
        ...
        ```

4.  **Execution with `-l` flag:**
    *   Command: `$ ll -l /`
    *   Output: Identical to `$ ll` (no arguments), as `ll` itself represents the `-l` behavior of `ls`.
        ```
        /bin/
        /dev/
        /doc/
        /etc/
        /home/
        /sbin/
        /src/
        /var/
        ```

**Error Handling:**
*   **Non-existent Path:** When a specified path does not exist, the command correctly reports an error.
    *   Example: `$ ll /nonexistent_path`
    *   Output: `!! ls: path does not exist: /nonexistent_path`

**Notes:**
*   **Help Text Discrepancy:** The `--help` output currently displays a comprehensive GNU `ls` help page. It is unclear how many of the numerous flags listed in this generic help are actually implemented or supported within the IOSK `ll` command.
*   **Long Format Details:** While `ll` (as `ls -l`) prints one entry per line, it does not currently display additional file metadata like permissions, owner, group, or size, as a traditional UNIX `ls -l` would. Its primary "long format" characteristic is the per-line output.

**Status:** Working. The core listing functionality, including the `-a` flag, operates correctly with each entry on a new line. The previous "Multiple Output Bug" has been resolved. The primary remaining points are the lack of detailed metadata in the "long format" and the generic nature of the `--help` output.
