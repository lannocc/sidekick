# IOSK Kernel: I/O Redirection and Pipes Test Plan

**Feature:** I/O Redirection (`>`, `>>`) and Pipes (`|`)
**Proposal:** `doc/iosk/proposal/redirection.md`
**Target Components:** `src/iosk/kernel.py` (`IOSK.call`, `_execute_single_command`), `src/iosk/parser.py`, `src/iosk/io.py` (`Context` class, especially `io.stdin`, `io.stdout`, `io.output`), and relevant `/bin` commands (`echo.py`, `wc.py`, `search.py`, `head.py`, `tail.py`).

---

## 1. Feature Description

This feature enhances the IOSK command-line interface to support standard UNIX-style pipes (`|`) and I/O redirection (`>`, `>>`).
*   **Output Redirection**: Allows directing the standard output of a command to a file, either overwriting (`>`) or appending (`>>`) to its content.
*   **Pipes**: Connects the standard output of one command to the standard input of another, enabling multi-step data processing workflows.
This functionality aims to increase the composability and power of the command-line environment for both human and AI users.

## 2. Scope

This test plan covers the core functionality of pipes and output redirection, including basic usage, combinations, and error handling. It assumes that the "Advanced Shell Parser" (documented in `doc/iosk/proposal/parser.md`) is fully implemented and functioning correctly for tokenization and variable expansion.

## 3. Prerequisites

*   An IOSK system instance must be running, accessible via a shell (e.g., `sk iosk shell <root_path>`). The current user should have write access to `/home/<user>/` (e.g., `beta`).
*   The `bin/echo.py`, `bin/wc.py`, `bin/search.py`, `bin/head.py`, and `bin/tail.py` commands must be present and correctly updated to read from `io.stdin` when no file argument is provided, as per the `redirection.md` proposal. The provided file content indicates `wc.py`, `head.py`, and `tail.py` are already updated.
*   Necessary test files exist in the `/home/beta/` directory.

## 4. Test Environment Setup

Before executing test cases, ensure the following files exist in `/home/beta/`:

1.  **`/home/beta/simple.txt`**:
    ```
    line 1
    line 2
    line 3
    ```

2.  **`/home/beta/test_tail_file.txt`**: (already exists from hierarchy)
    ```
    This is line 1.
    This is line 2.
    This is line 3.
    This is line 4.
    This is line 5.
    This is line 6.
    This is line 7.
    This is line 8.
    This is line 9.
    This is line 10.
    This is line 11.
    This is line 12.
    This is line 13.
    This is line 14.
    This is line 15.
    ```

