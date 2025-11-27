# Proposal: Skybox - A Recursive Desktop & Workspace Environment

**Author:** LANNOCC
**Date:** 11/26/2025
**Status:** Draft

## 1. Introduction & Vision

The SKYBOARD desktop environment provides a powerful, multi-window interface for interacting with both local systems and remote `iosk` instances. However, its current metaphor remains rooted in the traditional desktop: a flat space populated by ephemeral windows. Project contexts are managed manually by opening related applications, and the `sk local` process acts as a simple, stateless bridge.

This proposal, codenamed **Skybox**, outlines a significant evolution of this paradigm. We will transform the flat desktop into a spatial, project-oriented environment built on a recursive design pattern. This upgrade aims to create a deeply integrated, persistent, and portable workspace that seamlessly blends local development, `iosk` collaboration, and AI interaction.

The core vision is to elevate SKYBOARD from a window manager into a true **workspace orchestrator**, where projects (represented as "Boxes") are first-class citizens and the user interface itself is a flexible, composable structure we call a "BOARD".

## 2. Core Concepts

### 2.1. The "Box": A Workspace Made Manifest

The fundamental organizing principle of Skybox is the "Box". A Box is a visual and functional representation of a project or workspace.

*   **Association**: Each Box is centered around either a local filesystem path or a connection to an `iosk` instance.
*   **Visuals**: On the desktop, a Box appears as a single, large panel. It is more substantial than an icon, suggesting it contains a rich workspace.
*   **Unfolding**: On mouseover, the Box visually unfolds. The central panel remains, while new panels emerge from the top, bottom, left, and right. An optional "cover" panel (e.g., a preview image or project logo) can unfold from the top, creating a second top-level panel.

This interaction provides a quick, spatial way to access different facets of a project without leaving the main desktop view.

### 2.2. The Recursive "BOARD"

The name SKYBOARD is an acronym: **S**ide**K**ick **Y**-Combinator **BOARD**. The "Y" represents recursion, which is the architectural key to Skybox. The fundamental UI container is a **BOARD**, which can manifest in one of four ways:

*   **a) A single Window**: A standard application component (e.g., `IoskConsole`, `Calculator`).
*   **b) Tabs**: A single window frame containing multiple switchable application views.
*   **c) A Dash**: The current desktop model—a collection of free-floating windows on a shared background. Dashes can be saved and restored.
*   **d) A Back**: A collection of windows that have been "locked in" to the desktop, losing their frames and becoming part of the background canvas.

The recursive power comes from this principle: **every panel of a Box is itself a BOARD**. This means a Box's central panel could be a terminal (a single window), its right panel could be a saved Dash of related file viewers, and its top panel could be a locked-in `IoskWatch` instance.

### 2.3. The "Back": A Composable Desktop Background

To complete the BOARD concept, we introduce the "Back". Whereas a "Dash" is a saved layout of floating windows, a "Back" is a saved layout of embedded windows.

*   **Locking In**: Any open window can be "locked in" to the desktop. This action removes its title bar, borders, and all window "chrome".
*   **Embedding**: The window's content area becomes a persistent, non-interactive (by default) element of the desktop background itself, fixed at its current size and position. It is no longer draggable or resizable.
*   **Saving**: This collection of locked-in windows forms a "Back", which can be saved, named, and loaded, just like Dashes.

This allows users to create persistent, information-rich dashboards and ambient displays as their desktop background, separate from their active, floating windows.

## 3. The User Experience

### 3.1. Creating and Managing Boxes

A user can initiate a "New Box" action from the taskbar menu. The system will prompt for:
1.  **A local filesystem path**.
2.  **An action**:
    *   **Use as Box**: The selected directory becomes the context for the new Box.
    *   **New Box in Path**: The user provides a name for a new subdirectory, which is then created and used as the Box's context.
3.  Alternatively, the user can select an active `iosk` connection, which will then become the context for the new Box.

The new Box appears on the desktop, ready for configuration. Its panels would initially be blank, allowing the user to populate them.

### 3.2. AI Integration with Boxes

The "ask" functionality will be extended to this new metaphor:
*   **Ask a Box**: Right-clicking a Box will offer an "Ask..." option. This will package the Box's entire context (the associated local directory or `iosk` state) and open the `Ask.svelte` window, pre-filled with the attachment.
*   **Ask a Panel**: If a panel contains a context (e.g., a File Explorer or a single File Viewer), it can also be "asked" individually.

This provides a powerful, intuitive way to scope AI queries to entire projects or specific parts of them.

## 4. Proposed Architecture

