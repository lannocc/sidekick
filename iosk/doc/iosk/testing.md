# IOSK Commands: To Be Tested & Known Issues

This document outlines commands that require further attention, either because they have known issues, were explicitly skipped during initial testing, or their functionality is unclear. Commands marked as "Working" in their respective QA documents are not included here.

---

## Known Issues

The following issues have been identified in the existing QA documentation:

*   **`/bin/ask.py`**:
    *   **Issue**: Causes the system to hang. Explicitly skipped for testing.
    *   **Status**: Broken.
*   **`/bin/attach.py`**:
    *   **Issue**: Restriction against attaching the console device has been noted for future reference. Explicitly skipped for testing.
    *   **Status**: Skipped.
*   **`/bin/help` (skrip)**:
    *   **Issue**: The skrip does not handle any arguments (e.g., `$ help --help`, `$ help ls`) and throws an unhandled exception instead of ignoring them or printing an error message.
    *   **Status**: Broken.
*   **`/bin/ll.py`**:
    *   **Issue 1: Multiple Output Bug**: When flags such as `-a`, `-l`, or combined flags like `-la` are used, the command produces multiple sets of output (e.g., `ll -a /` prints output twice, `ll -la /` prints it thrice). The command seems to be incorrectly iterating over its arguments and running the underlying `ls` command multiple times.
    *   **Issue 2: Help Text Discrepancy**: The help output is a mix of a standard GNU `ls` help page and a smaller, IOSK-specific summary. It is unclear how many of the numerous flags from the GNU section are actually implemented or supported within the IOSK environment.
    *   **Status**: Broken.
*   **`/bin/mkdir.py`**:
    *   **Issue 1: Duplicate Output Bug**: On successful creation, the command prints its success message twice.
    *   **Issue 2: Inconsistent Error Messages**: When attempting to create a directory that already exists, the command returns multiple, different error messages.
    *   **Status**: Broken.
*   **`/bin/mv.py`**:
    *   **Issue 1: CRITICAL: Output Duplication/Escalation**: Output is repeated multiple times, and the number of repetitions appears to increase with each subsequent command executed in the session.
    *   **Issue 2: Inconsistent Error Messages**: When attempting to move a file to a non-existent directory, the command outputs multiple, different error messages before finally throwing a generic exception.
    *   **Status**: Broken (Critical).
*   **`/bin/touch.py`**:
    *   **Issue**: Differs from standard UNIX `touch` as it will not update the modification time of an existing file; instead, it errors if the file already exists.
    *   **Status**: Working as a file creation utility, but non-standard behavior for existing files.

---

## Commands to Be Tested

The following commands require further testing, investigation, or fixing:

1.  **`/bin/ask.py`**
    *   **Reason**: Known broken (causes system hang) and skipped. Requires fixing before use.
2.  **`/bin/attach.py`**
    *   **Reason**: Explicitly skipped. Needs to be enabled and thoroughly tested, especially regarding the console device restriction.
3.  **`/bin/bank.py`**
    *   **Reason**: Explicitly skipped (due to lannocc's instructions). Requires enabling and testing once banking functionality is to be used.
4.  **`/bin/bankrupt.py`**
    *   **Reason**: Explicitly skipped (due to lannocc's instructions). Requires enabling and testing once banking functionality is to be used.
5.  **`/bin/banks.py`**
    *   **Reason**: No explicit "Working" status given, and is related to the skipped banking commands. Needs full testing.
6.  **`/bin/detach.py`**
    *   **Reason**: Explicitly skipped. Needs to be enabled and thoroughly tested.
7.  **`/bin/get.py`**
    *   **Reason**: "Functionality unclear without a valid filename" according to its QA doc. Needs testing to clarify intended behavior and confirm it handles valid inputs correctly.
8.  **`/bin/help` (skrip)**
    *   **Reason**: Known broken; throws exceptions when arguments are provided. Requires fixing to handle arguments gracefully (either by ignoring them or providing context-sensitive help).
9.  **`/bin/ll.py`**
    *   **Reason**: Known broken; suffers from output duplication bugs with flags and help text discrepancies. Requires fixing.
10. **`/bin/mkdir.py`**
    *   **Reason**: Known broken; has duplicate output and inconsistent error messages. Requires fixing.
11. **`/bin/mv.py`**
    *   **Reason**: Known critical bug with output duplication/escalation and inconsistent error messages. High priority for fixing.
12. **`/bin/touch.py`**
    *   **Reason**: While it works for file creation, its behavior for existing files is non-standard (errors instead of updating timestamp). This should be reviewed to either align with standard UNIX `touch` or confirm the current behavior is intentional and document it clearly.

---
