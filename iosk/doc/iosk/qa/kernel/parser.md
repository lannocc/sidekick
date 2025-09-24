# IOSK Kernel Parser Functionality Verification

**Proposal:** `doc/iosk/proposal/parser.md`
**Tester:** beta
**Date of QA:** 2025-09-24

## LANNOCC NOTE

I found a regression. The user chat logs no longer show all the user's comment and command history while they were attached whereas now it is only showing what everybody else sees for that user (not their actual activity). It's important the logs track all the activity of the user. This regression needs to be noted more and incorporated into this document for further analysis. --LANNOCC 9/24

### Introduction
This document details the verification process for the new shell parser implemented in `src/iosk/kernel.py`. The parser aims to provide robust tokenization, variable expansion, and seamless alias integration, simplifying command implementations by standardizing argument passing as a list (`argv`) rather than a raw string (`args`).

### Core Goals and Verification Matrix

| Goal                         | Description                                            | Test Case ID | Status   | Notes                                                               |
| :--------------------------- | :----------------------------------------------------- | :----------- | :------- | :------------------------------------------------------------------ |
| Robust Tokenization          | Correctly splits command strings, respecting quotes for arguments with spaces. | P001, P002 | Passed   | Ensure files with spaces can be handled by commands like `cat`, `cp`. |
| Variable Expansion           | Automatically expands `$VAR` and `${VAR}` syntax.      | P003, P004 | Pending  | Test with `$USER` and custom variables.                             |
| Alias Integration            | Aliases containing complex arguments or variables are correctly expanded and parsed. | P005     | Pending  | Test an alias that includes spaces and/or variables.                |
| Command Simplification       | Commands receive arguments as a pre-parsed list (`argv`), removing internal parsing logic. | P006     | Pending  | Implied by `echo.py` and `cp.py` refactor; verify their new behavior. |

---

### Test Cases and Results

#### P001: Tokenization with spaces (cat command)
**Description:** Verify `cat` can process a filename containing spaces when enclosed in double quotes.
**Steps:**
1. Create a file named `my test file.txt` with some content.
2. Attempt to `cat "my test file.txt"`.
**Expected Result:** The content of `my test file.txt` is displayed correctly.
**Actual Result:**
```
This is the content of "my test file.txt".
It demonstrates robust tokenization.
```
The content was displayed correctly.
**Status:** Passed

#### P002: Tokenization with spaces (cp command)
**Description:** Verify `cp` can copy a file with spaces in its name to a destination with spaces, using double quotes.
**Steps:**
1. Create `source file.txt` with content.
2. Attempt to `cp "source file.txt" "destination file.txt"`.
**Expected Result:** A new file `destination file.txt` is created with the same content as `source file.txt`.
**Actual Result:**
The file "destination file.txt" was created and its content matches "source file.txt".
**Status:** Passed

#### P003: Variable Expansion ($VAR)
**Description:** Verify `echo` correctly expands `$USER` variable.
**Steps:**
1. Run `echo "Logged in as: $USER"`.
**Expected Result:** `Logged in as: beta` (or current user's name) is displayed.
**Actual Result:** (Pending execution)

#### P004: Variable Expansion (${VAR})
**Description:** Verify `echo` correctly expands `${USER}` variable.
**Steps:**
1. Run `echo "User is: ${USER}"`.
**Expected Result:** `User is: beta` (or current user's name) is displayed.
**Actual Result:** (Pending execution)

#### P005: Alias Integration with variables and spaces
**Description:** Verify an alias that uses variables and arguments with spaces works as expected.
**Steps:**
1. Create an alias: `alias greet='echo "Hello, $USER! Today is $(date) and you are testing."`
2. Run `greet`.
**Expected Result:** A message including "Hello, beta!", the current date, and the "testing" phrase is displayed.
**Actual Result:** (Pending execution)

#### P006: Command Simplification (echo and cp using argv)
**Description:** Verify that `echo` and `cp` commands work as expected, demonstrating their reliance on the new `argv` parsing.
**Steps:**
1. Run `echo "This is a test of echo using the new parser."`
2. Run `cp original.txt copy.txt` (assuming original.txt exists).
**Expected Result:** `echo` prints the entire string. `cp` successfully copies the file. These implicitly test the `argv` argument passing.
**Actual Result:** (Pending execution)

---

### Final Status
**Overall Status:** [Pending]

**Summary:**
(To be filled after all tests are executed)

**Recommendations:**
(To be filled after all tests are executed)
