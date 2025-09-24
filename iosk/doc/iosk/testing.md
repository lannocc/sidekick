# IOSK Commands: To Be Tested & Known Issues

This document outlines commands that require further attention, either because they have known issues, were explicitly skipped during initial testing, or their functionality is unclear. Commands marked as "Working" in their respective QA documents are not included here.

---

## Known Issues

The following issues have been identified in the existing QA documentation:

*   **`/bin/ask.py`**:
    *   **Issue**: Causes the system to hang. Explicitly skipped for testing.
    *   **Status**: Broken.
*   **`/bin/help` (skrip)**:
    *   **Issue**: The skrip does not handle any arguments (e.g., `$ help --help`, `$ help ls`) and throws an unhandled exception instead of ignoring them or printing an error message.
    *   **Status**: Broken.
*   **`/bin/mkdir.py`**:
    *   **Issue**: When attempting to create a directory that already exists, the command returns multiple, different error messages. The "Duplicate Output Bug" on successful creation has been resolved.
    *   **Status**: Broken (due to inconsistent error messages).
*   **`/bin/mv.py`**:
    *   **Issue 1: CRITICAL: Output Duplication/Escalation**: Output is repeated multiple times, and the number of repetitions appears to increase with each subsequent command executed in the session.
    *   **Issue 2: Exception on Non-Existent Directory**: When attempting to move a file to a non-existent directory, the command throws a general exception (`!! exception calling mv`) instead of a single, clear error message.
    *   **Status**: Broken (Critical).
*   **`/bin/touch.py`**:
    *   **Issue**: Differs from standard UNIX `touch` as it will not update the modification time of an existing file; instead, it errors if the file already exists.
    *   **Status**: Working as a file creation utility, but non-standard behavior for existing files.

---

## Commands to Be Tested

The following commands require further testing, investigation, or fixing:

1.  **`/bin/ask.py`**
    *   **Reason**: Known broken (causes system hang) and skipped. Requires fixing before use.
2.  **`/bin/bank.py`**
    *   **Reason**: Explicitly skipped (due to lannocc's instructions). Requires enabling and testing once banking functionality is to be used.
3.  **`/bin/bankrupt.py`**
    *   **Reason**: Explicitly skipped (due to lannocc's instructions). Requires enabling and testing once banking functionality is to be used.
4.  **`/bin/banks.py`**
    *   **Reason**: No explicit "Working" status given, and is related to the skipped banking commands. Needs full testing.
5.  **`/bin/get.py`**
    *   **Reason**: "Functionality unclear without a valid filename" according to its QA doc. Needs testing to clarify intended behavior and confirm it handles valid inputs correctly.
6.  **`/bin/help` (skrip)**
    *   **Reason**: Known broken; throws exceptions when arguments are provided. Requires fixing to handle arguments gracefully (either by ignoring them or providing context-sensitive help).
7.  **`/bin/ll.py`**
    *   **Reason**: While core listing functionality is working, its `--help` output is generic, and the "long format" (`-l`) does not display additional file metadata (permissions, owner, size, etc.) as a traditional UNIX `ls -l` would.
8.  **`/bin/mkdir.py`**
    *   **Reason**: Known broken due to inconsistent error messages when creating an existing directory. Requires fixing.
9.  **`/bin/mv.py`**
    *   **Reason**: Known critical bugs with output duplication/escalation and throwing a generic exception when moving to a non-existent directory. High priority for fixing.
10. **`/bin/touch.py`**
    *   **Reason**: While it works for file creation, its behavior for existing files is non-standard (errors instead of updating timestamp). This should be reviewed to either align with standard UNIX `touch` or confirm the current behavior is intentional and document it clearly.

---
