# Proposal: Advanced Session History Management

**Status**: Implemented

### Introduction

Currently, an IOSK user's session history is managed as a simple, monolithic stream of text in an `io.StringIO` buffer. While functional for basic logging and providing context to AI agents, this approach has significant limitations. The history grows indefinitely, leading to excessive token consumption in long-running sessions. Furthermore, there is no mechanism to selectively edit or remove parts of the history, making it difficult to correct mistakes, remove sensitive information, or fine-tune an AI's context.

This proposal introduces a robust, structured session history system. By representing history as a sequence of discrete, numbered entries rather than a flat text stream, we can introduce powerful new features for managing an agent's context and improving the user experience. This includes a `forget` command for selectively removing history entries and a configurable `rolling` cutoff mechanism to automatically manage context size. These changes will give users and administrators precise control over session history, leading to better performance, lower operational costs, and more effective human-agent and agent-agent interactions.

### Core Concepts

1.  **Structured History Entries**: The core of this proposal is to replace the `StringIO` session buffer with a list of structured objects (`HistoryEntry`). Each object will represent a distinct event in the session, such as a user command and its output, a chat message, or a system notification. Each entry will be decorated with metadata, including a unique, sequential prompt number. This structure is the key enabler for all other features.

2.  **Chronological Prompt Numbering**: Each user's session will maintain a prompt counter, starting at 1. This number will be assigned to each new history entry and will be displayed as part of the user's command-line prompt (e.g., `[user@host / 1]$`). This provides a clear, user-facing reference for every event in their session, which is essential for the `forget` command. The `reset` command will clear the history and reset this counter.

3.  **Selective Forgetting**: A new command, `forget`, will be introduced to provide fine-grained control over the session history. Users will be able to remove specific entries by their prompt number. The command will support removing single entries, multiple entries, and contiguous ranges. This allows users to surgically remove mistakes, irrelevant information, or confidential data from an AI's context without resetting the entire session.

4.  **Configurable Rolling Cutoff**: To manage the context length of long-running sessions automatically, a per-user, configurable rolling cutoff will be implemented. When enabled, the system will automatically prune the oldest history entries whenever a new entry is added that pushes the history over a defined limit. This limit can be configured based on several metrics:
    *   Total token count
    *   Total byte count
    *   Total line count
    *   Total prompt (entry) count

5.  **Dynamic Token Recalculation**: Any operation that modifies the history—`reset`, `forget`, or the rolling cutoff—will trigger an immediate and accurate recalculation of the user's context token counts. This ensures that the system's understanding of context size is always up-to-date, which is critical for managing AI interactions and costs.

### Implementation Strategy

#### 1. `Context` Class Modifications (`src/iosk/io.py`)

The `Context` class will be significantly updated to manage the new structured history.

*   **State Attributes**:
    *   `self.session = StringIO()` will be removed.
    *   `self.session_history = []` will be added to store a list of `HistoryEntry` objects.
    *   `self.prompt_number = 1` will be added to track the current prompt number.
    *   `self.rolling_config = {'enabled': False, 'mode': None, 'limit': 0}` will store the user's rolling cutoff settings.

*   **New `HistoryEntry` Class (conceptual):**
    A simple data class will be defined to hold history information.
    ```python
    class HistoryEntry:
        def __init__(self, number, content_str, token_count, byte_count, line_count):
            self.number = number
            self.content = content_str
            self.tokens = token_count
            # ... other metadata
    ```

*   **Method Rework**:
    *   A new method, `add_history_entry(content: str)`, will be created. This method will be the sole entry point for adding to the history. It will create a `HistoryEntry`, calculate its metadata (tokens, bytes, etc.), append it to `self.session_history`, increment `self.prompt_number`, and then trigger `_apply_rolling_cutoff()`.
    *   `_apply_rolling_cutoff()`: A new private method that checks if the rolling cutoff is enabled and, if the history exceeds the configured limit, removes the oldest entries until the history is within bounds. It will then trigger a token recalculation.
    *   `get_session_string() -> str`: This method will iterate over `self.session_history` and concatenate the content of each entry to produce the flat string required by the AI `Engagement` logic.
    *   The existing `print()`, `input()`, and `error()` methods will be refactored. Instead of writing directly to a buffer, command execution logic will capture all output for a given command and then call `add_history_entry()` once with the complete text block.

