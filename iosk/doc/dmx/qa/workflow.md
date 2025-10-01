### Diametrix QA Process Workflow

This document outlines the structured workflow for submitting, testing, and approving new features, bug fixes, and enhancements within the Diametrix Financial Analysis System. Our goal is to achieve predictive certainty in the quality and stability of our software, leveraging a clear, auditable, and collaborative process.

#### 1. Submission of Items for QA (`incoming/`)

*   **Purpose:** To provide a single, organized entry point for all items requiring QA.
*   **Procedure:**
    *   Developers or product managers will create a markdown file in the `/doc/dmx/qa/incoming/` directory.
    *   The filename should follow the format: `T[TicketID]-Description.md` (e.g., `T254-ClientInformationDisplayFix.md`).
    *   Each file **MUST** contain the following metadata at the top:
        ```
        ---
        Ticket ID: [e.g., T254]
        Feature/Bug: [e.g., Feature, Bug Fix, Enhancement]
        Priority: [e.g., Critical, High, Medium, Low]
        Submitted By: [Your Username]
        Submission Date: [YYYY-MM-DD HH:MM:SS]
        Target Release: [e.g., 1.0.1, Next Sprint]
        ---
        ```
    *   Below the metadata, provide a clear and concise description of the item to be tested, including:
        *   **Problem/Goal:** What issue is being resolved or what new functionality is being introduced?
        *   **Steps to Reproduce/Test:** Detailed, step-by-step instructions on how to test the functionality. Include specific data, user roles, and expected outcomes.
        *   **Dependencies:** Any external systems, configurations, or other features that must be in place or tested concurrently.
        *   **Relevant Files/Branches:** Pointers to the specific code changes (e.g., Git branch, pull request link if available) and any associated documentation.
    *   **Automated Scans/Checks:** Before submission, ensure that standard linting, static analysis, and unit tests have passed.

#### 2. QA Review and Testing (`testing/`)

*   **Purpose:** To systematically execute test plans and identify any deviations from expected behavior.
*   **Procedure:**
    *   The QA team (The Conclave) will periodically review the `incoming/` directory.
    *   An item, once picked up for testing, will be moved from `incoming/` to `/doc/dmx/qa/testing/`.
    *   The assigned QA engineer will:
        *   Thoroughly review the submission file for clarity and completeness.
        *   Design and document additional test cases as needed.
        *   Execute manual and automated tests according to the provided steps and newly designed test cases.
        *   Record all findings, including screenshots or logs where necessary, directly within the `T[TicketID]-Description.md` file, appending a "QA Notes" section.
        *   Update the metadata with a "QA Status" field (e.g., `QA Status: In Progress, Failed, Passed`).
    *   If a bug is found during testing that is not part of the current ticket, a new bug report should be created in `bugs/`.

#### 3. Bug Reporting and Management (`bugs/`)

*   **Purpose:** To track and manage all identified defects.
*   **Procedure:**
    *   When a defect is identified, a new markdown file should be created in `/doc/dmx/qa/bugs/`.
    *   The filename format: `BUG-[YYYYMMDD]-[ShortDescription].md` (e.g., `BUG-20250930-LoginPageCrash.md`).
    *   Each bug file **MUST** contain the following metadata at the top:
        ```
        ---
        Bug ID: [Internal tracking ID or filename]
        Severity: [e.g., Blocker, Critical, Major, Minor, Cosmetic]
        Reported By: [Your Username]
        Report Date: [YYYY-MM-DD HH:MM:SS]
        Affected Component: [e.g., Frontend, Backend, Database, Integration]
        Status: [e.g., Open, Acknowledged, In Development, Ready for Retest, Closed]
        ---
        ```
    *   Below the metadata, provide:
        *   **Description:** Clear explanation of the bug.
        *   **Steps to Reproduce:** Precise, repeatable steps to trigger the bug.
        *   **Expected Result:** What should have happened.
        *   **Actual Result:** What actually happened, including error messages, logs, and screenshots.
        *   **Environment:** Details of the testing environment (e.g., OS, browser, server version, specific data used).

#### 4. Approval and Deployment Readiness (`approved/`)

*   **Purpose:** To signify that an item has met all quality criteria and is ready for release.
*   **Procedure:**
    *   Once an item passes all QA tests and any identified bugs are resolved and re-tested, the `T[TicketID]-Description.md` file will be moved from `testing/` to `/doc/dmx/qa/approved/`.
    *   The "QA Status" in the metadata should be updated to `QA Status: Approved`.
    *   The "Approval Date" and "Approved By" fields should be added to the metadata.

#### 5. Rejection and Rework (`rejected/`)

*   **Purpose:** To clearly mark items that failed QA and require further development.
*   **Procedure:**
    *   If an item fails QA due to critical issues that prevent approval, the `T[TicketID]-Description.md` file will be moved from `testing/` to `/doc/dmx/qa/rejected/`.
    *   The "QA Status" in the metadata should be updated to `QA Status: Rejected`.
    *   A "Rejection Notes" section should be added to the file, detailing why it was rejected and referencing any associated bug reports.
    *   The item will be returned to the development team for rework and must re-enter the `incoming/` queue once changes are made.

#### 6. Templates (`templates/`)

*   **Purpose:** To provide standardized formats for submissions and bug reports.
*   **Content:** This directory will contain example markdown files for:
    *   `submission_template.md`
    *   `bug_report_template.md`

This systematic approach, rooted in The Abacus's logic, will ensure that Diametrix reaches new heights of reliability and performance, paving the way for truly predictive certainty in our development cycle.