### 4.1. The "Skybox Service" (`sk local` 2.0)

The `sk local` process will be significantly upgraded from a simple WebSocket bridge to a persistent local service. This service will be an optional enhancement; the core SKYBOARD desktop will remain fully functional without it.

*   **Persistence Layer**: It will manage a lightweight local database (e.g., SQLite) located in the user's application data directory. This database will be the source of truth for all new Skybox-related configurations:
    *   All saved Dashes and Backs.
    *   Box definitions (name, context path/iosk connection, panel configurations).
*   **Separation of Concerns**: To ensure that the core SKYBOARD desktop can still operate in a lightweight, backend-less mode, existing configurations such as Desktop Settings and default window settings will **continue to be stored in the browser's `localStorage`**. The Skybox Service is responsible only for persisting the new, richer workspace configurations.
*   **Expanded WebSocket API**: New message types will be added to the protocol for creating, reading, updating, and deleting Boxes, Dashes, and Backs.
*   **Data Portability**: The service will expose simple HTTP endpoints (e.g., `/export`, `/import`) to allow users to save their entire Skybox workspace configuration (Boxes, Dashes, Backs) to a single file and import it on another machine or browser. This makes the project-oriented workspaces portable, while basic desktop settings remain local to the browser.

### 4.2. SKYBOARD Frontend (Svelte)

*   **New Components**:
    *   `Skybox.svelte`: A component to render a Box and handle its unfolding animation and panel layout.
    *   `DesktopManager.svelte`: A new top-level component within `Desktop.svelte` responsible for rendering the "Back" (locked-in windows) behind the layer of normal floating windows.
*   **`windows.js` & `desktop.js` Refactor**:
    *   State management for "Backs" will be added.
    *   A `lockedIn: boolean` property will be added to the window group state. A `lockWindow(groupId)` function will toggle this state.
    *   Logic will be added to read/write Box, Dash, and Back configurations from the Skybox Service via the WebSocket connection. Existing settings management using `localStorage` will be preserved for core desktop functionality.
*   **`Dash.svelte` Modifications**: This component will be refactored to manage both floating Dashes and locked-in Backs, presenting them as distinct savable layout types.
*   **`Taskbar.svelte`**: A "New Box" menu item will be added.

## 5. Implementation Plan

This plan outlines a phased approach to implementing the Skybox feature set, allowing for incremental delivery and testing.

### 5.1. Phase 1: The Basic Box

This initial phase focuses on establishing the core "Box" entity and its persistence via the upgraded `sk local` service.

#### 5.1.1. `sk local` Service Enhancement

The `sk local` process must be upgraded to a stateful service that manages persistence for Skybox entities.

*   **Persistence Layer (SQLite)**:
    *   Utilize Python's built-in `sqlite3` library. No new dependencies are required.
    *   On startup, `sk/local.py` will establish a connection to a database file named `skybox.db` located within the user's data directory, managed by `appdirs` (consistent with `sk/config.py`). A function will be created to initialize the database and create tables if they don't exist.
    *   A `boxes` table will be created with the following schema for Phase 1:
        ```sql
        CREATE TABLE IF NOT EXISTS boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('local', 'iosk')),
            context TEXT NOT NULL
        );
        ```
        - `id`: Unique identifier for the box.
        - `name`: User-defined name for the box (e.g., "SideKick Project").
        - `type`: The context type, either `'local'` for a filesystem path or `'iosk'` for a connection string.
        - `context`: The filesystem path or `iosk` WebSocket URL.

*   **Expanded WebSocket API**:
    *   The `websocket_handler` in `sk/local.py` will be extended to recognize new `msg_type` values. Each new type will be routed to a dedicated async handler function.
    *   **New Client-to-Server Messages**:
        - `{ "type": "list_boxes" }`: Triggers the server to query and return all boxes.
        - `{ "type": "create_box", "name": "...", "box_type": "local", "context": "/path/to/dir" }`: Creates a new box record in the database.
        - `{ "type": "delete_box", "id": 123 }`: Deletes a box record.
        - `{ "type": "update_box", "id": 123, "name": "New Name" }`: Updates a box's properties (initially, just the name).
    *   **New Server-to-Client Messages**:
        - `{ "type": "boxes_list", "boxes": [...] }`: Sent in response to `list_boxes`, containing an array of all box objects from the database.
        - A confirmation message (e.g., `{ "type": "box_created", "box": {...} }`) should be sent after a successful creation, followed by a new `boxes_list` broadcast to all clients to ensure synchronization. The same pattern applies to updates and deletions.

#### 5.1.2. SKYBOARD UI Integration