#### 2. Kernel and Chat Modifications (`kernel.py`, `chat.py`)

*   **`kernel.py` (`IOSK.interactive`):** The prompt construction will be updated to include the prompt number from `io.prompt_number`.
    *   `prompt_str = f'[{io.user} {io.pwd} {io.prompt_number}] {prompt_char} '`

*   **`kernel.py` (`CommandPipelineExecutor`):** This is the ideal place to manage history entry creation for commands. Before executing a pipeline, it will start capturing output. After the pipeline completes, it will take the captured output, prepend the user's input command, and call `io.add_history_entry()` with the resulting block of text.

*   **`chat.py` (`Engagement.engage`):** The logic that builds the prompt for an AI trip will be modified.
    *   `prompt = self.io.session.read()` will be replaced with `prompt = self.io.get_session_string()`. This ensures the AI always gets a coherent history based on the current state of `session_history`.

#### 3. Command Updates and Additions

*   **`bin/reset.py`**:
    *   This command will be updated to clear `target_io.session_history`, reset `target_io.prompt_number = 1`, and clear the `rolling_config`. It will also trigger a full recalculation of token counts.

*   **New Command: `/bin/forget.py`**:
    *   **Usage:** `forget <id> | <id>-<id> | -<id> | <id>- ...`
    *   **Description:** Removes entries from the session history by prompt number.
    *   **Implementation:** The `iocall` will parse the arguments to build a set of prompt numbers to remove. It will then filter `io.session_history`, removing the matching entries. Finally, it will call a method on `io` to recalculate context tokens and print a confirmation to the user.

*   **New Command: `/bin/rolling.py`**:
    *   **Usage:**
        *   `rolling`: Displays the current rolling cutoff configuration.
        *   `rolling on|off`: Enables or disables the feature.
        *   `rolling --<mode> <limit>`: Sets the cutoff mode and limit.
    *   **Modes:** `--bytes`, `--tokens`, `--prompts`, `--lines`.
    *   **Implementation:** The `iocall` will parse arguments and read from or write to the `io.rolling_config` dictionary.

### Use Case Scenarios

**1. Correcting AI Context**
An agent is stuck in a repetitive loop based on a user's poorly phrased prompt (prompt #15) and its own flawed response (prompt #16).
```
[user@host / 17]$ forget 15-16
:: 2 entries forgotten. Context is now 1520 tokens.
[user@host / 17]$ # User re-phrases the prompt
```
The agent now receives a clean context without the confusing exchange.

**2. Managing a Long-Running Monitoring Agent**
An agent, `log-watcher`, has been running for days, and its context has grown to 30,000 tokens, making API calls slow and expensive.
```
[admin@host / 5]$ reattach log-watcher
[admin@host / 6]$ rolling on --tokens 8000
:: Rolling history enabled. Cutoff at 8000 tokens.
```
From now on, the `log-watcher` agent's history will be automatically pruned, keeping its context window to a manageable size. The oldest entries are dropped as new ones are added.

**3. Starting Fresh**
A user's session state has become confusing.
```
[user@host / 123]$ reset
:: resetting session for user 'user'...
:: session for user 'user' has been reset.
[user@host / 1]$ # The prompt number is reset to 1
```

### Benefits

*   **Precise Context Management**: Gives users and agents the power to surgically edit AI context, leading to more accurate and efficient interactions.
*   **Cost and Performance Optimization**: The rolling cutoff feature prevents unbounded growth of session history, reducing API token costs and improving AI response times for long-running agents.
*   **Enhanced Usability**: Numbered prompts and the `forget` command create a more forgiving and intuitive command-line experience.
*   **Robust Foundation**: A structured history log is a prerequisite for future features, such as session summarization, history search, and more advanced context management strategies.

