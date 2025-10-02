# /bin/bank.py
**Description:** Loads a file's content into the user's memory banks. If the file has a shebang (e.g., `#!/bin/skrip`), it is executed and its output is captured. Otherwise, the raw file content is loaded directly. It supports various path resolutions and can also load content from standard input.
**Usage:**
  - `bank <path components...>`
  - `... | bank`
  - `bank --help`

**Test Cases:**

1.  **Bank from `/bank` (executed skrip):**
    -   **Command:** `$ bank role devops`
    -   **Output:** `:: memory bank loaded from '/bank/role/devops' (executed)`
    -   **Verification:** `$ banks` shows `/bank/role/devops` in the list.

2.  **Bank from an absolute path (executed skrip):**
    -   **Command:** `$ bank /etc/skrc`
    -   **Output:** `:: memory bank loaded from '/etc/skrc' (executed)`
    -   **Verification:** `$ banks` shows `/etc/skrc` in the list.

3.  **Bank from a relative path (executed skrip):**
    -   **Commands:**
        ```bash
        $ cd /bank/access
        $ bank ./admin
        ```
    -   **Output:** `:: memory bank loaded from '/bank/access/admin' (executed)`
    -   **Verification:** `$ banks` shows `/bank/access/admin` in the list.

4.  **Bank from a raw text file (no shebang):**
    -   **Setup:** `echo "Just some text." > /home/beta/raw.txt`
    -   **Command:** `$ bank /home/beta/raw.txt`
    -   **Output:** `:: memory bank loaded from '/home/beta/raw.txt' (raw content)`
    -   **Verification:** `$ banks` shows `/home/beta/raw.txt` in the list. The content of this bank would be "Just some text."

5.  **Bank from piped input:**
    -   **Command:** `$ echo "Piped content" | bank`
    -   **Output:** `:: content piped into memory bank 'stdin-bank-...'` (UUID varies)
    -   **Verification:** `$ banks` shows the unique `stdin-bank-...` key in the list.

6.  **Non-existent path:**
    -   **Command:** `$ bank non/existent/path`
    -   **Output:** `!! path not found: /bank/non/existent/path`
    -   **Verification:** The command correctly reports an error.

**Status:** Working.

