# /bin/send.py
**Description:** Reads content from one or more files, or from standard input, and sends it as a raw text message to other users in the current chat room. The sender sees a confirmation and a copy of the sent content in their own session.
**Usage:**
  - `send <file>...`
  - `... | send`
  - `send --help`

**Test Cases:**

1.  **Send from a single file:**
    -   **Setup:** `echo "Hello from file" > /home/beta/send_test.txt`
    -   **Command:** `$ send /home/beta/send_test.txt`
    -   **Sender's Output:**
        ```
        :: content sent to chat.
        --- You sent ---
        Hello from file

        ----------------
        ```
    -   **Receiver's Output:** A chat message from the sender containing "Hello from file".
    -   **Verification:** The sender sees the confirmation, and other users see the message.

2.  **Send from multiple files:**
    -   **Setup:**
        - `echo "File A content." > /home/beta/file_a.txt`
        - `echo "File B content." > /home/beta/file_b.txt`
    -   **Command:** `$ send /home/beta/file_a.txt /home/beta/file_b.txt`
    -   **Sender's Output:**
        ```
        :: content sent to chat.
        --- You sent ---
        File A content.File B content.
        ----------------
        ```
    -   **Receiver's Output:** A chat message containing the concatenated content of both files.

3.  **Send from piped input:**
    -   **Command:** `$ ls /bin | grep .py$ | send`
    -   **Sender's Output:** `:: content sent to chat.` followed by a copy of the output of the `grep` command.
    -   **Receiver's Output:** A chat message containing the list of `.py` files from `/bin`.

4.  **Send content containing special characters:**
    -   **Setup:** `echo '$ echo "This should not be run"\n# a comment' > /home/beta/special.txt`
    -   **Command:** `$ send /home/beta/special.txt`
    -   **Receiver's Output:** A chat message containing the literal text `$ echo "This should not be run"\n# a comment`.
    -   **Verification:** A receiving AI agent should treat this as text from another user and not attempt to execute the command or interpret the comment.

5.  **Error case: file not found:**
    -   **Command:** `$ send /home/beta/non_existent_file.txt`
    -   **Sender's Output:** `!! path not found: /home/beta/non_existent_file.txt`
    -   **Verification:** No message is sent to other users, and the command returns a failure status.

**Status:** Working.

