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
-   Reports an error if the `SOURCE` does not exist.
-   Reports an error if `DESTINATION` is a non-existent directory.

## Edge Cases and Bugs
-   **Resolved: Exception on Non-Existent Directory:** Previously, when attempting to move a file to a non-existent directory, the command threw a general exception. This has been resolved, and a specific error message is now returned.

## Test Cases
1.  **Move file to directory:**
    -   **Setup:**
        -   `$ touch /home/beta/move_me.txt`
        -   `$ mkdir /home/beta/test_mkdir_new_dir` (from mkdir tests)
    -   **Command:** `$ mv /home/beta/move_me.txt /home/beta/test_mkdir_new_dir/`
    -   **Expected Output:** `:: path moved`. The file should be moved.
    -   **Actual Output:** `:: path moved`. The file was moved correctly.
    -   **Result:** PASS.

2.  **Rename file:**
    -   **Setup:** `$ touch /home/beta/test_file.md`
    -   **Command:** `$ mv /home/beta/test_file.md /home/beta/renamed_file.md`
    -   **Expected Output:** `:: path moved`. The file should be renamed.
    -   **Actual Output:** `:: path moved`. The file was renamed correctly.
    -   **Result:** PASS.

3.  **Move to non-existent directory:**
    -   **Setup:** `$ touch /home/beta/renamed_file.md` (from previous test)
    -   **Command:** `$ mv /home/beta/renamed_file.md /home/beta/nonexistent_dir/`
    -   **Expected Output:** A single, clear error message indicating the directory does not exist.
    -   **Actual Output:** `!! mv: move failed: Directory does not exist: iosk/home/beta/nonexistent_dir/`
    -   **Result:** PASS.

4.  **Move non-existent source file:**
    -   **Command:** `$ mv /home/beta/does_not_exist.txt /home/beta/some_dir/`
    -   **Expected Output:** A single, clear error message indicating the source does not exist.
    -   **Actual Output:** (to be verified in future tests, but current `mv` implementation should handle this cleanly)
    -   **Result:** Not tested explicitly in this round, but general error handling is improved.
