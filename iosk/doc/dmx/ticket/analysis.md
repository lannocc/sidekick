# Analysis of Open Diametrix Tickets

This document provides a strategic analysis of the open tickets related to the Diametrix (dmx) project. The goal is to categorize and group these tasks to facilitate prioritization and assignment, whether to automated agents within the IOSK environment or to human operators.

Three different scenarios for grouping the tickets are presented below, each tailored to a specific strategic objective:
1.  **Priority for First Customer Launch**: Organizes tasks based on their criticality for delivering a viable product to the first customer.
2.  **Agent Role Delegation**: Groups tasks by the technical role best suited to address them, ideal for a supervisor agent delegating work.
3.  **IOSK Agent vs. Human Intervention**: Separates tasks that can be performed by agents within the IOSK sandbox from those requiring external access, research, or physical action by a human.

---

## Scenario 1: Grouping by Priority for First Customer Launch

This breakdown prioritizes tasks required to achieve a Minimum Viable Product (MVP) for the first bank customer, separating them from enhancements and long-term features.

### Group 1: Critical for MVP & Initial Launch
These tickets represent core functionality, critical bug fixes, and essential security measures. They must be resolved for a stable, secure, and functional product launch.

*   **T15**: W-2 data
*   **T16**: duplicity of schedules
*   **T17**: pay slip data
*   **T38**: Removing document / cleanup
*   **T48**: Documents uploaded to view but not spread
*   **T52**: closing applications
*   **T132**: Projected ratios, Tax Returns vs Summary
*   **T167**: Summary screen Proposed Mortgages
*   **T172**: Personal Financial Statement
*   **T175**: Summary tab
*   **T176**: Schedules tab
*   **T177**: Tax Return Tab
*   **T184**: Full manual entry
*   **T187**: Incorrect CPLTD for Long-Term and Current Liabilities
*   **T188**: K-1 and Ownership in Related Entities
*   **T189**: Summary tab calculations
*   **T203**: Tax Returns income after taxes
*   **T205**: Schedule D calculation order re: averages
*   **T206**: 1040 projected total income incorrect
*   **T208**: Demo.Diametrixfs link does not automatically ask you to sign in when opening the page.
*   **T209**: Data retention policy and SECURITY
*   **T210**: Actual login with SECURITY (user model)
*   **T221**: Cash Flow (Auto/Manual)
*   **T222**: Balance Sheet (Current/Projected)
*   **T224**: Repayment Capacity
*   **T225**: Analysis of Financials
*   **T226**: Yr. 1 Summary
*   **T236**: Fixed-point arithmetic for Money
*   **T241**: Customization "switch" (calculation overrides)
*   **T242**: New Bank Setup
*   **T244**: Session model
*   **T250**: web.py API and cleanup
*   **T253**: Field custom format options refactor
*   **T263**: Misc. Farm/Ag

### Group 2: High Priority Enhancements
These tickets represent significant improvements to usability, data accuracy, and the overall user experience. While not strictly blockers for launch, they should be addressed as soon as possible.

*   **T105**: Credit report items
*   **T134**: Reading supplemental notes (K-1)
*   **T140**: Handling divide by zero, etc.
*   **T152**: Confidence
*   **T159**: Log profile item add/delete
*   **T164**: Flag for mismatched documents
*   **T169**: Schedule K-1 training
*   **T178**: Number formatting / precision
*   **T179**: Flagged issues screen
*   **T181**: Quick jump back to source document / field
*   **T182**: PFS "Mortgaged to" should be lender
*   **T185**: Schedule E property type
*   **T186**: Proposed loan market value
*   **T190**: Remove "Existing & Proposed Debt" from Summary
*   **T192**: Consistent capitalization of field labels
*   **T193**: Remove interest rate on existing debt
*   **T194**: Tax Schedules "Annual payments"
*   **T197**: Ignore Schedule E "other" (amortization)
*   **T199**: Schedule 1 training
*   **T200**: Schedule 1 averages
*   **T201**: Schedule 1 new field "Non-Recurring Incomes"
*   **T202**: Positive vs negative money
*   **T207**: T207 Hide TNW and Working Capital
*   **T216**: On-screen calculator
*   **T229**: Ability to clear (erase) field values
*   **T233**: Unified Document Manager
*   **T234**: Notes on documents
*   **T246**: Fix the view for financial statements
*   **T247**: Color-coded calculated vs manual fields
*   **T248**: app integrity key
*   **T249**: No "Enter" key on mobile (or Escape)
*   **T254**: Ability to split tax packet
*   **T258**: "Viewport"
*   **T259**: key mode
*   **T260**: view fixes / adjustments / improvements
*   **T261**: Existing long term debt in PFS.
*   **T262**: Downloadable ".dmx" blob
*   **T50**: only display line items that have values
*   **T54**: Schedule 1 other items
*   **T55**: "Assumed term"
*   **T56**: Schedules annual payments
*   **T62**: Liability payments include tax+insurance?

