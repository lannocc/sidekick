# Proposal: Full Circle - Backend-Initiated Window Management

**Author:** LANNOCC
**Date:** November 15, 2025
**Status:** Draft

## 1. Introduction & Motivation

The SKYBOARD interface provides a rich, graphical environment for interacting with the IOSK kernel. Currently, this interaction is a one-way street: the user, via the SKYBOARD frontend, initiates all actions, and the IOSK backend reactively responds to these requests. While powerful, this model limits the backend to a passive role.

This proposal, codenamed **Full Circle**, outlines a plan to "close the loop" by enabling the IOSK backend to proactively request the SKYBOARD frontend to open and manage windows. This will transform simple command-line scripts into launchers for rich GUI applications, seamlessly bridging the gap between the terminal and the graphical desktop.

The primary use cases motivating this proposal are:

1.  **GUI Application Launchers:** A user could run a command like `$ calculator` in an `IoskConsole`, and instead of seeing text output, the graphical `Calculator.svelte` application would open in a new window on their desktop.
2.  **Upgrading `watch`:** The `watch` command is an excellent monitoring tool, but its current implementation is a text-mode UI that only works for users on a local `/dev/console`. This proposal will upgrade `watch` to detect when it's being run from a SKYBOARD client. In that scenario, it will launch the dedicated `IoskWatch.svelte` GUI component, pre-configured with the command to monitor, making this powerful feature accessible to all users.

Implementing Full Circle will make the IOSK environment more dynamic, intuitive, and capable, further blurring the lines between a traditional CLI and a modern GUI.

## 2. Core Requirements

1.  **New Backend-to-Frontend Protocol:** A new message type must be added to the `SK1:` WebSocket protocol, allowing the backend to request the opening of a frontend window.
2.  **Component Specification:** The new protocol message must specify the target window component by name (e.g., `'IoskWatch'`, `'Calculator'`).
3.  **Property Passing:** The message must support passing an object of initial properties (`props`) to the new Svelte component. For `IoskWatch`, this would include `initialCommand`, `initialPwd`, and `initialInterval`.
4.  **Backend Scripting API:** A simple, high-level function must be exposed to backend scripts (e.g., `io.open_window(component_name, props)`) to abstract away the underlying WebSocket communication.
5.  **Context-Aware Commands:** Backend commands like `watch` must be updated to be context-aware, checking the user's device (`io.dev`) to decide whether to launch a GUI window or run the traditional terminal UI.

## 3. Proposed Architecture

The implementation will span both the backend kernel/scripts and the frontend Svelte application, connected by a new WebSocket message.

### 3.1. Backend (IOSK)

The core change is to provide a mechanism for scripts to send a specific message to the client they are running on.

#### 3.1.1. New WebSocket Protocol

A new server-to-client message will be defined:
`{"type": "ui_open_window", "componentName": "...", "props": {...}}`

-   `componentName`: A string matching a key in the frontend's `componentMap` (e.g., `'IoskWatch'`).
-   `props`: An object containing initial properties for the Svelte component.

#### 3.1.2. `iosk/io.py` & `iosk/port.py`

To make this accessible to scripts, we will add a helper method to the `Context` class.

1.  **`PortManager` (`port.py`):** A new method will be created to handle the raw message sending.
    ```python
    # In PortManager
    async def request_client_window_open(self, username: str, component_name: str, props: dict):
        payload = {
            "type": "ui_open_window",
            "componentName": component_name,
            "props": props
        }
        await self.send_payload_to_client(username, payload)
    ```

2.  **`Context` (`io.py`):** A user-facing method will be added. This is what scripts will call.
    ```python
    # In Context class
    async def open_window(self, component_name: str, props: dict):
        if self.dev.startswith('network:'):
            # The consoleId is crucial for context-aware windows like IoskWatch.
            # The tab's ID is stored in the io context as `self.id` (from cid).
            props_with_context = {'consoleId': self.id, **props}
            await self.os.port.request_client_window_open(self.user, component_name, props_with_context)
            return True
        return False # Not a network client, can't open a window.
    ```

#### 3.1.3. Command Script Updates

With the API in place, we can update/create the command scripts.

1.  **`iosk/bin/watch.py` (Modified):**
    The `iocall` function will be wrapped in a check for the user's device.
    ```python
    # in iosk/bin/watch.py
    async def iocall(io, argv):
        # ... argument parsing for interval, command_str, etc. ...

        if io.dev.startswith('network:'):
            # User is on SKYBOARD, request the GUI window.
            props = {
                'initialCommand': command_str,
                'initialPwd': io.pwd,
                'initialInterval': interval
            }
            await io.open_window('IoskWatch', props)
            return True # Command succeeded by launching GUI
        else:
            # User is on a local console, run the existing text-mode UI.
            # ... existing logic with clear_screen_code, asyncio.sleep, etc. ...
    ```

