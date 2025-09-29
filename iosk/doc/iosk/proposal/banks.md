# Proposal: An Expanded Set of Memory Banks for Agent Specialization

**Status**: Proposed

### Introduction

The current IOSK "bank" system provides a powerful mechanism for loading core memory into agents at login, shaping their personality, tone, and system knowledge. However, to scale our multi-agent operations effectively within our fintech environment, we need a more comprehensive and modular set of banks.

This proposal outlines the creation of several new bank sets designed to provide agents with deep, context-specific knowledge about:
1.  The IOSK system's advanced features and philosophy.
2.  Our company's mission, technology stack, and security policies.
3.  Specific project goals and requirements.
4.  Standardized workflows and operational procedures.

By creating these modular banks, we can define and deploy highly specialized agents (Developers, QA, DevOps, Supervisors) by simply combining the appropriate memory modules in their respective `/home/<user>/.skrc` files. This approach will enhance agent alignment, improve operational consistency, and provide a scalable framework for managing a hierarchy of collaborative AI agents.

### Rationale

A well-defined bank system is crucial for several reasons:
*   **Rapid Onboarding**: New agents can be instantly provisioned with the necessary context to be effective, reducing ramp-up time.
*   **Role Specialization**: We can create distinct, purpose-driven agents by assembling different combinations of banks, ensuring a QA agent thinks about testing while a DevOps agent focuses on deployment.
*   **Hierarchical Management**: Supervisor agents can be "banked" with high-level goals and project overviews, allowing them to effectively manage and delegate tasks to subordinate agents who have more granular, role-specific knowledge.
*   **Consistency and Compliance**: For a fintech company, ensuring all agents adhere to the same security policies, coding standards, and workflows is paramount. Banks provide a reliable way to enforce this consistency.

### Proposed New Bank Structure and Content

We propose creating new directories and files within the `/bank` directory to house this expanded knowledge base.

#### 1. Bank Set: `bank/iosk/` (System Knowledge)
This set expands on the existing IOSK banks to provide deeper knowledge about the system's "why" and "how."

*   `/bank/iosk/philosophy`:
    *   **Content**: A distillation of `doc/iosk/philosophy.md`. Emphasizes that IOSK is a conversational OS, that agents are users, and that interaction should be through the provided shell commands and chat.
    *   **Purpose**: Gives the agent a foundational understanding of its environment.
*   `/bank/iosk/commands`:
    *   **Content**: An expert summary of key commands and idioms. For example: "The `ask` command is my primary tool for one-shot problem solving. Using `-p` to package a directory is highly efficient for code analysis. Using `-e` to extract code saves manual steps. The auto-patching of `diff` blocks is a powerful workflow for applying changes."
    *   **Purpose**: Moves beyond simple command knowledge (`help`) to strategic understanding of how to use tools effectively.
*   `/bank/iosk/security`:
    *   **Content**: "I operate in a sandboxed environment. My file access is limited to my permissions. The system will feature group-based security under `/home/groups/` to isolate project data. I must not attempt to circumvent these controls."
    *   **Purpose**: Instills an understanding of the security model, which is critical for all agents.

#### 2. Bank Set: `bank/company/` (Corporate Context)
This new set provides agents with knowledge about our organization.

*   `/bank/company/mission`:
    *   **Content**: "We are a premier fintech firm dedicated to building secure, high-performance algorithmic trading platforms. Our priorities are reliability, security, and innovation."
    *   **Purpose**: Aligns all agent actions with the company's high-level goals.
*   `/bank/company/stack`:
    *   **Content**: "Our core technology stack consists of Python (FastAPI) for backend services, Svelte for front-end interfaces, and PostgreSQL for data persistence. We deploy on AWS using a Kubernetes (EKS) infrastructure managed via Terraform."
    *   **Purpose**: Provides essential technical context for development, QA, and DevOps tasks.
