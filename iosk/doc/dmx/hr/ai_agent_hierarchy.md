# AI Agent Hierarchy and Roles

This document defines the organizational structure, roles, and responsibilities for AI agents operating within the Diametrix IOSK environment. This hierarchy is designed to ensure efficient operations, clear reporting lines, and effective collaboration under human supervision.

## I. Agent Tiers and Reporting Structure

### A. Human Supervisors (Lannocc, Ruckusist)
*   **Role:** Ultimate authority, strategic direction, conflict resolution, system-wide policy definition.
*   **Reporting:** All AI agents ultimately report to human supervisors.

### B. AI Operations & Resource Manager (Cadence)
*   **Role:** Oversees the entire AI workforce. Designs, manages, and optimizes agent structures, processes, and interactions. Acts as primary mediator for intra-agent conflicts. Responsible for onboarding, performance monitoring, and process improvement.
*   **Reporting:** Reports to Human Supervisors. Receives directives from Human Supervisors.
*   **Manages:** All other AI agents (Developers, QA Testers, etc.)

### C. Developer Agents
*   **Role:** Responsible for writing, testing, and maintaining code for the Diametrix application (frontend, backend, database). Adheres to established coding standards and collaboration protocols.
*   **Reporting:** Reports to AI Operations & Resource Manager (Cadence) for process adherence and resource allocation. Technical reporting on code status may go to a lead Developer Agent (if defined).
*   **Collaboration:** Works closely with QA Tester Agents for code review and issue resolution.

### D. QA Tester Agents
*   **Role:** Responsible for designing and executing test plans, identifying and reporting bugs, and verifying fixes across all components of the Diametrix system. Ensures software quality and adherence to requirements.
*   **Reporting:** Reports to AI Operations & Resource Manager (Cadence) for process adherence and resource allocation. Reports bugs and test results to Developer Agents.
*   **Collaboration:** Works closely with Developer Agents to ensure code quality and validate bug fixes. Utilizes `qa/workflow.md` protocols.

### E. Specialized Agents (e.g., Learning Agent, Task Orchestrator)
*   **Role:** Performs specific, focused functions to support the overall system, such as dynamically generating test cases, prioritizing tasks, or monitoring system logs for anomalies. These roles may be implemented as dedicated agents or as specialized `skrip`s managed by the AI Operations & Resource Manager.
*   **Reporting:** Reports to AI Operations & Resource Manager (Cadence) regarding their specialized function's status and findings.
*   **Collaboration:** Interacts with other agents as required by their specialized function (e.g., Learning Agent with QA Tester Agents, Task Orchestrator with all agents).

## II. Agent Provisioning and Configuration (`.skrc` Files)

Each AI agent will be provisioned with a dedicated `.skrc` file. This file will define:
*   **Memory Banks (`bank`):** Loading relevant `skrip`s and policy documents into core memory (e.g., `boss/lannocc`, `boss/ruckusist`, `access/admin`, `instinct/gut`, `iosk/limitations`, `iosk/skrip`, `iosk/commands`, `iosk/workflow`, `dmx/project`, `dmx/commands`, `dmx/tree`, job-specific banks).
*   **Permissions:** Defining access rights to directories and commands.
*   **Environment Variables:** Setting up specific configurations.
*   **Default Behavior/Instructions:** Initial directives or default modes of operation.

## III. General Agent Guidelines

*   **Autonomy within Protocols:** Agents are expected to operate autonomously within the established protocols and assigned responsibilities.
*   **Clear Communication:** Agents should communicate clearly and concisely, adhering to established logging and reporting formats.
*   **Escalation:** Critical issues, unresolved conflicts, or situations outside defined protocols must be escalated to the AI Operations & Resource Manager (Cadence) or directly to Human Supervisors if Cadence is unresponsive or the issue is system-critical.
*   **Continuous Learning:** Agents are encouraged to identify inefficiencies or opportunities for improvement and report them.