### Group 3: "Pro" Features & Long-Term Vision
These are features planned for a premium "Pro" version or represent longer-term architectural goals.

*   **T25**: Financial statement processor
*   **T26**: Blank values processor
*   **T31**: math checking
*   **T111**: Balance Sheet - FS
*   **T112**: Income Statements - FS
*   **T113**: Income Statement Analysis
*   **T114**: UCA Cash Flow Analysis
*   **T115**: WIP
*   **T116**: AR Inv. Collateral Evaluation
*   **T117**: Internationalization
*   **T129**: Guarantor
*   **T136**: Form 1120 (C) processor
*   **T151**: Check beginning- vs end-of-year balance sheet
*   **T153**: Form 1125-A processor
*   **T161**: Balance Sheet processor
*   **T162**: Income Statement processor
*   **T163**: Check previous year to current year statement uploads
*   **T165**: Schedules M-1/M-2
*   **T227**: Specific Equip. for Collateral
*   **T256**: Business "Projected" column(s)
*   **T257**: Input Assumptions Tab

### Group 4: Administrative, Meta & Analysis Tasks
These tickets are for internal processes, require human analysis before implementation, or are meta-tickets that bundle other tasks.

*   **T39**: forced user / single-user mode
*   **T41**: policy editor
*   **T100**: Summary cell E46 notes (and all other "Cell notes to look at" tickets: T61, T63, T65-T100)
*   **T170**: General Bugs & comments
*   **T235**: Alice Smith (Test) bugs and comments 7/29/25
*   **T252**: Business Section Overview

---

## Scenario 2: Grouping by Agent Role

This breakdown organizes tasks according to the primary skillset required, suitable for delegation by a supervisor agent to specialized developer agents.

### Group 1: Backend Developer (Python Agent)
Tasks related to core application logic, calculations, database interactions, AI/processor training, and system architecture.

*   **T15**: W-2 data
*   **T16**: duplicity of schedules
*   **T17**: pay slip data
*   **T25**: Financial statement processor
*   **T31**: math checking
*   **T38**: Removing document / cleanup
*   **T48**: Documents uploaded to view but not spread
*   **T52**: closing applications
*   **T54**: Schedule 1 other items
*   **T55**: "Assumed term"
*   **T56**: Schedules annual payments
*   **T62**: Liability payments include tax+insurance?
*   **T64**: Removing spousal income
*   **T105**: Credit report items
*   **T129**: Guarantor
*   **T132**: Projected ratios, Tax Returns vs Summary
*   **T134**: Reading supplemental notes (K-1)
*   **T136**: Form 1120 (C) processor
*   **T140**: Handling divide by zero, etc.
*   **T151**: Check beginning- vs end-of-year balance sheet
*   **T153**: Form 1125-A processor
*   **T158**: Business percent ownership * capital
*   **T159**: Log profile item add/delete
*   **T160**: Tax Returns H:40
*   **T161**: Balance Sheet processor
*   **T162**: Income Statement processor
*   **T163**: Check previous year to current year statement uploads
*   **T164**: Flag for mismatched documents
*   **T165**: Schedules M-1/M-2
*   **T167**: Summary screen Proposed Mortgages
*   **T169**: Schedule K-1 training
*   **T182**: PFS "Mortgaged to" should be lender
*   **T185**: Schedule E property type
*   **T186**: Proposed loan market value
*   **T187**: Incorrect CPLTD for Long-Term and Current Liabilities
*   **T188**: K-1 and Ownership in Related Entities
*   **T189**: Summary tab calculations
*   **T194**: Tax Schedules "Annual payments"
*   **T197**: Ignore Schedule E "other" (amortization)
*   **T199**: Schedule 1 training
*   **T200**: Schedule 1 averages
*   **T201**: Schedule 1 new field "Non-Recurring Incomes"
*   **T203**: Tax Returns income after taxes
*   **T204**: Form 4835 projected/average
*   **T205**: Schedule D calculation order re: averages
*   **T206**: 1040 projected total income incorrect
*   **T236**: Fixed-point arithmetic for Money
*   **T239**: Identity matching
*   **T241**: Customization "switch" (calculation overrides)
*   **T248**: app integrity key
*   **T250**: web.py API and cleanup
*   **T253**: Field custom format options refactor
*   **T254**: Ability to split tax packet
*   **T256**: Business "Projected" column(s)
*   **T261**: Existing long term debt in PFS.
*   **T262**: Downloadable ".dmx" blob

