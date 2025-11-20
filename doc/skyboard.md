# SKYBOARD Frontend Documentation

**Date:** 11/20/2025

## 1. Overview

**SideKick SKYBOARD** is a sophisticated, web-based desktop environment designed to provide a rich, multi-window user interface for interacting with both remote **IOSK** (Input/Output Support Kernel) backends and a local machine backend. It emulates a traditional desktop experience within a web browser, complete with a taskbar, draggable and resizable windows, application launching, and workspace management.

### 1.1. Core Features

- **Multi-Window Desktop Environment**: A fully-featured desktop with draggable, resizable, minimizable, and maximizable windows.
- **Tabbed Windows**: Windows can contain multiple tabs, which can be reordered, closed, or detached into new windows.
- **Workspace Management (Dash)**: Save and restore entire window layouts, including positions, sizes, and application-specific states (e.g., connection details, current paths).
- **Remote (IOSK) Interaction**: A suite of applications for interacting with the IOSK backend, including a powerful console, file explorer, file viewer, private chat, and an AI context inspector.
- **Local Backend Interaction**: Seamless integration with a local backend service (`sk local`) for terminal access, local file browsing, and running powerful AI-driven commands via the `Ask` application.
- **Persistent Settings**: User preferences for desktop appearance, sounds, and application defaults are saved to the browser's `localStorage`.
- **Keyboard-Driven Workflow**: Extensive keyboard shortcuts for window cycling, tab switching, and launching the Dash.

## 2. Architecture & Design Philosophy

SKYBOARD is built with **Svelte 5** and **Vite**, emphasizing a reactive, component-based architecture. The design prioritizes modularity, decoupling, and efficient state management to handle the complexity of a multi-window environment.

### 2.1. Technology Stack

- **Framework**: Svelte 5
- **Build Tool**: Vite
- **Styling**: Standard CSS with CSS Variables for theming.
- **Key Libraries**:
    - **`@xterm/xterm`**: For the `LocalTerminal` component, providing a full-featured terminal emulator.
    - **`marked` & `highlight.js`**: For rendering Markdown and syntax-highlighted code in the `IoskFileViewer`.

### 2.2. State Management

State is managed through a combination of Svelte stores, creating a clear and maintainable system.

#### 2.2.1. `desktopStore.js`: Global & Persistent State

This store manages settings that affect the entire application and are persisted in `localStorage`.
- `desktopSettings`: Controls the desktop's appearance (background, colors), behavior (focus-follows-mouse), and global defaults (chime sounds).
- `windowSettings`: Stores default settings for individual window types, such as initial URL for the browser or default position/size.
- `dashActive`: A boolean store that toggles the visibility of the Dash workspace manager.
- `dashLayouts`: An array of saved window layouts.
- `dashCycleIndex`: Tracks the currently previewed layout when cycling with keyboard shortcuts.

#### 2.2.2. `windows.js`: The Window Manager Core

This is the heart of the desktop environment. It exports a custom Svelte store (`windows`) that manages the state of all open windows.
- **Window Group Structure**: The store contains an array of "window group" objects. Each object represents a single window on the screen and contains:
    - Positional properties: `x`, `y`, `width`, `height`, `zIndex`.
    - State properties: `minimized`, `maximized`, `isActive`.
    - An array of `tabs`.
    - `activeTabId`: The ID of the currently visible tab.
- **Tab Structure**: Each tab object within a group represents a single application instance and contains:
    - A unique `id`.
    - `component`: The Svelte component to render (e.g., `IoskConsole`).
    - `componentName`: A string identifier for the component type, used for persistence.
    - Application-specific props (e.g., `title`, `path`, `wsUrl`).
- **Manager Functions**: The module exposes a rich API for manipulating windows and tabs, such as `addWindow`, `removeTab`, `focusWindow`, `toggleMaximize`, `groupWindows`, `detachTabToNewWindow`, and `restoreWindow`.

#### 2.2.3. Event Buses for Decoupled Communication

To avoid tight coupling between components (e.g., a file explorer needing a direct reference to a console), SKYBOARD uses Svelte stores as event buses.