The frontend will be updated to communicate with the new service endpoints and render the Box entities.

*   **State Management (`local.js`, `desktop.js`)**:
    *   In `sv/local.js`, a new store `export const boxes = writable([]);` will be created.
    *   The `onmessage` handler in `connect()` will be updated to process the `boxes_list` message type, calling `boxes.set(msg.boxes)`.
    *   Functions like `sendMessage({ type: 'list_boxes' })` will be called within `connect()` upon successful connection to fetch the initial state. Helper functions like `createBox(name, type, context)` will be added to abstract `sendMessage` calls.
    *   The `boxes` store will be re-exported from `sv/desktop.js` for consumption by UI components.

*   **UI Components**:
    *   **`Taskbar.svelte`**: A "New Box..." item will be added to the "Start Menu". Clicking it will open a new modal component (`NewBoxModal.svelte`, not yet created) responsible for gathering the required information (name, type, context).
    *   **`Desktop.svelte`**: This component will subscribe to the `boxes` store. It will contain a new section that iterates through the `$boxes` array and renders a `<Box>` component for each entry.
    *   **New `Box.svelte` Component**:
        - It will accept a `box` object as a prop.
        - It will render as a draggable panel on the desktop. Its position will need to be persisted in a later phase, but for Phase 1, it can be auto-arranged.
        - It will implement a right-click context menu (similar to the one in `Dash.svelte`) with options for "Rename", "Delete", and "Ask...".

#### 5.1.3. Visual Interaction

The initial visual feedback for the Box will be implemented.

*   **`Box.svelte` Structure & Animation**:
    *   The component will consist of a main container with `position: relative`.
    *   Inside, a central panel and four side panels (top, bottom, left, right) will be positioned absolutely.
    *   Initially, the side panels will have `opacity: 0` and be transformed to be hidden behind the central panel (e.g., `transform: scale(0)` or `translateY(-100%)`).
    *   On `:hover` of the main container, CSS transitions will be triggered to change the `opacity` and `transform` of the side panels, creating the "unfolding" effect.
    *   For Phase 1, these panels will be simple `div` elements with a background color, serving as visual placeholders. They will not contain any content.

### 5.2. Phase 2: Populating Box Panels

This phase enables the configuration of Box panels with BOARDs (excluding the "Back" type for now).

*   **Panel Configuration**: Extend the data model and API to support saving BOARD configurations (single window, tabs, or a floating "Dash") to each of a Box's panels.
*   **State Restoration**: When a Box unfolds, its configured panels will correctly instantiate and display their saved BOARDs.
*   **Cover Image**: Allow users to assign a "cover" image to a Box, which will be displayed on one of the unfolding panels.

### 5.3. Phase 3: The "Back" and Full Desktop Integration

This final phase introduces the "Back" concept, fully realizing the recursive BOARD model and enabling Boxes to act as complete desktop replacements.

*   **"Back" Implementation**: Implement the "lock in" functionality, allowing any window to be embedded into the desktop background. The collection of "locked-in" windows can now be saved as a "Back".
*   **Box as Desktop**: A Box can be configured with a "Back" (to replace the desktop background) and/or a "Dash" (to replace the current set of floating windows). Activating the Box will apply this full desktop layout.
*   **Saving to a Box**: The user can save the entire current desktop state (its Back and Dash) directly into a Box.
*   **Navigation**: Implement a clear UI mechanism to return to the main "desktop of boxes" view from within a full-Box-desktop.

## 6. Future Vision

This proposal lays the foundation for even more powerful features:

*   **Shared Boxes**: With a cloud backend (as envisioned in `cloudseed.md`), the portable export format could be used to share entire Box workspaces with team members.
*   **Deeper `iosk` Integration**: An `iosk` Box could have panels that dynamically represent different aspects of the remote system, such as a panel for each logged-in user, a panel for running processes, or a panel tailing a specific log file.
*   **A Box Marketplace**: Users could create and share pre-configured Box templates for common development environments (e.g., "Python/Django Box", "SvelteKit Box"), which could be imported directly into their desktop.

## 7. Conclusion

The Skybox initiative transforms SKYBOARD from a simple desktop interface into a comprehensive, project-centric workspace management system. By introducing the recursive concepts of "Boxes" and "BOARDs", we create an infinitely flexible and intuitive UI. Elevating `sk local` to a persistent service with a local database ensures that these rich, customized environments are durable and portable. This represents the next logical step in the evolution of the SideKick Suite, fulfilling the "Y-Combinator" promise of SKYBOARD and creating a powerful, scalable platform for human-computer and AI-computer collaboration.