2.  **`iosk/bin/calculator.py` (New File):**
    This script will serve as a simple proof-of-concept.
    ```python
    # new file: iosk/bin/calculator.py
    async def iocall(io, argv):
        """Launches the graphical calculator on SKYBOARD."""
        if not await io.open_window('Calculator', {}):
            await io.error("!! calculator GUI can only be opened from a SKYBOARD client.")
            return False
        return True
    ```

### 3.2. Frontend (SKYBOARD)

The frontend needs to listen for the new message and act on it.

1.  **`sv/windows.js`:** We will add a scalable function to the window manager that can open any known component by name.
    ```javascript
    // in createWindowManager() in sv/windows.js
    const openWindowByName = (name, props = {}) => {
        const component = componentMap[name];
        if (component) {
            addWindow(component, props);
        } else {
            console.error(`Unknown component name for openWindowByName: ${name}`);
        }
    };
    // ...
    return {
        // ... existing methods
        openWindowByName,
    };
    ```

2.  **`sv/IoskConsole.svelte`:** The console component, which receives all messages for its session, will handle the new `ui_open_window` type.
    ```javascript
    // In IoskConsole.svelte <script>
    import { windows } from './windows.js';

    // ... inside the ws.onmessage handler ...
    ws.onmessage = (event) => {
        // ... existing logic ...
        const data = JSON.parse(jsonData);

        if (data.type === 'ui_open_window') {
            // Backend requested a new window.
            // The `consoleId` is automatically added by the backend's io.open_window,
            // so we can just pass the props through.
            windows.openWindowByName(data.componentName, data.props);
        } else if (data.type === 'state_info') {
            // ... etc. ...
        }
    }
    ```

This architecture is illustrated below:

```
+-----------------------------------------------------------------+
| Backend (IOSK)                                                  |
| +-------------------------+      +----------------------------+ |
| | iosk/bin/watch.py       |      | iosk/port.py               | |
| |-------------------------|      |----------------------------| |
| | if io.dev == 'network': |      | def req_client_window_open | |
| |   io.open_window(...) --|----->|   payload = {...}          | |
| | else:                   |      |   ws.send(payload) --------|-----> (WebSocket)
| |   # run terminal UI     |      |                            | |
| +-------------------------+      +----------------------------+ |
+-----------------------------------------------------------------+
                                                                     |
+-----------------------------------------------------------------+  | (SK1:{"type":"ui_open_window",...})
| Frontend (SKYBOARD)                                             |  V
| +-------------------------+      +----------------------------+ |
| | IoskConsole.svelte      |      | windows.js                 | |
| |-------------------------|      |----------------------------| |
| | on:message(data)        |      | const componentMap = {...} | |
| | if data.type == 'ui...':|      | function openWindowByName: | |
| |   windows.openByName()--|----->|   addWindow(...)           | |
| +-------------------------+      +----------------------------+ |
+-----------------------------------------------------------------+
```

## 4. Future Vision: Deeper Integration

The "Full Circle" concept can be extended far beyond simply opening windows.

-   **Backend-Defined Geometry:** The `ui_open_window` payload could be enhanced to include optional `x`, `y`, `width`, `height`, and `title` properties, allowing a backend script to suggest a specific layout for the new window.

-   **Active Window Control:** We could introduce new message types for full lifecycle management, such as `ui_close_window`, `ui_focus_window`, `ui_update_props` (e.g., to change a window's title). This would require a shared identifier; the backend could generate a `requestId` on open, which the frontend would then associate with the `groupId` it creates.

-   **Bidirectional Script-UI Communication:** For a true "full circle" feedback loop, a specific backend script instance should be able to communicate with the specific UI window it launched. This could be achieved by passing a backend Process ID (PID) to the frontend.
    1.  Backend `watch` (PID 123) sends `ui_open_window` with a `backendPid: 123` prop.
    2.  Frontend `IoskWatch` component stores this `backendPid`.
    3.  When the user clicks the "Stop" button in the UI, the frontend sends a new message back, e.g., `{"type": "ui_action", "backendPid": 123, "action": "stop"}`.
    4.  The backend `PortManager` receives this, looks up PID 123 in the process table, and cancels its `asyncio.Task`, gracefully terminating the script.

-   **Dynamic UI Generation:** For ultimate flexibility, the backend could send a declarative UI schema (e.g., a JSON object describing buttons, text fields, and labels). The frontend would then render a generic "form" or "display" window based on this schema, allowing backend scripts to create simple, custom UIs on the fly without requiring new Svelte components.

## 5. Conclusion

By enabling the backend to initiate frontend actions, the **Full Circle** proposal fundamentally enhances the interactivity and capability of the SKYBOARD environment. It provides a clean, scalable architecture for integrating command-line tools with graphical components, starting with practical upgrades to `watch` and `calculator`. This foundational work paves the way for a future of much deeper, more dynamic human-AI collaboration within the SideKick ecosystem.

