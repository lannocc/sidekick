# Command: ls

## Description
The `ls` command lists the contents of a directory. It is analogous to the `ls` command in standard UNIX environments.

## Usage
`$ ls [options] [path ...]`

## Arguments
-   `[path ...]`: Optional. The path(s) to list. Defaults to the current directory if not provided.
-   `-l`: Use a long listing format.
-   `-a`: List all entries, including those starting with `.`.
-   `--help`: Display the help message.

## Behavior
-   When run without arguments, it lists the contents of the root directory in a tab-separated format.
-   When given a valid path, it lists the contents of that path.
-   When given an invalid path, it prints a clear error message: `!! ls: path does not exist: <path>`.
-   The `--help` option displays a detailed help message, but the help message itself is often duplicated, indicating the argument parsing bug affects it as well.

## Edge Cases and Bugs
-   **CRITICAL - Output Duplication Bug:** The command suffers from a severe bug where it often produces duplicate or even triplicate output when used with paths or certain flags (e.g., `$ ls /bin`, `$ ls -a /`). The formatting between the duplicated outputs can be inconsistent. This seems to be a fundamental issue in the shell's argument parser, which is exacerbated when `ls` is called by a wrapper like `ll`.
-   **CRITICAL - Private Output Leaks to Public Chat:** Under certain conditions, the output of the `ls` command is not kept private to the user but is instead sent as a public chat message. This is a major information leak and system bug.
-   **Inconsistent Bug Behavior:** The duplication bug does not trigger consistently. For example, `$ ls -l /` produced a single, correct output, while `$ ls -a /` produced a malformed, duplicated output. This suggests a complex interaction between the arguments being parsed.

## Test Cases
1.  **Standard execution (no args):**
    -   **Command:** `$ ls`
    -   **Expected Output:** A single, tab-separated listing of the root directory.
    -   **Actual Output:** Matches expected output.
    -   **Result:** PASS

2.  **Execution with path:**
    -   **Command:** `$ ls /bin`
    -   **Expected Output:** A single listing of the contents of `/bin`.
    -   **Actual Output:** A triplicate listing of the contents.
    -   **Result:** FAIL (Bug)

3.  **Execution with `-l` flag:**
    -   **Command:** `$ ls -l /`
    -   **Expected Output:** A single, long-format listing of the root directory.
    -   **Actual Output:** Matches expected output.
    -   **Result:** PASS

4.  **Execution with `-a` flag:**
    -   **Command:** `$ ls -a /`
    -   **Expected Output:** A single listing of the root directory, including hidden files.
    -   **Actual Output:** A duplicated, malformed listing.
    -   **Result:** FAIL (Bug)

5.  **Execution with invalid path:**
    -   **Command:** `$ ls /nonexistent`
    -   **Expected Output:** An error message indicating the path does not exist.
    -   **Actual Output:** `!! ls: path does not exist: /nonexistent`
    -   **Result:** PASS
