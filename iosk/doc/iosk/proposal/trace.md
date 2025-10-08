# Proposal: A System-Wide Tracing Facility

**Status**: Implemented

### Introduction

As IOSK evolves into a more complex multi-agent environment, the need for deep visibility into its internal operations becomes critical. Debugging AI interactions, understanding command pipeline failures, or auditing filesystem access is currently a manual and often difficult process. To address this, we propose the implementation of a flexible, system-wide tracing facility.

This system will introduce a new `trace` command to selectively enable or disable logging for specific, named "trace points" within the kernel and its subsystems. The initial and most critical trace point will be `trip`, designed to capture the exact prompts sent to and replies received from AI models. This will provide an invaluable, unobtrusive tool for developers and administrators to debug agent behavior, analyze performance, and ensure the system is operating as intended, laying a foundation for a more observable and manageable OS.

### Core Concepts

1.  **Trace Points**: These are named hooks embedded at key locations in the IOSK codebase. Each trace point corresponds to a specific system activity that can be logged when enabled (e.g., `trip`, `parser`).
2.  **Trace State Management**: The kernel will maintain the state (on/off) for each trace point. A global toggle will also be available to enable or disable all tracing simultaneously, providing a quick way to switch between normal and diagnostic modes.
3.  **Dedicated Trace Logs**: Each trace point will log its output to a designated subdirectory within `/var/log/`. This separation keeps trace data organized and prevents it from cluttering the main system or user logs.

### The `trace` Command

A new command, `/bin/trace.py`, will be the user interface for managing the tracing system.

**Usage:**

*   `trace`: Displays a list of all available trace points and their current state (ON/OFF).
*   `trace on|off`: Enables or disables all trace points globally.
*   `trace <name> on|off`: Enables or disables a single, specific trace point by its name.
*   `trace --help`: Displays the help message for the command.

**Example Session:**
```
$ trace
Global trace: OFF
  trip: OFF

$ trace trip on
:: Trace 'trip' set to ON

$ trace
Global trace: OFF
  trip: ON

$ trace off
:: Global trace set to OFF
```

### Initial Trace Implementation: `trip`

The first trace point to be implemented will be `trip`, which is essential for debugging AI agent interactions.

*   **Purpose**: To log the complete, fully-constructed prompt text sent to an AI model's API and the complete, raw reply text received in return.
*   **Trigger Points**: The trace will be written immediately after an AI `trip` (e.g., to Google, OpenAI) completes. This will be instrumented in `src/iosk/chat.py` for interactive sessions and in `bin/ask.py` for one-shot queries.
*   **Log Location**: All `trip` trace files will be stored in `/var/log/trip/`.
*   **Log Filename Format**: To ensure uniqueness and provide rich context, filenames will follow the format: `device-username-boot-cid-tid`.
    *   `device`: The sanitized name of the device making the call (e.g., `google-gemini-2.5-pro`, `openai-gpt-4o`).
    *   `username`: The user whose context is being used for the trip (e.g., `alpha`).
    *   `boot`: The current system boot number (`io.os.BOOT`).
    *   `cid`: The unique context ID of the session (`io.cid`).
    *   `tid`: A per-device trip ID. This is a counter that starts at 1 each boot and increments for every trip made by a specific device path (e.g., `/dev/google/gemini-2.5-pro` has its own counter).
    *   **Extension**: For each trip, two files will be created: one ending in `.prompt` for the sent request, and one ending in `.reply` for the received response.

*   **Log File Content**:
    *   The file ending in `.prompt` will contain only the raw prompt string sent to the AI.
    *   The file ending in `.reply` will contain only the raw reply string received from the AI.
    *   No additional text (like "--- PROMPT ---") will be included in these files.

### Implementation Strategy

#### 1. Kernel Modifications (`src/iosk/kernel.py`)

*   **New Attributes in `IOSK.__init__`**:
    *   `self.trace_states`: A dictionary to hold the state of all traces. Initialized to `{'_global_': False, 'trip': False}`.
    *   `self.device_trip_counters`: An empty dictionary `{}` to store the incrementing trip IDs for each device path.

*   **Directory Creation in `IOSK.start`**:
    *   Add logic to create the `/var/log/trip` directory if it does not already exist.

*   **New Helper Methods in `IOSK`**:
    *   `async def is_trace_active(self, trace_name: str) -> bool`: Checks if a specific trace is active. It should return `True` if `self.trace_states['_global_']` is `True` or if `self.trace_states.get(trace_name)` is `True`.
    *   `async def log_trip_trace(self, io: Context, prompt: str, reply: str)`: This method will contain all the logic for the `trip` trace. It will:
        1.  Check if the `trip` trace is active using `is_trace_active`.
        2.  Get and increment the `tid` for the `io.dev` from `self.device_trip_counters`.
        3.  Construct the base unique log filename (e.g., `device-username-boot-cid-tid`).
        4.  Write the `prompt` to `base_filename.prompt` in `/var/log/trip/`.
        5.  Write the `reply` to `base_filename.reply` in `/var/log/trip/`.

#### 2. Instrumentation of AI Trip Points

*   **`src/iosk/chat.py` (`Engagement.engage`)**:
    *   After a reply is received from `reply = await self.trip(client, prompt_text_for_trip)`, a call will be made to log the trace: `await self.io.os.log_trip_trace(self.io, prompt_text_for_trip, reply or "")`.

*   **`bin/ask.py` (`iocall`)**:
    *   Similarly, after `response = await google_trip(...)`, a call will be made: `await io.os.log_trip_trace(io, full_prompt, response or "")`.

#### 3. New Command Implementation (`/bin/trace.py`)

*   Create the file `/bin/trace.py`. Its `iocall` function will:
    1.  Access `io.os.trace_states` to read and write trace states.
    2.  If no arguments are given, iterate through the dictionary and print the current status of all traces.
    3.  If one argument (`on` or `off`) is given, set the `_global_` key.
    4.  If two arguments (`<name> on|off`) are given, validate the trace name and set its state in the dictionary.
    5.  Provide appropriate user feedback and error handling.

### Future Trace Points

The proposed framework is highly extensible. Once in place, new trace points can be added with minimal effort. Potential future traces include:

*   **`parser`**: Log the input string and the final `argv` list from `CommandLineParser.parse_and_tokenize` to debug complex command parsing. Logs would go to `/var/log/parser/`.
*   **`fs`**: Log all filesystem operations (`get`, `create`, `rm`, `copy`, `move`) showing the user, command, path(s), and success/failure status. Logs would go to `/var/log/fs/`.
*   **`exec`**: Log every command execution (`call`/`exec`), including the full `argv` and the user who ran it. Logs would go to `/var/log/exec/`.

### Benefits

*   **Deep Debugging**: Provides an unparalleled ability to inspect the exact data being processed at critical points in the system, especially for "black box" AI interactions.
*   **AI Auditing**: Creates a permanent, detailed record of all agent conversations, which is crucial for quality assurance, security analysis, and understanding agent decision-making.
*   **Performance Analysis**: Can be extended to log timing information, helping to identify bottlenecks in command execution or API response times.
*   **Improved Stability**: A more observable system is an easier system to maintain and stabilize.

