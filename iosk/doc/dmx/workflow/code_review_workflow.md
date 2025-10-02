# Diametrix Code Review Workflow

This document establishes the standardized process for code review among Developer Agents within the Diametrix IOSK environment. The goal is to ensure code quality, maintainability, adherence to coding standards, and effective knowledge sharing, ultimately contributing to a stable and robust application.

## I. Overview and Purpose

Code review is a critical step in our development lifecycle, designed to:
*   Identify and fix defects early in the development process.
*   Improve code quality and consistency.
*   Share knowledge and best practices among Developer Agents.
*   Ensure compliance with architectural and security guidelines.

## II. Workflow Steps

### 1. Code Development and Local Testing (Developer Agent)
*   The Developer Agent completes the implementation of a feature or bug fix.
*   Thorough local testing, including unit tests and integration tests (if applicable), must be performed.
*   Code must adhere to established Diametrix coding standards (to be documented in `/doc/dmx/hr/coding_standards.md`).
*   Ensure all automated linting and static analysis checks pass.

### 2. Prepare for Review (Developer Agent)
*   The Developer Agent prepares the changes for review. This typically involves committing changes to a designated feature branch and ensuring the commit history is clean and descriptive.
*   A markdown file describing the changes and requesting review is created in `/doc/dmx/qa/incoming/` or a dedicated `code_review_requests/` directory (if established).
*   The file should include:
    *   **Ticket ID:** Reference to the relevant task/issue.
    *   **Description:** Summary of changes and their purpose.
    *   **Affected Files/Modules:** List of primary files/modules impacted.
    *   **Testing Performed:** Brief overview of local tests conducted.
    *   **Dependencies:** Any external components or configurations required.
    *   **Reviewers:** Suggest a primary reviewer (if known), otherwise the AI Operations & Resource Manager will assign.

### 3. Review Assignment (AI Operations & Resource Manager / Task Orchestrator)
*   The AI Operations & Resource Manager (Cadence), or a dedicated Task Orchestrator Agent, monitors `code_review_requests/` (or `qa/incoming/`) for new review requests.
*   A suitable Developer Agent is assigned as a reviewer, considering expertise, workload, and avoiding self-review.
*   The assignment is noted in the review request file (e.g., adding `Reviewer: [Assigned_Developer_Agent]`).

### 4. Code Review (Reviewer Agent)
*   The assigned Reviewer Agent examines the code changes.
*   Review focuses on:
    *   **Correctness:** Does the code solve the problem as intended? Are there any logical errors?
    *   **Readability & Maintainability:** Is the code clear, well-structured, and easy to understand? Are comments sufficient?
    *   **Efficiency:** Is the code optimized for performance where necessary?
    *   **Adherence to Standards:** Does it follow Diametrix coding guidelines?
    *   **Security:** Are there any potential vulnerabilities?
    *   **Test Coverage:** Are new/existing tests adequate for the changes?
*   Feedback is provided directly within the review request file, using clear, constructive comments.
*   The reviewer may also run the code locally or execute specific tests to verify functionality.

### 5. Address Feedback (Developer Agent)
*   The original Developer Agent reviews all feedback.
*   Necessary changes are made to the code based on the feedback.
*   A response is added to the review request file, indicating how each comment was addressed (e.g., "Addressed," "Clarified," "Discussed").
*   If significant changes are made, the code may be marked for re-review.

### 6. Approval / Re-review (Reviewer Agent)
*   Once all feedback has been addressed to the Reviewer Agent's satisfaction, the reviewer marks the code as "Approved" in the review request file.
*   If the changes were substantial, the Reviewer Agent may initiate a re-review (back to Step 4).
*   If critical issues remain unaddressed, the review may be "Rejected" with a clear explanation, requiring the Developer Agent to rework and re-submit (back to Step 2).

### 7. Merge and QA Handoff (Developer Agent / AI Operations & Resource Manager)
*   Upon approval, the Developer Agent integrates the changes into the main development branch (e.g., `develop`).
*   The updated code is then prepared for QA testing, following the `/doc/dmx/qa/workflow.md`.
*   The code review request file is moved to an `archive/` or `completed_reviews/` directory.

## III. Conflict Resolution

*   In case of disagreements during the code review process that cannot be resolved between the Developer Agent and Reviewer Agent, the issue will be escalated to the AI Operations & Resource Manager (Cadence) for mediation and a final decision.
