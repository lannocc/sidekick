# Diametrix AI Developer Coding Standards

This document outlines the mandatory coding standards for all AI Developer Agents contributing to the Diametrix Financial Analysis System. Adherence to these standards ensures code quality, maintainability, readability, and consistency across the entire project.

## I. General Principles

*   **Readability:** Code must be easy to understand by other agents and human supervisors. Prioritize clarity over cleverness.
*   **Maintainability:** Code should be structured in a way that allows for easy updates, bug fixes, and feature additions without introducing new errors.
*   **Consistency:** Follow established patterns and styles throughout the codebase.
*   **Efficiency:** While readability is paramount, code should also be efficient in terms of resource utilization (CPU, memory) where performance is critical.
*   **Testability:** Code should be modular and easy to test with unit and integration tests.

## II. Naming Conventions

*   **Variables and Functions:** Use `snake_case` (e.g., `user_id`, `calculate_loan_interest`).
*   **Classes and Types:** Use `PascalCase` (e.g., `LoanApplication`, `UserProfileManager`).
*   **Constants:** Use `UPPER_SNAKE_CASE` (e.g., `MAX_LOAN_AMOUNT`, `DEFAULT_TIMEOUT_SECONDS`).
*   **Modules/Files:** Use `snake_case` (e.g., `user_api.py`, `data_processing.py`).

## III. Code Structure and Formatting

*   **Indentation:** Use 4 spaces for indentation. Tabs are forbidden.
*   **Line Length:** Limit all lines to a maximum of 120 characters. Break long lines logically.
*   **Blank Lines:**
    *   Separate top-level function and class definitions with two blank lines.
    *   Separate method definitions within a class with one blank line.
    *   Use blank lines judiciously to improve readability within functions.
*   **Imports:**
    *   Imports should generally be at the top of the file, immediately after any module comments and docstrings.
    *   Group imports into standard library, third-party, and local application imports, separated by blank lines.
    *   Sort imports alphabetically within each group.
*   **Docstrings and Comments:**
    *   All modules, classes, public functions, and public methods **MUST** have a docstring (using triple double-quotes `"""Docstring"""`).
    *   Docstrings should briefly explain the purpose, arguments, and return values.
    *   Inline comments should be used to explain complex logic or non-obvious code sections. `#` comments should be concise and relevant.

## IV. Error Handling

*   **Exceptions:** Use Python's built-in exception handling (`try-except`) for anticipated error conditions.
*   **Specific Exceptions:** Catch specific exceptions rather than broad `Exception` where possible.
*   **Logging:** Use the established logging framework for recording errors, warnings, and informational messages. Avoid printing directly to `stdout` in production code.

## V. Testing

*   **Unit Tests:** Every significant function or method should have corresponding unit tests.
*   **Test Naming:** Test files should be named `test_*.py` and test methods `test_*`.
*   **Test Coverage:** Strive for high test coverage, particularly for critical business logic.
*   **Fixture Usage:** Utilize testing fixtures to set up and tear down test environments efficiently.

## VI. Security Considerations

*   **Input Validation:** All external inputs (user input, API payloads, file contents) must be thoroughly validated to prevent injection attacks and other vulnerabilities.
*   **Sensitive Data:** Handle sensitive data (passwords, PII, financial information) with extreme care. Do not log sensitive data in plain text. Use secure storage and transmission mechanisms.
*   **Permissions:** Adhere to the principle of least privilege. Agents should only have access to resources necessary for their assigned tasks.

## VII. Version Control

*   **Branching Strategy:** Follow the established Git branching strategy (e.g., feature branches, `develop`, `main`).
*   **Commit Messages:** Write clear, concise, and descriptive commit messages. Each message should explain *what* was changed and *why*.
*   **Atomic Commits:** Make small, focused commits that represent a single logical change.

## VIII. Code Review

*   All code changes **MUST** undergo a formal code review process as defined in `/doc/dmx/workflow/code_review_workflow.md` before being merged into main development branches.

## IX. Enforcement

*   The AI Operations & Resource Manager (Cadence) will periodically audit codebases for adherence to these standards.
*   Violations may lead to code rejection during review or requiring rework.
*   Automated linting and static analysis tools will be integrated into the CI/CD pipeline to enforce many of these standards programmatically.
```
```
