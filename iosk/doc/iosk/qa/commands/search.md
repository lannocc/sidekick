# /bin/search.py
**Description:** Searches for a specified term within text files, with various options for output formatting.
**Usage:** `/bin/search.py [-i] [-n] [-l] [-c] <term> [path ...]`
**Options:**
*   `-i`: Case-insensitive search.
*   `-n`: Show line numbers (with normal output).
*   `-l`: List filenames with matches (suppress matched lines).
*   `-c`: Print count of matches per file.
*   `--help`: Show this help message.
**Notes:**
*   No quoting is supported; `<term>` cannot contain spaces.
*   If no paths are provided, defaults to `/home/<user>` if it exists; otherwise "/".
**Example:**
To search for the term "iosk" in the file `/doc/iosk/chat.md` and display the matching lines:
`/bin/search.py iosk /doc/iosk/chat.md`
**Output:**
```
/doc/iosk/chat.md/chat.md: *   `__init__(self, iosk)`:
/doc/iosk/chat.md/chat.md:     *   Initializes the `AIMessenger` with an IOSK instance (`iosk`).
/doc/iosk/chat.md/chat.md:     *   Sets `iosk.chat` to `self` to establish a bidirectional link.
```
**Status:** Working.
