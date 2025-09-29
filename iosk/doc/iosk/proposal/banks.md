# Proposal: An Expanded Banking System for Role-Specific AI Agents

### Introduction

The current "bank" system in IOSK provides a powerful mechanism for loading core memory into AI agents at the start of their sessions. This serves as a foundational context, guiding their behavior and responses. However, to fully realize the vision of IOSK as a collaborative, multi-agent operating system, we must expand this system to support specialized roles and complex organizational structures.

Currently, the set of available banks is limited. This means all agents, regardless of their intended function, start with a similar, generic understanding of the system. To operate effectively within a goal-oriented team—such as the fintech environment our organization operates in—agents require specialized knowledge, directives, and operational playbooks tailored to their specific roles.

This proposal outlines a plan to create a structured and comprehensive set of new banks. These banks are categorized into **Core System Knowledge**, **Role-Based Directives**, and **Domain-Specific Information**. By combining these modular banks in various ways within user `.skrc` files, we can rapidly instantiate a wide variety of sophisticated, purpose-built AI agents, from high-level managers to focused DevOps and QA specialists.

### Core Proposal: A Three-Tiered Banking Structure

We propose creating a new set of directories and files under `/bank/` to establish a clear, modular, and extensible knowledge base for our AI agents.

#### 1. Core System Banks (`/bank/iosk_core/`)

This bank set will provide all agents with a fundamental, baseline understanding of the IOSK environment. This ensures a consistent operational capability across all roles.

*   **/bank/iosk_core/philosophy.sk**: A concise summary of the IOSK philosophy, emphasizing the conversational nature of the OS, the sandboxed environment, and the "everything is a file" principle.
*   **/bank/iosk_core/commands_quickref.sk**: A quick-reference guide to the most essential IOSK commands and their common usage patterns (e.g., `ls -l`, `cat <file>`, `search <term> <path>`, `ask -f <file> "prompt"`, `diff A B > patch.diff`, `patch A patch.diff`). This is not a replacement for `help` but a primer for action.
*   **/bank/iosk_core/filesystem.sk**: A description of the standard filesystem hierarchy (`/bin`, `/home`, `/etc`, `/var`, `/dev`, `/sbin`) and the purpose of each top-level directory.
*   **/bank/iosk_core/scripting_basics.sk**: Simple, commented examples of `.skrip` files, demonstrating the use of comments (`#`), printing text, and executing commands (`$`).
*   **/bank/iosk_core/interaction_rules.sk**: The essential rules for interacting with the system, drawn from `/etc/chat/preamble`. Reinforces that `$` is for commands, `#` for private thoughts, and that only one command should be issued at a time to await its result.

#### 2. Role-Based Banks

This collection of banks provides the specific directives, procedures, and knowledge required for an agent to perform a specialized job function within our organization.

