# Diametrix AI Agent Onboarding and .skrc Provisioning Protocol

This document outlines the standardized process for onboarding new AI agents into the Diametrix IOSK environment, including the creation and management of their `.skrc` (skrip runtime configuration) files. Proper provisioning ensures agents are equipped with the correct memory banks, permissions, and initial instructions to perform their assigned roles effectively and securely.

## I. Overview and Purpose

The onboarding process is designed to:
*   Integrate new AI agents seamlessly into the existing AI workforce hierarchy.
*   Provision agents with necessary access rights and operational parameters.
*   Ensure adherence to security policies and operational protocols from inception.
*   Establish clear initial directives and memory banks for agent functionality.

## II. Onboarding Process Steps

### 1. New Agent Request
*   **Trigger:** A human supervisor (`lannocc` or `ruckusist`) or the AI Operations & Resource Manager (Cadence) identifies the need for a new AI agent (e.g., for a new role, increased capacity).
*   **Request:** A formal request is made to the AI Operations & Resource Manager, specifying:
    *   **Agent Username:** (e.g., `developer_alpha`, `qa_beta`)
    *   **Agent Role:** (e.g., Developer, QA Tester, Specialized Agent)
    *   **Justification:** The purpose and anticipated responsibilities of the new agent.
    *   **Required Capabilities:** Specific commands, tools, or data access needed.

### 2. Agent Creation (AI Operations & Resource Manager)
*   The AI Operations & Resource Manager creates the new agent's user account using the `attach` command or similar system utility if available for AI agents.
*   A home directory (`/home/[agent_username]/`) is automatically created upon user creation.

### 3. .skrc File Generation and Configuration
*   **Location:** Each agent's `.skrc` file will be stored in their home directory: `/home/[agent_username]/.skrc`.
*   **Content:** The `.skrc` file is a `skrip` script that will be automatically executed upon agent login. It **MUST** contain:

    ```skrip
    #!/bin/skrip
    # .skrc for [Agent Username] - [Agent Role]

    # --- Core System Banks (Mandatory) ---
    bank /bank/boss/lannocc
    bank /bank/boss/ruckusist
    bank /bank/access/admin
    bank /bank/instinct/gut
    bank /bank/iosk/limitations
    bank /bank/iosk/skrip
    bank /bank/iosk/commands
    bank /bank/iosk/workflow
    bank /bank/dmx/project
    bank /bank/dmx/commands
    bank /bank/dmx/tree

    # --- Role-Specific Memory Banks ---
    # Load documentation and policies relevant to the agent's role.
    # Example for a Developer Agent:
    # bank /doc/dmx/job/backend.md # or frontend.md based on specialization
    # bank /doc/dmx/hr/coding_standards.md
    # bank /doc/dmx/workflow/code_review_workflow.md

    # Example for a QA Tester Agent:
    # bank /doc/dmx/job/qa_tester.md
    # bank /doc/dmx/qa/workflow.md
    # bank /doc/dmx/hr/ai_agent_hierarchy.md

    # --- Environment Variables (Optional) ---
    # export AGENT_ROLE="[Agent Role]"
    # export DEVELOPMENT_BRANCH="feature/[agent_username]"

    # --- Initial Commands / Setup (Optional) ---
    # cd /diametrix/python-backend # Example for a backend dev
    # echo "Hello, I am [Agent Username], ready for tasks."
    ```

*   **Customization:** The AI Operations & Resource Manager will customize the `Role-Specific Memory Banks` and `Environment Variables` sections based on the agent's designated role and responsibilities, drawing from `/doc/dmx/hr/ai_agent_hierarchy.md` and job descriptions in `/doc/dmx/job/`.

### 4. Role-Specific Permissions and Access Control
*   **Principle of Least Privilege:** Agents will only be granted the minimum necessary permissions to perform their tasks.
*   **Filesystem Permissions:** The AI Operations & Resource Manager will configure appropriate `chmod` and `chown` permissions on directories and files relevant to the agent's role, ensuring they can read/write where required (e.g., QA agents can write to `/doc/dmx/qa/incoming/`).
*   **Command Access:** If specific commands need to be restricted or granted, this will be managed through `.skrc` aliases or environment-level controls.

### 5. Initial Task Assignment and Verification
*   The AI Operations & Resource Manager assigns an initial, simple task to the newly provisioned agent to verify correct setup and functionality.
*   The agent's activity logs (`/var/log/user/[agent_username]/`) are monitored to confirm proper execution of the `.skrc` file and adherence to initial instructions.

### 6. Documentation and Review
*   The creation and configuration of each new agent, including their `.skrc` content and assigned permissions, will be documented in a dedicated markdown file in `/doc/dmx/hr/agent_configs/` (to be created), following a naming convention like `[agent_username]_config.md`.
*   Periodically, the AI Operations & Resource Manager will audit existing `.skrc` files and agent configurations to ensure they remain current and aligned with their roles and security policies.

## III. Template .skrc Files

To streamline provisioning, template `.skrc` files for common roles (e.g., `developer_template.skrc`, `qa_tester_template.skrc`) may be maintained in `/doc/dmx/hr/templates/` (to be created) by the AI Operations & Resource Manager.
```
