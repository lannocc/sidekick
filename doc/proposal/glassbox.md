# Proposal: GlassBox for Live Context Inspection

**Author:** LANNOCC
**Date:** November 19, 2025
**Status:** Implemented

## 1. Introduction & Motivation

The internal state of an IOSK user session, particularly for AI agents (bots), is a complex and dynamic environment. It includes the AI's chat history, its core memory banks, environment variables, command history, and more. Currently, this state is effectively a "black box" from the perspective of a SKYBOARD user. When an AI agent behaves unexpectedly, debugging the root cause requires inspecting server-side logs, which is inefficient and indirect.

This proposal, codenamed **GlassBox**, outlines a plan to create a powerful, real-time "Context Inspector" within the SKYBOARD interface. This new tool will provide a live, read-only view into the complete `Context` and `UserSessionState` of any user in a session, transforming the debugging process from guesswork into direct observation. By making the internal state transparent, we can dramatically improve our ability to understand, debug, and refine AI agent behavior.

## 2. Core Requirements

1.  **UI Integration:** A new "Context..." option will be added to the user right-click menu in the `IoskConsole`'s participant panel.
2.  **Dedicated Inspector Window:** Clicking "Context..." will open a new, dedicated window (`IoskContextInspector.svelte`) populated with the target user's context data.
3.  **Comprehensive Data Display:** The inspector must provide a structured view of key state information, including:
    *   **Session Info:** `pwd`, `env`, `aliases`, command `history`.
    *   **User Details:** `loginTime`, `isBot`, `isSuperUser`.
    *   **AI Context:**
        *   The fully rendered `preamble` output.
        *   A list of loaded memory `banks`, with the ability to view the content of each.
        *   A detailed, entry-by-entry view of the `sessionHistory`.
        *   The fully rendered `postamble` output.
    *   **Telemetry:** The user's complete `tokenStats` record.
4.  **Live Updates:** The inspector window must automatically update its display in real-time as the target user's context changes (e.g., after they run a command).
5.  **Efficient Subscription Model:** The backend should only send context updates for a user if a client is actively inspecting them, avoiding unnecessary network traffic.

## 3. Proposed Architecture

The implementation will be based on a new subscription-based WebSocket protocol, allowing the frontend to register interest in a user's context and for the backend to push updates efficiently.

### 3.1. Backend (IOSK)

The backend will be responsible for serializing context data and managing update subscriptions.

#### 3.1.1. New WebSocket Protocol

Two new client-to-server messages will manage subscriptions:
*   `{"type": "ui_context_subscribe", "targetUser": "user.host"}`
*   `{"type": "ui_context_unsubscribe", "targetUser": "user.host"}`

One new server-to-client message will push data:
*   `{"type": "context_update", "targetUser": "user.host", "data": {...}}`

The `data` payload will be a JSON object containing the serialized context.

#### 3.1.2. `iosk/port.py` (PortManager)

`PortManager` will manage the subscription lifecycle.

1.  **Subscription State:** A new instance variable will be added:
    ```python
    self.context_subscriptions: Dict[str, set] = {} # Maps targetUser -> {ws1, ws2, ...}
    ```
2.  **Subscription Handlers:** New handlers in `iosk/web.py` will manage the subscription dictionary:
    *   `handle_ui_context_subscribe`: Adds the client's websocket to the set for the `targetUser`. Immediately after subscribing, it will trigger an initial `broadcast_context_update` for that user to populate the new inspector window.
    *   `handle_ui_context_unsubscribe`: Removes the websocket from the set.
3.  **New Broadcaster Method:** A new method in `PortManager` will be the entry point for sending updates.
    ```python
    # in PortManager
    async def broadcast_context_update(self, target_user_io: Context):
        target_user_addr = f"{target_user_io.session.user}.{self.os.hostname}"
        if target_user_addr not in self.context_subscriptions:
            return
    
        # Serialize the context data
        context_data = serialize_context_for_frontend(target_user_io)
        payload = {
            "type": "context_update",
            "targetUser": target_user_addr,
            "data": context_data
        }
    
        # Send the update to all subscribed clients
        subscribers = self.context_subscriptions.get(target_user_addr, set())
        for ws in list(subscribers): # Use list() for safe iteration
            if ws.open:
                await self.send_payload_to_client(ws.id, payload) # Assumes ws has a user/id mapping
            else:
                subscribers.remove(ws) # Clean up dead connection
    ```
    *(Note: `send_payload_to_client` will need a way to look up a user by websocket, which is already part of its connection metadata).*

#### 3.1.3. `iosk/io.py`

A new helper function will be created to perform the serialization. This isolates the complex data gathering logic.

