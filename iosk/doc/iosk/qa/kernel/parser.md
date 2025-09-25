# IOSK Kernel Parser Functionality Verification

**Overall STATUS: Passing with Caveats - Alias Definition and Expansion Issues**

**Proposal:** `doc/iosk/proposal/parser.md`
**Tester:** beta
**Date of QA:** 2025-09-24 (Updated)

### Introduction
This document details the verification process for the new shell parser implemented in `src/iosk/kernel.py`. The parser aims to provide robust tokenization, variable expansion, and seamless alias integration, simplifying command implementations by standardizing argument passing as a list (`argv`) rather than a raw string (`args`).

### Core Goals and Verification Matrix

| Goal                         | Description                                            | Test Case ID | Status   | Notes                                                               |
| :--------------------------- | :----------------------------------------------------- | :----------- | :------- | :------------------------------------------------------------------ |
| Robust Tokenization          | Correctly splits command strings, respecting quotes for arguments with spaces. | P001, P002 | Passed   | Ensure files with spaces can be handled by commands like `cat`, `cp`. |
| Variable Expansion           | Automatically expands `$VAR` and `${VAR}` syntax.      | P003, P004 | Passed   | Tested with `$PATH` and `${PATH}`.                                  |
| Alias Integration            | Aliases containing complex arguments or variables are correctly expanded and parsed. | P005     | Failed   | Variables expand at alias definition, not execution. Nested quotes in alias definitions lead to parsing errors. |
| Command Simplification       | Commands receive arguments as a pre-parsed list (`argv`), removing internal parsing logic. | P006     | Passed   | Verified `echo` and `cp` functionality.                             |

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
**Description:** Verify `echo` correctly expands `$PATH` variable.
**Steps:**
1. Run `export PATH=/bin` (if not already set).
2. Run `echo "Current PATH is: $PATH"`.
**Expected Result:** `Current PATH is: /bin` (or current PATH value) is displayed.
**Actual Result:** `Current PATH is: /bin`
**Status:** Passed

#### P004: Variable Expansion (${VAR})
**Description:** Verify `echo` correctly expands `${PATH}` variable.
**Steps:**
1. Run `export PATH=/bin` (if not already set).
2. Run `echo "Path using curly braces: ${PATH}"`.
**Expected Result:** `Path using curly braces: /bin` (or current PATH value) is displayed.
**Actual Result:** `Path using curly braces: /bin`
**Status:** Passed

#### P005: Alias Integration with variables and spaces (Re-tested)
**Description:** Verify an alias that uses variables and arguments with spaces works as expected, and test alias definitions with nested quotes.
**Steps:**
1. Define an alias with a variable: `alias showpath="echo The current PATH is: $PATH"`
2. Run `showpath`.
3. Define an alias with nested quotes: `alias test_nested_quotes='echo "This has inner quotes!"'`
4. Run `test_nested_quotes`.
**Expected Result:**
- `showpath` should display the current PATH at *execution time*.
- `test_nested_quotes` should display `This has inner quotes!`.
**Actual Result:**
- `alias showpath="echo The current PATH is: $PATH"` resulted in `Alias 'showpath' defined as 'echo The current PATH is: /bin'`. Executing `showpath` printed `The current PATH is: /bin`. This shows variable expansion occurs *during alias definition*, not execution.
- `alias test_nested_quotes='echo "This has inner quotes!"'` resulted in `Alias 'test_nested_quotes' defined as 'echo "This has inner quotes!'`. Executing `test_nested_quotes` resulted in `!! parse error: No closing quotation`. This confirms a problem with parsing nested quotes in alias definitions.
**Status:** Failed
**Notes:** Re-testing revealed two critical issues. First, variables within an alias definition (e.g., `$PATH`) are expanded *during the alias definition itself*, not during alias execution. This prevents dynamic variable usage within aliases. Second, the parser still struggles with nested quotes in alias definitions; the outer single quotes are not correctly interpreted, leaving inner quotes unmatched and leading to parse errors upon alias execution. The previous "Passed" status for P005 was based on a misunderstanding of the desired dynamic variable expansion and an avoidance of the nested quote issue.

#### P006: Command Simplification (echo and cp using argv)
**Description:** Verify that `echo` and `cp` commands work as expected, demonstrating their reliance on the new `argv` parsing.
**Steps:**
1. Run `echo "This is a test of echo using the new parser."`
2. Run `cp original.txt copy.txt` (assuming original.txt exists and has content).
**Expected Result:** `echo` prints the entire string. `cp` successfully copies the file. These implicitly test the `argv` argument passing.
**Actual Result:**
- `echo "This is a test of echo using the new parser."` correctly displayed `This is a test of echo using the new parser.`.
- `cp original.txt copy.txt` successfully copied `original.txt` to `copy.txt`, and `cat copy.txt` showed the correct content.
**Status:** Passed

---

### Final Status
**Overall Status:** Passing with Caveats - Alias Definition and Expansion Issues

**Summary:**
The IOSK kernel parser's core functionalities, including robust tokenization (P001, P002), basic variable expansion (P003, P004), and command simplification (P006), are still functioning as expected. However, the alias integration (P005) has significant issues. Variable expansion within aliases now occurs at *definition time* instead of execution time, limiting their utility for dynamic values. More critically, the parser fails to correctly handle nested quotes within alias definitions, consistently leading to `parse error: No closing quotation` upon alias execution.

**Recommendations:**
Attention is required to fix the alias parsing logic.
1. Alias definitions should preserve variable names (e.g., `$PATH`) for expansion at *execution time*, similar to how shell scripts typically handle them.
2. The parser needs to correctly handle nested quotes (e.g., `alias name='echo "quoted string"'`) so that the alias command itself can be defined with complex arguments. This might involve re-evaluating the quoting mechanism during alias definition and expansion.