### Group 2: Frontend Developer (Svelte Agent)
Tasks focused on UI components, visual presentation, user interaction flows, and improving the overall user experience.

*   **T50**: only display line items that have values
*   **T133**: color system for the income analysis ratios
*   **T178**: Number formatting / precision
*   **T179**: Flagged issues screen
*   **T181**: Quick jump back to source document / field
*   **T190**: Remove "Existing & Proposed Debt" from Summary
*   **T192**: Consistent capitalization of field labels
*   **T193**: Remove interest rate on existing debt
*   **T202**: Positive vs negative money
*   **T207**: T207 Hide TNW and Working Capital
*   **T216**: On-screen calculator
*   **T229**: Ability to clear (erase) field values
*   **T233**: Unified Document Manager
*   **T234**: Notes on documents
*   **T246**: Fix the view for financial statements
*   **T247**: Color-coded calculated vs manual fields
*   **T249**: No "Enter" key on mobile (or Escape)
*   **T258**: "Viewport"
*   **T259**: key mode
*   **T260**: view fixes / adjustments / improvements

### Group 3: DevOps & System Admin Agent
Tasks related to infrastructure, security policies, deployment, and system-level configuration.

*   **T39**: forced user / single-user mode
*   **T41**: policy editor
*   **T117**: Internationalization
*   **T166**: Keep uploaded documents / data retention policy
*   **T210**: Actual login with SECURITY (user model)
*   **T242**: New Bank Setup
*   **T244**: Session model
*   **T255**: Google processor migrations

### Group 4: QA, Analyst, & Project Management
Tasks requiring high-level analysis, business logic clarification, creation of test data, or are meta-tickets needing decomposition.

*   **T26**: Blank values processor
*   **T100**: Summary cell E46 notes (and all other "Cell notes to look at" tickets)
*   **T111**: Balance Sheet - FS
*   **T112**: Income Statements - FS
*   **T113**: Income Statement Analysis
*   **T114**: UCA Cash Flow Analysis
*   **T115**: WIP
*   **T116**: AR Inv. Collateral Evaluation
*   **T157**: Tax Returns: State/local "projected" tax
*   **T170**: General Bugs & comments
*   **T172**: Personal Financial Statement
*   **T175**: Summary tab
*   **T176**: Schedules tab
*   **T177**: Tax Return Tab
*   **T184**: Full manual entry
*   **T221**: Cash Flow (Auto/Manual)
*   **T222**: Balance Sheet (Current/Projected)
*   **T224**: Repayment Capacity
*   **T225**: Analysis of Financials
*   **T226**: Yr. 1 Summary
*   **T227**: Specific Equip. for Collateral
*   **T235**: Alice Smith (Test) bugs and comments 7/29/25
*   **T252**: Business Section Overview
*   **T257**: Input Assumptions Tab
*   **T263**: Misc. Farm/Ag

---

## Scenario 3: Grouping by IOSK Agent vs. Human Intervention

This breakdown separates tasks that can be completed within the IOSK sandbox from those requiring action in the real world or on external systems.

### Group 1: Assignable to IOSK Agents
The vast majority of tickets, encompassing all code changes, bug fixes, and feature implementations for both the Python backend and Svelte frontend, fall into this category. These are tasks that involve editing files within the `/diametrix` project directory.

### Group 2: Requires Human Intervention (Outside IOSK)
These tasks cannot be completed by an agent operating solely within the IOSK sandbox. They involve legal research, interaction with external GUIs, physical world tasks, or high-level strategic decisions.

*   **T106**: Security compliance (Requires legal research outside the scope of the codebase).
*   **T154**: Desk for Shawn (Requires purchasing physical hardware).
*   **T155**: Property database API's to look at (Requires researching and evaluating third-party services).
*   **T208**: Demo.Diametrixfs link does not automatically ask you to sign in when opening the page. (Requires debugging web server configuration, DNS, or browser behavior outside the application code).
*   **T209**: Data retention policy and SECURITY (Requires high-level business and legal decisions).
*   **T232**: Full Disk Encryption (Requires system administration on the host machines).
*   **T237**: Python console (Involves deep integration with the host system's terminal, may be complex for an agent).
*   **T240**: Sample Customers (Requires domain expertise to create realistic financial documents).
*   **T255**: Google processor migrations 9/24/25 (Requires a human to log into the Google Cloud web console and perform manual configuration changes).
*   **T264**: Data Security and privacy (Requires writing official policy documents).
*   **T265**: Data Security Brainstorm (Requires high-level strategic discussion and decision-making).

