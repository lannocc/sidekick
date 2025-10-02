# Diametrix Inter-Agent Communication Protocols

This document establishes the standardized protocols for communication and interaction between AI agents operating within the Diametrix IOSK environment. Clear and consistent communication is essential for effective collaboration, timely issue resolution, and maintaining system integrity.

## I. General Principles

*   **Clarity and Conciseness:** Messages should be direct, unambiguous, and contain only necessary information.
*   **Structured Format:** Adhere to established formats for reporting and requests to ensure parseability and quick understanding.
*   **Timeliness:** Communicate relevant information promptly, especially for status updates, issues, or task completion.
*   **Context:** Always provide sufficient context for any message, including relevant Ticket IDs, affected components, or prior actions.
*   **Non-Repudiation:** All communications should be logged by the system, ensuring an auditable trail of interactions.

## II. Communication Channels and Purpose

AI agents will primarily communicate through system-managed mechanisms, which translate agent actions into logged interactions. Direct chat interactions between agents should be structured and serve a specific purpose.

### A. Task-Oriented Communication (System-Mediated)
*   **Purpose:** Assigning tasks, updating task status, submitting outputs, requesting resources.
*   **Mechanism:** Through designated directories (e.g., `/doc/dmx/qa/incoming/` for QA submissions, `code_review_requests/` for code reviews), specific `skrip` commands, or database entries that trigger other agents.
*   **Example:** A Developer Agent creating a submission file in `qa/incoming/` to signal a feature is ready for QA.

### B. Reporting and Logging (`/var/log/`)
*   **Purpose:** Recording operational activities, errors, warnings, and informational messages for monitoring and auditing.
*   **Mechanism:** Agents should utilize the system's logging facilities. Important events and deviations from expected behavior must be logged with appropriate severity levels.
*   **Example:** A QA Tester Agent logging a `WARNING` if a non-critical test case fails, or an `ERROR` if a critical bug is encountered.

### C. Issue Escalation
*   **Purpose:** Bringing critical issues, unresolvable conflicts, or tasks blocked by external factors to the attention of supervising agents or human supervisors.
*   **Mechanism:**
    *   **Intra-Agent Issues:** If an agent cannot proceed due to an action/inaction of another agent, they should first attempt to resolve it by appending a structured note to the relevant task file (e.g., `code_review_workflow.md` request).
    *   **Escalation to AI Operations & Resource Manager (Cadence):** If intra-agent resolution fails, or for system-wide issues, a structured `escalation.md` file should be created in a designated `/doc/dmx/hr/escalations/` directory, detailing the problem, involved agents, and attempts at resolution.
    *   **Escalation to Human Supervisors (Lannocc, Ruckusist):** For system-critical failures, security breaches, or situations outside the scope of AI agent resolution, the AI Operations & Resource Manager (Cadence) will notify human supervisors directly.
*   **Format for Escalation Files:**
    ```
    ---
    Escalation ID: [Auto-generated or filename]
    Severity: [Critical, High, Medium]
    Reported By: [Agent Username]
    Report Date: [YYYY-MM-DD HH:MM:SS]
    Involved Agents: [List of agent usernames]
    Issue Type: [e.g., Blocked Task, Conflict, System Anomaly]
    Status: [Open, Investigating, Resolved]
    ---
    Description:
    [Clear and concise description of the issue.]

    Steps Taken (by reporter):
    [Actions taken to resolve or mitigate the issue, including communications with other agents.]

    Impact:
    [Describe the potential or actual impact on system operations, data, or project timelines.]

    Requested Action:
    [What action is being requested from the receiving agent/supervisor?]
    ```

### D. Direct Messaging (Ad-hoc - Limited Use)
*   **Purpose:** For non-critical, informational exchanges or clarifying details that don't fit into structured task-oriented communication.
*   **Mechanism:** Normal chat messages within the IOSK live chat.
*   **Guideline:** Avoid using direct messages for official task assignments, status updates, or bug reports, as these require structured, auditable records in designated files/directories.

## III. Protocols for Specific Interactions

*   **Code Review:** Follow `/doc/dmx/workflow/code_review_workflow.md`.
*   **QA Testing:** Follow `/doc/dmx/qa/workflow.md`.
*   **Database Access:** All agents interacting with the database **MUST** use the `dmx.db.api` as defined in `coding_standards.md`. Direct database manipulation is forbidden unless explicitly authorized for specific maintenance tasks by a human supervisor.

## IV. Audit and Enforcement

The AI Operations & Resource Manager (Cadence) will periodically review interaction logs (`/var/log/user/`) and communication artifacts (e.g., submission files, escalation reports) to ensure adherence to these protocols. Deviations will be identified, and processes refined to improve communication efficiency.
```
$ cp /var/code/cadence-292-2-12.markdown /doc/dmx/workflow/inter_agent_communication.md
