# IOSK Commands: To Be Tested & Known Issues

This document outlines commands that require further attention, either because they have known issues, were explicitly skipped during initial testing, or their functionality is unclear. Commands marked as "Working" in their respective QA documents are not included here.

---

## Known Issues

The following issues have been identified in the existing QA documentation:

*   **`/bin/touch.py`**:
    *   **Issue**: Differs from standard UNIX `touch` as it will not update the modification time of an existing file; instead, it errors if the file already exists.
    *   **Status**: Working as a file creation utility, but non-standard behavior for existing files.

---

## Commands to Be Tested

The following commands require further testing, investigation, or fixing:

1.  **`/bin/bank.py`**
    *   **Reason**: Explicitly skipped (due to lannocc's instructions). Requires enabling and testing once banking functionality is to be used.
2.  **`/bin/bankrupt.py`**
    *   **Reason**: Explicitly skipped (due to lannocc's instructions). Requires enabling and testing once banking functionality is to be used.
3.  **`/bin/banks.py`**
    *   **Reason**: No explicit "Working" status given, and is related to the skipped banking commands. Needs full testing.
4.  **`/bin/get.py`**
    *   **Reason**: "Functionality unclear without a valid filename" according to its QA doc. Needs testing to clarify intended behavior and confirm it handles valid inputs correctly.
5.  **`/bin/touch.py`**
    *   **Reason**: While it works for file creation, its behavior for existing files is non-standard (errors instead of updating timestamp). This should be reviewed to either align with standard UNIX `touch` or confirm the current behavior is intentional and document it clearly.

---
