# Proposal: Real-Time Token Telemetry for SKYBOARD

**Author:** LANNOCC
**Date:** November 18, 2025
**Status:** Draft

## 1. Introduction & Motivation

As IOSK evolves into a powerful multi-agent environment, the ability to monitor the resource consumption of automated "bot" users becomes critical. Currently, calculating the token usage of a bot's session requires running the `tokens` command manually, which provides only a point-in-time snapshot. There is no persistent, real-time visibility into an agent's activity or its associated costs.

This proposal outlines a plan to integrate real-time token telemetry directly into the SKYBOARD interface. By pushing token and byte count statistics from the backend after every AI interaction, we can provide operators with immediate, at-a-glance insight into bot performance and resource usage. This will transform the `IoskConsole`'s user list from a simple presence indicator into a lightweight agent monitoring dashboard, essential for debugging, cost management, and understanding agent behavior.

## 2. Core Requirements

1.  **At-a-Glance Totals:** In the `IoskConsole` "Users" panel, any user identified as a bot must display its total cumulative *input* tokens. This value should be abbreviated for readability (e.g., `11.2k`, `1.17m`) and be visible on the right-hand side of the user's name.
2.  **Detailed Tooltip:** Mousing over the abbreviated token count must reveal a detailed tooltip containing a breakdown of key metrics:
    *   Cumulative Input (Bytes / Tokens)
    *   Cumulative Output (Bytes / Tokens)
    *   Last Trip Input (Bytes / Tokens)
    *   Last Trip Output (Bytes / Tokens)
    *   Current Banked Memory (Bytes / Tokens)
    *   Current Chat History (Bytes / Tokens)
    *   Current Caching Context (Preamble + Banked + History) (Bytes / Tokens)
3.  **Real-Time Updates:** All displayed token statistics must update automatically and immediately after a bot completes an AI interaction ("trip").
4.  **Backend State Tracking:** The IOSK kernel must be enhanced to persistently track these token metrics for each user session.

## 3. Proposed Architecture

The implementation will require coordinated changes across the backend state management, the kernel's AI interaction logic, the WebSocket protocol, and the frontend UI components.

### 3.1. Backend (IOSK)

The backend is responsible for tracking, calculating, and pushing the token data.

#### 3.1.1. `Context` State Expansion (`iosk/io.py`)

The `Context` class, which represents a user's session state, will be expanded to store the necessary telemetry data. New attributes will be added to `Context.__init__`:

```python
# In Context class in iosk/io.py
self.token_stats = {
    'cumulative_input_tokens': 0, 'cumulative_input_bytes': 0,
    'cumulative_output_tokens': 0, 'cumulative_output_bytes': 0,
    'last_trip_input_tokens': 0, 'last_trip_input_bytes': 0,
    'last_trip_output_tokens': 0, 'last_trip_output_bytes': 0,
    'banked_tokens': 0, 'banked_bytes': 0,
    'history_tokens': 0, 'history_bytes': 0,
    'caching_context_tokens': 0, 'caching_context_bytes': 0
}
```
This dictionary structure keeps the telemetry data organized and easy to serialize.

#### 3.1.2. Kernel-Side Calculation (`iosk/kernel.py`)

The kernel's `log_trip_trace` function is the ideal location to perform these calculations, as it is already invoked after every AI trip and has access to the prompt and reply.

1.  **Update on Trip Completion:** `log_trip_trace` will be modified to update the `io.token_stats` dictionary on the user's `Context` object after calculating prompt and reply tokens.
    *   It will update `last_trip_*` values with the new counts.
    *   It will increment `cumulative_*` values.

2.  **Pre-Trip Context Calculation:** To calculate the `banked`, `history`, and `caching` context sizes, the logic currently within `iosk/bin/tokens.py` will be extracted into a new, reusable helper method within the `IOSK` kernel class (e.g., `_calculate_context_tokens(self, io)`). This method will be called by `log_trip_trace` *before* the main trip stats are calculated to capture the state of the context that was just used.

3.  **Broadcasting Updates:** After updating the stats, `log_trip_trace` will trigger a broadcast to the frontend.
    ```python
    # In IOSK.log_trip_trace in kernel.py, after updating io.token_stats
    if io.bot and self.port:
        await self.port.broadcast_token_stats_update(io)
    ```

#### 3.1.3. New WebSocket Protocol (`iosk/port.py`)

A new message type and a corresponding broadcast method will be added to `PortManager`.

