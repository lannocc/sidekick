# Command: mv

## Description
The `mv` command is used to move or rename files and directories.

## Usage
`$ mv SOURCE DESTINATION`

## Arguments
-   `SOURCE`: The source file or directory to move.
-   `DESTINATION`: The destination path or new name.

## Behavior
-   If `DESTINATION` is an existing directory, `SOURCE` is moved into it.
-   If `DESTINATION` is a filename, `SOURCE` is renamed to `DESTINATION`.
-   The core functionality of moving and renaming files works as expected.

## Edge Cases and Bugs
-   **CRITICAL: Output Duplication/Escalation:** Like other commands (`ls`, `mkdir`), `mv` suffers from a severe bug where its output is repeated multiple times. The number of repetitions appears to increase with each subsequent command executed in the session. The final test case resulted in an exception after numerous repeated errors.
-   **Inconsistent Error Messages:** When attempting to move a file to a non-existent directory, the command outputs multiple, different error messages before finally throwing a generic exception. This indicates poor and confusing error handling.
-   **Example of repeated output (success):**
    ```
    $ mv /path/to/file /new/path/
    :: path moved
    :: path moved
    ```
-   **Example of repeated output (failure):**
    ```
    $ mv /path/to/file /nonexistent/
    !! mv: target '/nonexistent/' is not a directory
    !! mv: cannot move '/path/to/file' to '/nonexistent/': No such file or directory
    ... (repeated many times) ...
    !! exception calling mv
    ```

## Test Cases
1.  **Move file to directory:**
    -   **Command:** `$ mv /home/beta/workspace/move_me.txt /home/beta/workspace/test_dir/`
    -   **Expected Output:** A single confirmation message `:: path moved`. The file should be moved.
    -   **Actual Output:** `:: path moved` was printed twice. The file was moved correctly.
    -   **Result:** PASS (functionality), FAIL (output bug).

2.  **Rename file:**
    -   **Command:** `$ mv /home/beta/workspace/test_file.md /home/beta/workspace/renamed_file.md`
    -   **Expected Output:** A single confirmation message `:: path moved`. The file should be renamed.
    -   **Actual Output:** `:: path moved` was printed four times. The file was renamed correctly.
    -   **Result:** PASS (functionality), FAIL (output bug escalation).

3.  **Move to non-existent directory:**
    -   **Command:** `$ mv /home/beta/workspace/renamed_file.md /nonexistent_dir/`
    -   **Expected Output:** A single, clear error message.
    -   **Actual Output:** A cascade of repeated, inconsistent error messages, culminating in an exception.
    -   **Result:** FAIL.
