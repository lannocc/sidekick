# Command: mkdir

## Description
The `mkdir` command creates new directories.

## Usage
`$ mkdir [PATH]...`

## Arguments
- `[PATH]...`: One or more paths to the directories to be created.

## Behavior
- Creates a new directory at the specified path.
- Reports an error if the directory already exists.
- Reports an error if a component of the path is not a directory.

## Edge Cases and Bugs
- **Inconsistent Error Messages:** When attempting to create a directory that already exists, the command returns multiple, different error messages, suggesting redundant or conflicting error-checking routines. (e.g., `!! path already exists: ...` and `!! mkdir: cannot create directory: ...`). The expected behavior is a single, clear error message.

## Test Cases
1.  **Standard execution (creating a new directory):**
    -   **Command:** `$ mkdir /home/beta/test_mkdir_new_dir`
    -   **Expected Output:** A single success message.
    -   **Actual Output:** `:: directory created`
    -   **Result:** PASS. The "Duplicate Output Bug" has been resolved.

2.  **Creating an existing directory:**
    -   **Command:** `$ mkdir /home/beta/test_mkdir_new_dir`
    -   **Expected Output:** A single, clear error message.
    -   **Actual Output:**
        ```
        !! path already exists: /home/beta/test_mkdir_new_dir
        !! mkdir: cannot create directory: /home/beta/test_mkdir_new_dir
        ```
    -   **Result:** FAIL (due to inconsistent and multiple errors).

3.  **Invalid path (component is a file):**
    -   **Setup:** `$ touch /home/beta/test_mkdir_file_component.txt`
    -   **Command:** `$ mkdir /home/beta/test_mkdir_file_component.txt/another_dir`
    -   **Expected Output:** An error message indicating the path is invalid.
    -   **Actual Output:** `!! mkdir: cannot create directory: /home/beta/test_mkdir_file_component.txt/another_dir`
    -   **Result:** PASS.