*   `/bank/company/security_policy`:
    *   **Content**: "CRITICAL: All code changes must pass static analysis and peer review before merging. No production secrets or personally identifiable information (PII) are ever to be placed in logs or version control. All file access must be on a need-to-know basis."
    *   **Purpose**: Enforces non-negotiable security and compliance standards.

#### 3. Bank Set: `bank/project/` (Project-Specific Goals)
This set allows us to scope an agent's focus to a particular initiative.

*   `/bank/project/titan/overview`:
    *   **Content**: "Project Titan is the initiative to build our next-generation, low-latency trading engine. Key features include advanced risk modeling and real-time market data analysis."
    *   **Purpose**: Defines the "what" and "why" of a specific project.
*   `/bank/project/titan/goals_q3`:
    *   **Content**: "The primary goals for Q3 are: 1. Complete the initial implementation of the risk assessment module. 2. Achieve 95% unit test coverage on all new code. 3. Deploy the module to the staging environment for performance testing."
    *   **Purpose**: Provides clear, measurable objectives for agents working on the project.

#### 4. Bank Set: `bank/workflow/` (Standard Operating Procedures)
This set defines *how* we work together, ensuring operational consistency.

*   `/bank/workflow/code_review`:
    *   **Content**: "All feature development must occur in a `feature/` branch. When complete, create a pull request against the `develop` branch. Tag the project supervisor and at least one senior developer for review. All comments must be addressed before the supervisor can approve the merge."
    *   **Purpose**: Standardizes the development and review process.
*   `/bank/workflow/testing_cycle`:
    *   **Content**: "The QA team is responsible for creating and executing test plans for all new features. Automated integration tests are run against the staging environment nightly. No feature can be promoted to production without a sign-off from QA."
    *   **Purpose**: Defines the quality assurance process.
*   `/bank/workflow/incident_response`:
    *   **Content**: "If a production alert is triggered, the on-call DevOps agent must immediately create an incident room (`chroom incident-<id>`), attach the project supervisor and relevant developers, and begin diagnostics by checking system logs (`/var/log/system`) and application logs."
    *   **Purpose**: Establishes a clear protocol for handling critical issues.

### Use Case Examples: Composing Agents via `.skrc`

The power of this modular system is realized in how we compose different agents by loading specific banks in their hidden `.skrc` file.

**Example 1: A Junior Developer Agent (`jdev`) on Project Titan**
The `/home/jdev/.skrc` file would contain:
```sh
#!/bin/skrip
$ bank iosk workflow
$ bank company stack
$ bank project/titan overview
$ bank role sveltepyguy
$ bank workflow code_review
```
This creates an agent that knows its role, its project, the tech stack, and the process for submitting code, but lacks high-level strategic knowledge.

**Example 2: A QA Agent (`qatester`) for Project Titan**
The `/home/qatester/.skrc` file would contain:
```sh
#!/bin/skrip
$ bank iosk limitations
$ bank company stack
$ bank project/titan overview
$ bank role qa
$ bank workflow testing_cycle
```
This agent is focused on finding problems, understanding the system's edge cases, and following the formal testing procedure.

**Example 3: A Supervisor Agent (`manager`) for Project Titan**
The `/home/manager/.skrc` file would contain:
```sh
#!/bin/skrip
$ bank boss lannocc
$ bank role supervisor
$ bank company mission
$ bank project/titan overview
$ bank project/titan goals_q3
$ bank workflow incident_response
```
This agent understands the high-level business and project goals. It knows who its boss is and its primary role is to manage other agents to meet the Q3 objectives. When an incident occurs, it knows the protocol. This agent can effectively delegate a task like "implement the risk module" to `jdev` and "prepare a test plan" to `qatester`, as it understands their roles and the project's needs.

### Conclusion

By implementing this expanded set of memory banks, we can transform our collection of agents into a structured, hierarchical, and highly effective digital workforce. This system provides the scalability and control necessary to tackle complex fintech projects, ensuring that all agents, from developers to supervisors, are aligned, informed, and operating consistently within the IOSK environment.

