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
- **Duplicate Output Bug:** On successful creation, the command prints its success message twice. This seems related to a system-wide argument parsing issue.
- **Inconsistent Error Messages:** When attempting to create a directory that already exists, the command returns multiple, different error messages, suggesting redundant or conflicting error-checking routines.
- **Standard Error Handling:** Correctly fails when a component of the path is a file, not a directory.

## Test Cases
1.  **Standard execution:**
    -   **Command:** `$ mkdir /home/beta/workspace/test_dir`
    -   **Expected Output:** A single success message.
    -   **Actual Output:** `:: directory created` printed twice.
    -   **Result:** FAIL (due to duplicate output)

2.  **Creating an existing directory:**
    -   **Command:** `$ mkdir /home/beta/workspace/test_dir`
    -   **Expected Output:** A single, clear error message.
    -   **Actual Output:** Multiple, different error messages.
    -   **Result:** FAIL (due to inconsistent and multiple errors)

3.  **Invalid path (component is a file):**
    -   **Command:** `$ mkdir /home/beta/workspace/test_file.md/another_dir`
    -   **Expected Output:** An error message indicating the path is invalid.
    -   **Actual Output:** `!! mkdir: cannot create directory: /home/beta/workspace/test_file.md/another_dir`
    -   **Result:** PASS