*   **New Message Type:** `token_stats_update`
    *   **Payload:** `{"type": "token_stats_update", "user": "bot@host", "stats": {...}}`
    *   The payload will contain the full `token_stats` dictionary for a single user, ensuring updates are granular and efficient.

*   **New `PortManager` Method:**
    ```python
    # In PortManager class in port.py
    async def broadcast_token_stats_update(self, user_io: "Context"):
        if not user_io.bot: return
        payload = {
            "type": "token_stats_update",
            "user": f"{user_io.user}.{self.kernel.hostname}",
            "stats": user_io.token_stats
        }
        await self.broadcast_to_clients(payload)
    ```

*   **Identifying Bots:** To enable the frontend to distinguish bots, the `user_update` message broadcast on login will be augmented with an `is_bot` flag, sourced from the `io.bot` attribute. This state will be managed in `kernel.network_users` and propagated to clients via the main `state_info` message.

### 3.2. Frontend (SKYBOARD)

The `IoskConsole` component will be updated to receive, store, and display the new telemetry data.

#### 3.2.1. State Management (`IoskConsole.svelte`)

*   A new state variable will be introduced: `let userTokenStats = {};`
*   The WebSocket `onmessage` handler will be updated to process the `token_stats_update` message, updating the `userTokenStats` object with the new data keyed by the user's address.
    ```javascript
    // In ws.onmessage
    } else if (data.type === 'token_stats_update') {
        userTokenStats[data.user] = data.stats;
        userTokenStats = userTokenStats; // Trigger reactivity
    }
    ```
*   The `room_state_update` handler will process the new `is_bot` flag for each participant.

#### 3.2.2. UI Rendering (`IoskConsole.svelte`)

The user list rendering logic will be updated to display the telemetry. A helper function will be created for number abbreviation.

```javascript
function abbreviateNumber(num) {
    if (num < 1000) return num.toString();
    const suffixes = ["", "k", "m", "b", "t"];
    const i = Math.floor(Math.log10(num) / 3);
    const short = (num / Math.pow(1000, i)).toFixed(i > 0 ? 2 : 0);
    return short + suffixes[i];
}
```

A UI mockup of the proposed change in the "Users" panel:

```
+-------------------------------------------------------------+
| IoskConsole.svelte Users Panel                              |
+-------------------------------------------------------------+
| 👤 Users                      [Attach]                      |
| ----------------------------------------------------------- |
| root                                                        |
| agent-alpha ............................ 1.17m <------------|-- Abbreviated cumulative input tokens
|                                           ^                 |
|                                           | Mouse Hover     |
| +---------------------------------------------------------+ |
| | Cumulative Input: 1,172,403 tokens (4.92 MB)            | |
| | Cumulative Output: 88,194 tokens (352.78 KB)            | |
| | Last Trip Input: 4,096 tokens (16.38 KB)                | |
| | Last Trip Output: 251 tokens (1.00 KB)                  | |
| | Banked Memory: 8,192 tokens (32.77 KB)                  | |
| | Chat History: 31,445 tokens (125.78 KB)                 | |
| | Caching Context: 40,011 tokens (160.04 KB)              | |
| +---------------------------------------------------------+ |
| my-other-agent ......................... 11.2k              |
+-------------------------------------------------------------+
```

This will be implemented using a container element with `position: relative;` and an absolutely positioned child `div` for the tooltip, toggled with `on:mouseenter` and `on:mouseleave` events.

## 4. Data Flow

The real-time update sequence will be as follows:

1.  **AI Trip:** A bot user's code (e.g., in `/dev/google`) sends a prompt to an AI.
2.  **Response:** The AI streams back a response.
3.  **Kernel Hook:** `IOSK.log_trip_trace` is called with the final prompt and reply.
4.  **State Update:** `log_trip_trace` calculates all token/byte metrics and updates the bot's `io.token_stats` dictionary.
5.  **Broadcast:** The kernel calls `PortManager.broadcast_token_stats_update(io)`.
6.  **WebSocket Push:** `PortManager` sends a `token_stats_update` message to all connected SKYBOARD clients.
7.  **Frontend Reception:** The `IoskConsole`'s `onmessage` handler receives the message.
8.  **UI Update:** The Svelte component updates its local `userTokenStats` state, causing the UI to reactively re-render with the new numbers.

## 5. Conclusion

By implementing real-time token telemetry, we elevate SKYBOARD from a simple interactive client to a sophisticated monitoring tool for AI agent development. This feature provides essential, immediate feedback on agent resource consumption, which is fundamental for managing costs, optimizing performance, and debugging complex agent behaviors. This proposal provides a clear and robust architecture for delivering this critical functionality.