- **`ioskEvents.js`**: Manages communication between components interacting with the *same* IOSK console instance.
    - `fileSystemRequests`: A component (like `IoskFileExplorer`) writes a request here.
    - `fileSystemResponses`: The `IoskConsole` writes the backend's response here, which the original requester listens to.
    - This pattern is used for `privateMessages`, `consoleCommands`, `contextUpdates`, etc.

- **`localBackendStore.js`**: Manages the single WebSocket connection to the local backend.
    - It abstracts connection logic (`connect`, `sendMessage`).
    - It multiplexes incoming messages from the WebSocket into dedicated, reactive stores (`terminalData`, `askOutput`, `fsListResponse`, etc.), which the relevant components can subscribe to.

### 2.3. Rendering Strategy

The `Desktop.svelte` component uses an efficient two-layer rendering strategy to maintain performance.

1.  **Windows Layer (`Window.svelte`)**: This layer iterates through the `$windows` store and renders a `Window.svelte` component for each window group. This component is responsible *only for the window chrome*: the title bar, frame, resize handles, and tabs. It handles dragging, resizing, and other frame-level interactions.

2.  **Tab Contents Layer**: This layer iterates through *all tabs of all windows* but only renders the component for the *active tab of a non-minimized window*. The content is absolutely positioned to perfectly overlay its corresponding window frame.

This ensures that even with dozens of windows and tabs open, only the components for the currently visible tabs are mounted and active in the DOM, preserving resources and keeping the UI responsive.

## 3. Component Breakdown

The application is composed of several key components located in the `sv/` directory.

### 3.1. Core Desktop Shell

- **`SideKick.svelte`**: The root Svelte component. It lays out the `Taskbar` and `Desktop` and sets up global keyboard shortcuts.
- **`Desktop.svelte`**: The main workspace area. It renders the desktop background, manages the desktop context menu (Settings), and implements the two-layer rendering of windows and their contents. It also handles the "focus-follows-mouse" feature and the Alt+Drag/Resize shortcuts.
- **`Taskbar.svelte`**: The bar at the top of the screen. It provides:
    - A "Dash" button to open the workspace manager.
    - A "Windows" menu to list and focus open windows.
    - A dynamic area for taskbar buttons representing each open window group. The layout logic cleverly positions buttons based on their window's screen position.
    - A central analog `Clock`.
    - A "SKY" start menu for launching new applications.
- **`Window.svelte`**: The generic window container. Its responsibilities include:
    - Rendering the title bar with controls (close, minimize, maximize, options).
    - Handling window dragging and resizing.
    - Managing and rendering multiple tabs.
    - Implementing tab dragging, reordering, and detaching into new windows.
    - Displaying a flashing effect to grab user attention.
- **`Dash.svelte`**: A full-screen overlay for managing workspaces. It displays the "Current Desktop" alongside saved layouts. Users can preview, restore, rename, and delete layouts. It serializes the state of all open windows (including component type and props) into a JSON object for persistence.

### 3.2. IOSK Applications

These components interact with a remote IOSK backend, typically arbitrated through an `IoskConsole` instance.

- **`IoskConsole.svelte`**: The primary interface to an IOSK server.
    - **Connection**: Manages the WebSocket connection and user handshake.
    - **Terminal**: Displays output from the server and sends user input. Includes ANSI color support.
    - **Room/User Management**: Displays a list of users in the current "room", distinguishing between local and remote users. Provides a context menu on users for actions like private chat, viewing logs, or inspecting context.
    - **Event Broker**: Subscribes to `ioskEvents.js` stores to act on requests from other components (e.g., file listing) and publishes events from the server (e.g., incoming messages).
- **`IoskFileExplorer.svelte`**: A file browser for the remote system.
    - **Views**: Supports flat list, nested tree list, and tile views.
    - **Navigation**: Allows browsing through the remote directory structure.
    - **File Operations**: Opens files in `IoskFileViewer`.
    - **Live Updates**: A "Watch" mode provides real-time updates on file changes in the current directory, with animations for new, modified, or removed files.
- **`IoskFileViewer.svelte`**: Views files from the IOSK backend.
    - **Content Types**: Can render images, Markdown, and syntax-highlighted source code. It falls back to a raw text or hex view for other file types.
    - **Performance**: Implements chunked loading for large text files to ensure the UI remains responsive.
    - **Tailing**: Supports a "Follow" mode to stream new content as it's appended to a file (e.g., a log file).
