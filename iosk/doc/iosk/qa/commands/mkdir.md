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
- No known bugs at this time. (Removed the "Inconsistent Error Messages" bug as it's resolved).

## Test Cases
1.  **Standard execution (creating a new directory):**
    -   **Command:** `$ mkdir /home/beta/test_mkdir_new_dir`
    -   **Expected Output:** A single success message.
    -   **Actual Output:** `:: directory created`
    -   **Result:** PASS.

2.  **Creating an existing directory:**
    -   **Command:** `$ mkdir /home/beta/test_mkdir_new_dir`
    -   **Expected Output:** A single, clear error message indicating the directory already exists.
    -   **Actual Output:** `!! mkdir: path already exists: /home/beta/test_mkdir_new_dir` (Updated output)
    -   **Result:** PASS. The previous "Inconsistent Error Messages" bug has been resolved, and a single, clear error message is now returned.

3.  **Invalid path (component is a file):**
    -   **Setup:** `$ touch /home/beta/test_mkdir_file_component.txt`
    -   **Command:** `$ mkdir /home/beta/test_mkdir_file_component.txt/another_dir`
    -   **Expected Output:** An error message indicating the path is invalid because a component is not a directory.
    -   **Actual Output:** `!! mkdir: failed to create directory /home/beta/test_mkdir_file_component.txt/another_dir: [Errno 20] Not a directory: 'iosk/home/beta/test_mkdir_file_component.txt/another_dir'` (Updated output)
    -   **Result:** PASS.
