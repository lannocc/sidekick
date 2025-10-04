# Proposal: Per-User Configurable Engagement Timing

**Status**: Proposed

### Introduction

The current IOSK `Engagement` class, which governs AI agent interaction, uses hardcoded, class-level constants for its timing parameters. This means every AI agent in the system behaves with the same cadence. While this is simple, it lacks the flexibility required for a sophisticated multi-agent environment. Different tasks and roles may benefit from different interaction speeds; for instance, a DevOps agent monitoring logs might need to be highly responsive, while a creative writing agent could be more deliberative and slower.

This proposal outlines a plan to make these timing parameters dynamic and configurable on a per-user basis. It introduces a mechanism to set and adjust an agent's responsiveness at runtime, a new timing parameter to enforce a minimum delay between responses, and new commands for monitoring and managing these settings. This change will provide administrators and users with fine-grained control over agent behavior, enabling better task-specific performance, cost management, and the creation of more diverse agent "personalities."

### Core Concepts

1.  **Dynamic Timing Parameters**: The core timing settings will be moved from class constants to per-user configuration attributes. These settings will be stored on the user's `Context` (`io`) object, allowing them to persist through `reattach` operations. The parameters are:
    *   `SECS_IDLE_BEFORE_TRIP`: Seconds of inactivity after new output before the AI is prompted.
    *   `SECS_NOISY_WAIT_REPLY`: Maximum seconds to wait after the last AI trip before prompting, even with no new output.
    *   `SECS_QUIET_IDLE_POLL`: Seconds of inactivity before polling the AI when there is no new output.
    *   **New - `MIN_RESPONSE_DELAY`**: A new parameter representing a forced delay (in seconds) *after* an AI trip completes. This can be used to throttle an agent's response rate, making it appear more thoughtful or simply to control API usage. It defaults to `0`.

2.  **System Defaults**: The current hardcoded values for the three existing parameters will become the system-wide defaults, used for any agent whose settings are not explicitly overridden.

3.  **Runtime Configuration**: The `attach` and `reattach` commands will be enhanced with options to set these timing parameters for an agent upon creation or modification. A new command, `whenami`, will allow users to view and modify their own timing settings.

4.  **Monitoring**: A new `when` command will provide a system-wide overview of all active agents, their timing configurations, and the time of their last AI interaction, offering crucial visibility into agent activity.

### Implementation Strategy

#### 1. `Context` and `Engagement` Class Modifications

*   **`src/iosk/io.py` (`Context` class):**
    *   A new attribute, `self.timing_config`, will be added. This will be a dictionary initialized with the system's default timing values. Example: `{'idle_trip': 2.3, 'noisy_wait': 13.0, 'quiet_poll': 22.0, 'min_delay': 0.0}`.
    *   This dictionary will be the single source of truth for a user's timing settings.

*   **`src/iosk/chat.py` (`Engagement` class):**
    *   The timing constants (`SECS_IDLE_BEFORE_TRIP`, etc.) will be removed.
    *   A new instance attribute, `self.last_trip`, will be added and updated whenever an AI trip is made.
    *   The `engage()` loop will be modified to read its timing parameters directly from its associated `self.io.timing_config` dictionary.
    *   After a reply is successfully received from the `trip()` function, the `engage()` loop will check `self.io.timing_config['min_delay']`. If the value is greater than zero, it will execute `await asyncio.sleep()` for that duration. This happens *before* the reply is processed, ensuring the delay is respected.

#### 2. Modified Commands: `attach` and `reattach`

These commands will be updated to accept a new set of options for configuring agent timing.

**New Options:**
*   `--idle-trip <seconds>`
*   `--noisy-wait <seconds>`
*   `--quiet-poll <seconds>`
*   `--min-delay <seconds>`

The `iocall` functions for both commands will parse these arguments. If present, they will update the corresponding key-value pairs in the target user's `io.timing_config` dictionary. This allows an administrator to tune an agent's behavior during creation or on-the-fly.

**Example:**
`$ attach google --min-delay 5 --idle-trip 10 slow-thinker`
`$ reattach turbo_bot --noisy-wait 2.5`

#### 3. New Commands: `when` and `whenami`

These commands provide the primary interface for monitoring and self-managing timing parameters.

*   **`/bin/when.py`**
    *   **Usage:** `when`
    *   **Description:** Displays a table of all active bot users, their timing parameters, and when they last interacted with their underlying AI model.
    *   **Implementation:** The `iocall` function will iterate through `io.os.users`. For each user with an active `Engagement`, it will access `user.io.timing_config` and `user.engagement.last_trip` to format and print the data.
    *   **Example Output:**
        ```
        USER          LAST_TRIP_AGO   IDLE   NOISY    POLL   DELAY
        slow-thinker  8s              10.0s  13.0s    22.0s  5.0s
        turbo_bot     1s              2.3s   2.5s     22.0s  0.0s
        ```

*   **`/bin/whenami.py`**
    *   **Usage:** `whenami [--set <key>=<value>]...`
    *   **Description:** Displays the current user's timing parameters. With the `--set` option, it allows the user to modify their own timing settings.
    *   **Implementation:**
        *   When run without arguments, it reads and displays the contents of the current user's `io.timing_config`.
        *   When run with `--set key=value`, it parses the key-value pair, validates that the key is a valid timing parameter (e.g., `idle_trip`, `min_delay`) and the value is a valid number, then updates `io.timing_config`.
    *   **Example Usage:**
        *   `$ whenami` (Displays current settings)
        *   `$ whenami --set min_delay=2.5 --set idle_trip=5` (Modifies two settings at once)

### Use Case Scenarios

1.  **Creating a "Deliberate" Agent**: An administrator needs an agent for a research task that should not respond too quickly.
    *   `$ attach google --min-delay 15 slow_researcher`
    *   The `slow_researcher` agent will now always wait at least 15 seconds after getting a result from Google before formulating its response.

2.  **Monitoring Agent Activity**: An admin wants to see which agents are active and how they are configured.
    *   `$ when`
    *   The output shows that `turbo_bot` last responded 2 seconds ago, while `slow_researcher` responded 3 minutes ago, providing a quick health check.

3.  **Self-Throttling**: An AI agent, `alpha`, determines that its current task requires less frequent interaction to save on API costs.
    *   It executes the command: `$ whenami --set quiet_poll=60`
    *   Its own timing configuration is immediately updated, and it will now only poll its underlying model every 60 seconds during idle periods.

### Benefits

*   **Fine-Grained Control**: Enables the precise tuning of agent responsiveness to match specific roles and tasks.
*   **Cost Management**: Slower polling and forced delays can directly reduce the number of API calls made, leading to significant cost savings.
*   **Behavioral Diversity**: Allows for the creation of agents with distinct "personalities" (e.g., hyper-responsive, thoughtful, periodic), making the multi-agent environment more dynamic and realistic.
*   **Improved System Management**: The `when` and `whenami` commands provide essential tools for monitoring agent status and allowing agents to self-regulate, which is a powerful step towards greater autonomy.