- **`IoskContextInspector.svelte`**: A developer tool for inspecting the internal state of AI agents (bots) running on the IOSK server. It provides a detailed, tabbed view of an agent's memory, command history, environment, and token usage statistics. It features a "pop-out" capability, allowing different sections to be viewed in separate windows.
- **`IoskWatch.svelte`**: A utility, similar to the Linux `watch` command, that repeatedly executes a given command on the IOSK server and displays the output.
- **`IoskPrivateChat.svelte`**: A window for one-on-one messaging with other users in the IOSK room.

### 3.3. Local Backend Applications

These components interact with the local backend service.

- **`LocalTerminal.svelte`**: A full-featured terminal emulator (`xterm.js`) connected to the user's local shell.
- **`LocalFileExplorer.svelte`**: A file browser for the local filesystem. It also serves as a file/path picker for other applications like `Ask`.
- **`Ask.svelte`**: A powerful interface to the `sk ask` command.
    - **Input**: Accepts a text prompt and a list of attached local files/directories.
    - **Configuration**: Allows setting options for the AI model, including whether to use OpenAI, perform file modifications (`-w`), or take a screenshot.
    - **Output**: Streams the command's output in real-time.
    - **Telemetry**: Provides a real-time calculation of the total bytes and estimated tokens for the given prompt and attachments, helping users manage context size.

### 3.4. Utility Applications

- **`Calculator.svelte`**: A standard calculator application with keyboard support.
- **`WebBrowser.svelte`**: A simple browser using an `<iframe>` to render web pages.
- **`Settings.svelte`**: The main interface for configuring global desktop settings stored in `desktopStore.js`.

## 4. Technical Details & Data Flow

### 4.1. Application Launch

1.  A user clicks an option in the `Taskbar`'s start menu (e.g., "Calculator").
2.  The `Taskbar` calls an exported function from `windows.js`, like `newCalculator()`.
3.  `newCalculator()` calls the core `windows.addWindow(Calculator, { ...props })`.
4.  `addWindow` creates a new window group object with a new tab object inside it. It checks `windowSettings` for any saved default position/size for the `Calculator` component.
5.  It adds this new group to the `$windows` store array, bringing it into focus with the highest `zIndex`.
6.  Svelte's reactivity triggers `Desktop.svelte` to re-render. It creates a new `Window.svelte` for the frame and renders the `Calculator.svelte` component in the tab content layer.

### 4.2. IOSK File Listing Flow

This flow demonstrates the decoupled event-bus architecture.

1.  The user navigates to a new directory in an `IoskFileExplorer` instance.
2.  `IoskFileExplorer` dispatches a request by setting the `fileSystemRequests` store in `ioskEvents.js`. The request includes its unique `requesterId` (the tab ID) and the `consoleId` it's linked to.
3.  The corresponding `IoskConsole` instance is subscribed to `fileSystemRequests`. It sees the new request, checks if the `consoleId` matches its own, and sends the `fs_list` command over its WebSocket to the IOSK server.
4.  The IOSK server responds with an `fs_list_response` message.
5.  `IoskConsole` receives the message, sees it's a response for another component (based on the `requesterId`), and publishes it to the `fileSystemResponses` store.
6.  `IoskFileExplorer` is subscribed to `fileSystemResponses`. It sees the response, checks if the `requesterId` matches its own ID, and updates its UI with the new file list.

### 4.3. Dash Layout Save/Restore

-   **Saving**: When a user saves a layout in `Dash.svelte`, the `generateLayoutObject` function is called. It iterates through the live `$windows` store. For each window group and tab, it extracts essential, serializable data: position, size, component type (as a string), and relevant props (`wsUrl`, `username`, `currentPath`, etc.). This JSON object is added to the `$dashLayouts` store, which is persisted to `localStorage`.
-   **Restoring**: When a user clicks a saved layout, `handleRestoreLayout` is called. It iterates through the saved `windowGroups` in the layout object. For each group, it calls `windows.restoreWindow()`. This function uses the `componentMap` to turn the component name string back into a Svelte component reference and then creates new windows and tabs with the saved properties, effectively recreating the saved state. It also intelligently scales window positions and sizes relative to the current screen dimensions.