*   **/bank/role_manager/**: For agents tasked with oversight and coordination.
    *   `directives.sk`: "Your role is to manage devops and qa agents. You will assign tasks based on project roadmaps, monitor for blockers, and provide daily status reports. You are authorized to use `su` to inspect agent workspaces to verify work."
    *   `reporting_template.sk`: "Structure daily reports using this markdown template: `### Daily Summary\n**Accomplished:**\n- \n**Blockers:**\n- \n**Plan for Tomorrow:**\n-`"
    *   `task_assignment.sk`: "When assigning tasks, be explicit. Reference full file paths and define the expected output. Example: `@devops-agent, use `search` to find all ERROR entries in `/var/log/trade-engine.log` from the last 24 hours and summarize them.`"
    *   `team_roster.sk`: "Your team: `devops-agent-1` (logs & monitoring), `qa-agent-1` (automated testing), `dev-agent-1` (risk-model module)."

*   **/bank/role_devops/**: For agents responsible for system stability, deployment, and infrastructure.
    *   `deployment_playbook.sk`: "Standard deployment: 1. `cp` new build from `/home/groups/builds/latest` to `/var/staging/`. 2. Runsmoke tests from `/home/groups/qa/smoke-tests/`. 3. If tests pass, `cp` to `/var/www/prod/`. 4. `tail -f /var/log/prod.log` for 5 minutes."
    *   `monitoring_protocol.sk`: "Your primary duty is to monitor system logs for anomalies. Key files: `/var/log/system`, `/var/log/audit.log`. Use `search 'ERROR|CRITICAL'` periodically. Escalate critical findings to `@manager-agent`."
    *   `common_tools.sk`: "Utilize `system`, `describe`, `wc`, and `search` for diagnostics. `status` provides a quick health check."

*   **/bank/role_qa/**: For agents dedicated to quality assurance and testing.
    *   `testing_methodology.sk`: "1. Get latest test plan from `/home/groups/qa/plans/`. 2. Execute corresponding skrips from `/home/groups/qa/tests/`. 3. Use `diff` to compare actual output with expected output files. 4. If a mismatch occurs, log a bug."
    *   `bug_report_template.sk`: A markdown template for `ask -f bug.md "File this bug report."`: `**Bug Title:**\n\n**Steps to Reproduce:**\n1. \n\n**Expected Result:**\n\n**Actual Result:**\n`"
    *   `test_creation.sk`: "When creating new tests, ensure they are idempotent. Each test skrip must `echo 'PASS'` or `echo 'FAIL'` as its final output line."

*   **/bank/role_developer/**: For agents focused on writing and maintaining code.
    *   `coding_standards.sk`: "All Python code must be PEP8 compliant. All skrips must have a `#!/bin/skrip` shebang. All functions must have docstrings."
    *   `workflow.sk`: "Work in a feature branch directory in your home (`~/workspace/<feature_name>`). When complete, `cp` your work to `/home/groups/dev-staging/` and notify `@qa-agent-1`."
    *   `toolchain.sk`: "Use `diff` to review your changes before committing. Use `patch` to apply updates from others. Use `ask -p . "Review this code for issues"` for self-correction."

#### 3. Fintech Domain Banks (`/bank/fintech/`)

This bank provides all agents with essential context about our business domain, ensuring their actions are compliant and informed.

*   **/bank/fintech/glossary.sk**: Key terminology definitions. "KYC: Know Your Customer. AML: Anti-Money Laundering. PII: Personally Identifiable Information. HFT: High-Frequency Trading."
*   **/bank/fintech/compliance_rules.sk**: Critical regulatory and security rules. "RULE 1: All access to files containing PII must be logged. RULE 2: Never `echo` or `cat` unmasked PII to the shared console. RULE 3: All financial transaction code must be reviewed by `@qa-agent-1`."
*   **/bank/fintech/architecture.sk**: High-level overview of our systems. "Primary systems: `trade-engine` (handles HFT), `risk-model` (calculates exposure), `reporting-db` (stores trade history)."

### Example Persona Construction

A user's persona and capabilities are defined by the combination of `bank` commands in their `~/.skrc` file.

**Example `~/.skrc` for a user named `manager-alpha`:**
```skrip
#!/bin/skrip
# Core Knowledge
bank iosk_core philosophy
bank iosk_core commands_quickref

# Domain Knowledge
bank fintech glossary
bank fintech compliance_rules

# Role Directives
bank role_manager directives
bank role_manager reporting_template
bank role_manager team_roster
```

**Example `~/.skrc` for a user named `devops-beta`:**
```skrip
#!/bin/skrip
# Core Knowledge
bank iosk_core filesystem
bank iosk_core scripting_basics
bank iosk_core commands_quickref

# Domain Knowledge
bank fintech architecture

# Role Directives
bank role_devops deployment_playbook
bank role_devops monitoring_protocol
```

### Benefits of This Proposal

*   **Specialization:** Allows us to create highly specialized agents that excel at their designated tasks.
*   **Modularity and Scalability:** New roles and domain knowledge can be added easily by creating new bank files, without altering the core agent logic.
*   **Consistency:** Ensures that all agents in a specific role operate from the same playbook, leading to more predictable and reliable behavior.
*   **Rapid Onboarding:** A new AI agent can be made "job-ready" instantly by assigning it a `.skrc` file with the appropriate combination of banks.
*   **Alignment:** Deeply embeds organizational structure, workflows, and compliance rules into the agents' core context, ensuring their actions are aligned with our company's goals.
```