3.  **Clean up any previous test artifacts:**
    ```bash
    $ rm /home/beta/output_file.txt
    $ rm /home/beta/append_file.txt
    $ rm /home/beta/piped_output.txt
    $ rm /home/beta/temp_dir/redirect_file.txt
    $ rmdir /home/beta/temp_dir
    ```
    *(Note: `rm` and `rmdir` will print errors if files/dirs don't exist, which is expected for cleanup.)*

## 5. Test Cases

---

### Category A: Output Redirection (`>` and `>>`)

| ID    | Description                                       | Command(s)                                                                 | Expected Output/Behavior                                                                                                                                                                             | Verification Step                                                                  | Status |
| :---- | :------------------------------------------------ | :------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- | :----- |
| A.1   | Basic overwrite to a new file                     | `$ echo "Hello World" > /home/beta/output_file.txt`                        | Command should not print to console. File `/home/beta/output_file.txt` should be created and contain `Hello World\n`.                                                                                | `$ cat /home/beta/output_file.txt`                                                 |        |
| A.2   | Overwrite to an existing file                     | `$ echo "New content" > /home/beta/output_file.txt`                        | Command should not print to console. File `/home/beta/output_file.txt` should now contain only `New content\n`. Previous content should be gone.                                                     | `$ cat /home/beta/output_file.txt`                                                 |        |
| A.3   | Append to a new file                              | `$ echo "First line" >> /home/beta/append_file.txt`                        | Command should not print to console. File `/home/beta/append_file.txt` should be created and contain `First line\n`.                                                                                 | `$ cat /home/beta/append_file.txt`                                                 |        |
| A.4   | Append to an existing file                        | `$ echo "Second line" >> /home/beta/append_file.txt`                       | Command should not print to console. File `/home/beta/append_file.txt` should now contain `First line\nSecond line\n`.                                                                             | `$ cat /home/beta/append_file.txt`                                                 |        |
| A.5   | Command producing multiple lines of output        | `$ cat /home/beta/simple.txt > /home/beta/output_file.txt`                 | Command should not print to console. File `/home/beta/output_file.txt` should contain the exact content of `simple.txt`.                                                                           | `$ cat /home/beta/output_file.txt`                                                 |        |
| A.6   | Command producing no output (return code only)    | `$ rm /home/beta/non_existent_file.txt > /home/beta/output_file.txt`       | Command should attempt `rm`, which should fail (file not found), but `rm`'s error message should *not* be redirected. Console should show the error. `output_file.txt` should remain unchanged (or empty if it was created empty by the redirect itself). | `$ cat /home/beta/output_file.txt` (should be unchanged from A.5 if already existed, or empty) |        |
| A.7   | Redirection to a non-existent directory (failure) | `$ echo "Fail" > /home/beta/non_existent_dir/redirect_file.txt`            | Command should print an error to console, indicating that the target directory does not exist. The redirect operation should fail.                                                                      | Console output, then `$ ls /home/beta/` (verify `non_existent_dir` not created) |        |
| A.8   | Redirection with path containing spaces (quoted)  | `$ echo "Content with spaces" > "/home/beta/output file with spaces.txt"` | Command should not print to console. File `output file with spaces.txt` should be created in `/home/beta/` and contain `Content with spaces\n`.                                                     | `$ cat "/home/beta/output file with spaces.txt"`                                   |        |
| A.9   | Redirection to a newly created directory          | `$ mkdir /home/beta/temp_dir` <br> `$ echo "In temp" > /home/beta/temp_dir/redirect_file.txt` | `mkdir` should succeed. The `echo` command should not print to console. File `/home/beta/temp_dir/redirect_file.txt` should be created and contain `In temp\n`.                                   | `$ cat /home/beta/temp_dir/redirect_file.txt`                                      |        |

---

### Category B: Pipes (`|`)

| ID    | Description                                           | Command(s)                                                                 | Expected Output/Behavior                                                                                                                                                                                                                                    | Verification Step                                                                                                                                                                                                                                                                                                                                           | Status |
| :---- | :---------------------------------------------------- | :------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----- |
| B.1   | Basic two-command pipe (`ls | wc`)                  | `$ ls /home/beta | wc`                                                       | The `ls` command's output for `/home/beta` should be piped to `wc`. `wc` should then count lines, words, and characters of that output and print its result to the console. Expected output will vary based on `/home/beta` contents (e.g., `12  12      153     `). | Observe console output. Compare with manual execution of `ls /home/beta` then manually copy-pasting to `wc`. (e.g., `ls /home/beta | sed '$d' | sed '$d' | wc` if ls adds lines for count) <br> **Note:** `wc`'s output includes `filename` field which should be empty. |        |
| B.2   | Chained pipes (`cat | head | tail`)                 | `$ cat /home/beta/test_tail_file.txt | head -n 10 | tail -n 3`                | The `cat` command's output (15 lines) should be piped to `head` (outputs first 10 lines). `head`'s output should then be piped to `tail` (outputs last 3 of those 10 lines). Expected: `This is line 8.\nThis is line 9.\nThis is line 10.\n`                       | Observe console output.                                                                                                                                                                                                                                                                                                                             |        |
| B.3   | Pipe with `search`                                    | `$ cat /home/beta/test_tail_file.txt | search "line 5"`                   | `search` should receive the content of `test_tail_file.txt` via stdin and find "line 5". Expected: `line 5` (or similar, depending on search output format).                                                                                             | Observe console output.                                                                                                                                                                                                                                                                                                                             |        |
| B.4   | Pipe with `search -n` (line numbers)                  | `$ cat /home/beta/test_tail_file.txt | search -n "line 10"`                 | `search` should receive the content and output `10: This is line 10.`                                                                                                                                                                                       | Observe console output.                                                                                                                                                                                                                                                                                                                             |        |
| B.5   | Pipe with `search -c` (count)                         | `$ cat /home/beta/test_tail_file.txt | search -c "line"`                    | `search` should receive the content and output the count of lines containing "line". Expected: `15` (or similar).                                                                                                                                             | Observe console output.                                                                                                                                                                                                                                                                                                                             |        |
| B.6   | Pipe with `head` and `tail` on content from stdin | `$ echo -e "a\nb\nc\nd\ne" | head -n 3 | tail -n 2`                      | `echo` outputs 5 lines. `head -n 3` gets `a\nb\nc\n`. `tail -n 2` gets `b\nc\n`.                                                                                                                                                                            | Observe console output.                                                                                                                                                                                                                                                                                                                             |        |

---

### Category C: Combined Pipes and Redirection

| ID    | Description                                     | Command(s)                                                                     | Expected Output/Behavior                                                                                                                                              | Verification Step                                                                  | Status |
| :---- | :---------------------------------------------- | :----------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- | :----- |
| C.1   | Pipe leading to overwrite redirection           | `$ ls /home/beta | wc > /home/beta/piped_output.txt`                             | `ls` output is piped to `wc`. `wc`'s output is redirected to `/home/beta/piped_output.txt`. Nothing should be printed to console. File should contain `wc`'s result. | `$ cat /home/beta/piped_output.txt`                                                |        |
| C.2   | Pipe leading to append redirection              | `$ ls /home/beta | wc >> /home/beta/piped_output.txt`                            | `ls` output is piped to `wc`. `wc`'s output is appended to `/home/beta/piped_output.txt`. Nothing should be printed to console. File should now contain previous content + `wc`'s result. | `$ cat /home/beta/piped_output.txt`                                                |        |
| C.3   | Complex pipeline with `search` and redirection  | `$ cat /home/beta/test_tail_file.txt | search "line 1" > /home/beta/line1.txt` | `cat` output is piped to `search`. `search` finds "line 1" and its output is redirected. File `/home/beta/line1.txt` should contain `This is line 1.\n`.           | `$ cat /home/beta/line1.txt`                                                       |        |

---

### Category D: Error Handling

| ID    | Description                                           | Command(s)                                                                 | Expected Output/Behavior                                                                                                                                                                                                                                                                  | Verification Step                                                                  | Status |
| :---- | :---------------------------------------------------- | :------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- | :----- |
| D.1   | Missing filename for `>` redirection                | `$ echo "Oops" >`                                                          | Command should print an error to console, e.g., `!! parse error: missing filename for redirection '>'`.                                                                                                                                                                         | Console output.                                                                    |        |
| D.2   | Missing filename for `>>` redirection               | `$ echo "Oops" >>`                                                         | Command should print an error to console, e.g., `!! parse error: missing filename for redirection '>>'`.                                                                                                                                                                        | Console output.                                                                    |        |
| D.3   | Invalid command in pipeline (first command)           | `$ invalid_cmd | wc`                                                       | The first command `invalid_cmd` should fail. The pipe should not proceed. Console should show `!! command not found: invalid_cmd`.                                                                                                                                           | Console output.                                                                    |        |
| D.4   | Invalid command in pipeline (second command)          | `$ echo "test" | invalid_cmd`                                              | The first command `echo "test"` should succeed and its output piped. The second command `invalid_cmd` should fail. Console should show `!! command not found: invalid_cmd`.                                                                                                 | Console output.                                                                    |        |
| D.5   | Empty command before pipe                             | `$ | wc`                                                                     | Command should print an error to console, e.g., `!! parse error: empty command before pipe`.                                                                                                                                                                            | Console output.                                                                    |        |
| D.6   | Empty command after pipe                              | `$ ls |`                                                                     | Command should print an error to console, e.g., `!! parse error: empty command after pipe`.                                                                                                                                                                             | Console output.                                                                    |        |
| D.7   | Multiple output redirections (not supported by spec)  | `$ echo "test" > /home/beta/file1.txt > /home/beta/file2.txt`              | Command should print an error to console, e.g., `!! parse error: multiple redirections are not supported`.                                                                                                                                                                | Console output.                                                                    |        |
| D.8   | Redirection to an existing directory (failure)        | `$ echo "to dir" > /home/beta/temp_dir`                                    | Command should print an error to console indicating it cannot redirect output to a directory (e.g., `!! error during pipeline execution: [Errno 21] Is a directory: '.../iosk/home/beta/temp_dir'`).                                                                    | Console output. `$ cat /home/beta/temp_dir` (should fail or show directory contents, not "to dir") |        |
| D.9   | Pipeline with non-text file as input (should implicitly fail for commands reading stdin) | `$ cp /bin/welcome /home/beta/copy_welcome | wc` | The `cp` command will copy a file. Then `wc` will attempt to read from standard input, but `cp` does not write to standard output. `wc` should output `0 0 0` or similar for empty input. This tests `wc`'s robust handling of empty stdin. | Observe console output. (`cp` might print success message to console, or stderr might be piped through if `cp` has internal print statements). Check `wc`'s output. |        |

---
**Status Key:**
*   **Passed:** The test case executed as expected.
*   **Failed:** The test case did not execute as expected (e.g., error, incorrect output, hang).
*   **Blocked:** The test case could not be executed due to a dependency or prerequisite issue.
*   **Skipped:** The test case was intentionally not executed (e.g., out of scope, known bug not being addressed in this iteration).