```python
# within io.py
def serialize_context_for_frontend(io: Context) -> dict:
    session = io.session
    return {
        "user": session.user,
        "loginTime": session.login_time.isoformat() if session.login_time else None,
        "isBot": session.bot,
        "isSuperUser": session.su,
        "pwd": io.pwd,
        "env": io.environ(),
        "aliases": session.aliases,
        "commandHistory": session.history,
        "tokenStats": session.token_stats,
        "aiContext": {
            "preamble": session.preamble_cache or "",
            # Assuming postamble is not persistently stored, this would be tricky.
            # For now, we can omit it or find a way to cache the last one.
            "banks": [{"name": k, "content": v} for k, v in session.banks.items()],
            "sessionHistory": [
                {"number": entry.number, "content": entry.content}
                for entry in session.session_history
            ]
        }
    }
```

#### 3.1.4. `iosk/proc.py` (ProcessManager)

The command execution loop is the perfect place to hook into state changes. The `call` method (or its delegate in `pipeline.py`) will be modified.

```python
# in ProcessManager.call() or PipelineExecutor.execute_pipeline()
async def execute_pipeline(self, io: Context, ...):
    # ... existing pipeline execution logic ...
    success = ...

    # --- GlassBox Hook ---
    # After any command finishes, check for subscribers and broadcast the new state.
    if self.os.port:
        await self.os.port.broadcast_context_update(io)
    # --- End Hook ---

    return success
```

### 3.2. Frontend (SKYBOARD)

The frontend will manage the inspector window's lifecycle and data display.

1.  **`sv/ioskEvents.js`:** A new store will be created to decouple the console from the inspector.
    ```javascript
    // in sv/ioskEvents.js
    export const contextUpdates = writable(null);
    ```

2.  **`sv/IoskConsole.svelte`:**
    *   **Menu:** The user right-click menu (`.user-context-menu`) will be updated:
      ```html
      <button class="menu-item" on:click={viewUserLog}> View Log... </button>
      <button class="menu-item" on:click={() => inspectUserContext(userContextMenu.user)}> Context... </button>
      ```
    *   **Logic:** A new `inspectUserContext` function will open the window and send the subscription message.
      ```javascript
      // in IoskConsole.svelte <script>
      import { newIoskContextInspector } from './windows.js';
      
      function inspectUserContext(targetUser) {
          // Open the new window component
          newIoskContextInspector(id, targetUser);
      
          // Subscribe to updates
          if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ui_context_subscribe', targetUser }));
          }
          closeUserContextMenu();
      }
      ```
    *   **Message Handling:** The `onmessage` handler will pipe `context_update` messages to the new store.
      ```javascript
      // in IoskConsole.svelte ws.onmessage
      if (data.type === 'context_update') {
          contextUpdates.set(data);
      } else if (...) {
          // ... other message types
      }
      ```

3.  **`sv/IoskContextInspector.svelte` (New Component):**
    *   This component will be responsible for rendering the context data.
    *   It will manage its own unsubscription on destruction.
    ```svelte
    <script>
        import { onMount, onDestroy } from 'svelte';
        import { contextUpdates } from './ioskEvents.js';
    
        export let targetUser; // Prop passed when window is created
        export let consoleWs; // Reference to the console's WebSocket for unsubscribing
    
        let contextData = null;
    
        const unsubscribeStore = contextUpdates.subscribe(update => {
            if (update && update.targetUser === targetUser) {
                contextData = update.data;
            }
        });
    
        onDestroy(() => {
            // Unsubscribe from the Svelte store
            unsubscribeStore();
    
            // Unsubscribe from backend updates
            if (consoleWs && consoleWs.readyState === WebSocket.OPEN) {
                consoleWs.send(JSON.stringify({ type: 'ui_context_unsubscribe', targetUser }));
            }
        });
    </script>
    
    <div class="inspector-container">
        {#if contextData}
            <!-- UI with tabs/sections for pwd, env, aliases, AI context, etc. -->
            <h1>Context for {contextData.user}</h1>
            <pre>{JSON.stringify(contextData, null, 2)}</pre>
        {:else}
            <p>Waiting for context data for {targetUser}...</p>
        {/if}
    </div>
    ```
    *(Note: The actual UI would be more sophisticated than a JSON dump, using tabs and collapsible sections.)*

## 4. Conclusion

The **GlassBox** proposal provides a clean and powerful architecture for gaining real-time insight into a user's session state. By implementing a simple subscription protocol, a dedicated serializer, and a new inspector component, we can create an invaluable debugging and analysis tool. This feature will demystify the internal workings of our AI agents, making the entire IOSK environment more transparent, predictable, and easier to manage for developers and administrators alike.

