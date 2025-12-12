# Proposal: Skybox - A Recursive Desktop & Workspace Environment

**Author:** LANNOCC
**Date:** 11/26/2025
**Status:** Implemented

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
    *   A `box` table will be created with the following schema for Phase 1:
        ```sql
        CREATE TABLE IF NOT EXISTS box (
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
        - `{ "type": "box_list", "boxes": [...] }`: Sent in response to `list_boxes`, containing an array of all box objects from the database.
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

This phase focuses on making the Box panels functional by allowing them to contain and persist different types of UI layouts, known as BOARDs. This will be achieved through a combination of database schema extensions, new WebSocket APIs, and enhanced frontend components that support dynamic rendering and user interaction.

#### 5.2.1. `sk local` Service Enhancement

The backend service will be updated to store and serve the configuration for each panel within a Box.

*   **Persistence Layer (SQLite) Extension**:
    *   A new table, `panel`, will be created in `skybox.db` to store the configuration for each of a Box's six potential panels (center, top, bottom, left, right, and cover).
    *   This table will be linked to the `box` table via a foreign key, and its schema will be as follows:
        ```sql
        CREATE TABLE IF NOT EXISTS panel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            location TEXT NOT NULL CHECK(location IN ('center', 'top', 'bottom', 'left', 'right', 'cover')),
            board_type TEXT NOT NULL CHECK(board_type IN ('empty', 'window', 'tabs', 'dash', 'image')),
            board_config TEXT, -- JSON blob for the BOARD configuration
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE,
            UNIQUE(box_id, location)
        );
        ```
        - `box_id`: Links the panel to its parent box.
        - `location`: Defines the panel's position.
        - `board_type`: Specifies the type of content the panel holds.
        - `board_config`: A JSON string containing the detailed configuration for the BOARD. For `board_type: 'dash'`, this will be a full Dash layout object. For `window` or `tabs`, it will contain the necessary properties to restore the component(s) (e.g., component type, title, initial state). For `image`, it will store the image URL.

*   **Expanded WebSocket API**:
    *   The `websocket_handler` in `sk/local.py` will be extended with new message types for managing panel content.
    *   **New Client-to-Server Messages**:
        - `{ "type": "get_box_config", "id": 123 }`: Requests the configurations for all panels associated with the specified `box_id`.
        - `{ "type": "set_panel_config", "box_id": 123, "location": "right", "board_type": "tabs", "board_config": {...} }`: Creates or updates the configuration for a specific panel. Sending `board_type: 'empty'` will clear the panel.
    *   **New Server-to-Client Messages**:
        - `{ "type": "box_config_response", "box_id": 123, "panels": [...] }`: Sent in response to `get_box_config`. The `panels` array will contain objects matching the `panels` table schema for that box.
        - After a `set_panel_config` is processed successfully, a new `box_config_response` will be broadcast to all connected clients to ensure all views are synchronized.

#### 5.2.2. SKYBOARD UI Integration

The frontend will be enhanced to allow users to configure panels and to render the saved BOARDs when a Box unfolds.

*   **State Management (`local.js`, `desktop.js`)**:
    *   The `boxes` store in `desktop.js` will be updated so that each box object contains a `panels` property (e.g., a map of `location` to panel configuration).
    *   The `onmessage` handler in `sv/local.js` will process the `box_config_response` message, finding the relevant box in the `boxes` store and updating its `panels` property.
    *   A new helper function, `savePanelConfig(boxId, location, boardType, config)`, will be added to `sv/local.js` to abstract the `set_panel_config` WebSocket message.

*   **Panel Configuration UI**:
    *   **Drag-and-Drop**: Users will configure panels primarily through drag-and-drop.
        - An open window (or a window group with tabs) can be dragged from the desktop and dropped onto one of a Box's unfolded panels.
        - The `dragState` store in `sv/windows.js` will be extended to detect when a drag operation is hovering over a valid panel drop target.
        - Upon dropping a window, a helper function (similar to `generateLayoutObject` in `Dash.svelte`) will create the `board_config` object. The appropriate `board_type` (`window` or `tabs`) will be determined, and `savePanelConfig` will be called.
    *   **Cover Image**: A "Set Cover Image" option will be added to the Box's right-click context menu. This will prompt the user for an image URL and save it as the 'cover' panel with `board_type: 'image'`.
    *   **Dash Panel**: A saved layout tile from `Dash.svelte` can be dragged onto a panel. This will set the panel's `board_type` to `dash` and store the entire layout object in `board_config`.

*   **State Restoration and Rendering**:
    *   The `Box.svelte` component will be refactored. On hover, when a panel unfolds, it will dynamically render its content based on the `board_type` from its configuration.
    *   A new component, tentatively named `Board.svelte`, will be created to handle this dynamic rendering. It will receive `board_type` and `board_config` as props.
    *   Using `<svelte:component>`, `Board.svelte` will instantiate the correct view:
        - **`window`**: It will render the specified component directly within the panel's bounds, passing the saved props (e.g., `initialPath` for a file explorer). The panel itself serves as the window frame.
        - **`tabs`**: It will render a compact tab bar and the active tab's component, effectively creating a mini-window within the panel.
        - **`dash`**: It will render a miniature, self-contained desktop environment, recursively using components like `Desktop.svelte` and `Window.svelte`, and populate it by calling `windows.restoreWindow` for each item in the saved layout.
        - **`image`**: It will render an `<img>` tag for the cover panel.

#### 5.2.3. Visual Interaction

The visual feedback for panel configuration will be made clear and intuitive.

*   **Drop Target Highlighting**: When a window is dragged over a valid, empty panel on an unfolded Box, the panel will light up or display an icon to indicate it is a drop target.
*   **Content Loading Animation**: When a Box unfolds, the panels will animate into place first. The content within each panel (the BOARD) will then fade in smoothly, preventing visual lag during the unfolding transition.
*   **Cover Panel Unfolding**: The cover panel will unfold from the top, simultaneously with or just before the main top panel, creating a layered, visually appealing reveal. Its content will simply be the configured image, styled to fit the panel.

This phase transforms the static Box placeholders from Phase 1 into fully functional, configurable, and persistent mini-workspaces, setting the stage for the full desktop integration planned in Phase 3.

### 5.3. Phase 3: The "Back" and Full Desktop Integration

This final phase introduces the "Back" concept, fully realizing the recursive BOARD model. It enables windows to be "locked in" as part of the desktop background and allows a Box to represent a complete, loadable desktop environment, including both its background ("Back") and its floating windows ("Dash").

#### 5.3.1. `sk local` Service Enhancement

The backend service's persistence layer and API will be extended to manage "Backs" and associate full desktop layouts with Boxes.

*   **Persistence Layer (SQLite) Extension**:
    *   A new table, `back`, will be created in `skybox.db` to store saved background layouts. Its structure will be analogous to how Dashes are stored.
        ```sql
        CREATE TABLE IF NOT EXISTS back (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            layout_config TEXT NOT NULL -- JSON blob of locked-in window groups
        );
        ```
    *   The existing `box` table will be altered to link to a default Dash and a default Back, representing a complete workspace.
        ```sql
        ALTER TABLE box ADD COLUMN active_dash_id INTEGER REFERENCES dash(id);
        ALTER TABLE box ADD COLUMN active_back_id INTEGER REFERENCES back(id);
        ```

*   **Expanded WebSocket API**:
    *   The `websocket_handler` in `sk/local.py` will be expanded to manage `back` and update `box` with desktop layout associations.
    *   **New Client-to-Server Messages**:
        - `{ "type": "list_backs" }`: Requests all saved Back layouts.
        - `{ "type": "create_back", "name": "...", "layout_config": {...} }`: Creates a new Back record. The server will respond with the newly created back object, including its ID.
        - `{ "type": "delete_back", "id": 123 }`: Deletes a Back record.
        - `{ "type": "update_box_desktop", "id": 123, "dash_id": 4, "back_id": 7 }`: Updates a Box to associate it with a specific Dash and Back.
    *   **New Server-to-Client Messages**:
        - `{ "type": "back_list", "backs": [...] }`: Sent in response to `list_backs` and broadcast on any change.
        - Standard confirmation messages (`back_created`, `back_deleted`, etc.) will be sent, followed by a `back_list` broadcast to synchronize all clients.

#### 5.3.2. SKYBOARD UI Integration

The frontend will be updated to implement the "lock in" feature, manage Backs, and handle the activation of a Box as a full desktop environment.

*   **State Management (`windows.js`, `desktop.js`)**:
    *   **`windows.js`**:
        - A `lockedIn: boolean` property will be added to the window group state object. It will default to `false`.
        - A new exported function, `lockWindow(groupId)`, will be created. It will find the specified window group and set its `lockedIn` property to `true`.
        - A corresponding `unlockWindow(groupId)` will set `lockedIn` to `false`.
    *   **`desktop.js`**:
        - A new store, `export const backs = writable([]);`, will be added to manage saved Back layouts, mirroring `dashLayouts`.
        - A store to track the currently active workspace: `export const activeBox = writable(null);`. When `null`, the main "desktop of boxes" is shown. When it holds a box object, a full-box-desktop is active.
    *   **`local.js`**:
        - The `onmessage` handler will be updated to process `back_list` messages and populate the `back` store.
        - Helper functions will be added to send the new WebSocket messages: `saveBack(name, config)`, `deleteBack(id)`, `updateBoxDesktop(boxId, dashId, backId)`.

*   **UI Components**:
    *   **`Desktop.svelte`**:
        - The main render loop (`{#each $windows as win...}`) will be split. It will first iterate and render all windows where `win.lockedIn` is `true`, followed by a second loop for windows where `lockedIn` is `false`.
        - For locked-in windows, it will not render the `<Window>` component. Instead, it will directly render the tab content wrapper (`<div class="tab-content-wrapper">...</div>`) and the component inside it, positioned using the window's `x, y, width, height`. The `pointer-events` on the content area will need to be managed to allow right-clicks for unlocking but prevent other interactions by default.
    *   **`Window.svelte`**:
        - The options menu (`showOptionsMenu`) will gain a "Lock In" item that calls `windows.lockWindow(id)`.
        - When a window is unlocked via a new context menu on the desktop, its `lockedIn` state will become false, and the standard `<Window>` component will reappear for it in the `Desktop.svelte` loop.
    *   **`Dash.svelte`**:
        - The UI will be updated with a toggle to switch between managing "Dashes" and "Backs".
        - The "Save Current Layout" button's logic will be modified:
            - In "Dash" mode, it saves the layout of floating windows (`$windows.filter(w => !w.lockedIn)`).
            - In "Back" mode, it saves the layout of locked-in windows (`$windows.filter(w => w.lockedIn)`).
        - The list of saved layouts will display both Dashes and Backs, with distinct icons or labels.
    *   **`Box.svelte` (not yet created)**:
        - A primary `on:click` event will activate the Box as a desktop. This will:
            1. Set the `activeBox` store in `desktop.js` to the clicked box object.
            2. Call `windows.closeAllWindows()`.
            3. Fetch the `active_dash_id` and `active_back_id` from the box's configuration.
            4. Find the corresponding layouts in the `$dashes` and `$backs` stores and call `windows.restoreWindow` for each item within them, setting the `lockedIn` flag appropriately for items from the Back.
    *   **`Taskbar.svelte`**:
        - The component will subscribe to the `activeBox` store.
        - When `$activeBox` is not `null`, the "Dash" button (`&mdash;`) will be replaced by a "Return to Skybox" button. This button's `on:click` handler will set `activeBox` back to `null` and call `windows.closeAllWindows()`.

#### 5.3.3. Visual Interaction & Workflow

The user experience for these new features will be designed to be intuitive and fluid.

*   **Locking and Unlocking**:
    - When "Lock In" is selected, the window's frame and title bar will fade out, leaving only the content area fixed on the desktop.
    - A right-click on the content area of a locked-in window will open a minimal context menu with an "Unlock" option. Selecting it will fade the window chrome back in and restore its floating behavior.
*   **Saving the Desktop to a Box**:
    - When a full-box-desktop is active, the "Save" button in the `Dash.svelte` interface will be repurposed. A click will prompt the user: "Save current layout to this Box?".
    - On confirmation, the system will automatically save the current floating windows as a new Dash, the locked-in windows as a new Back, and then update the active Box to point to these new layouts via `updateBoxDesktop`.
*   **Box Activation and Navigation**:
    - Activating a Box will trigger a zoom-in animation centered on the Box, with the new desktop (Back and Dash) fading in seamlessly.
    - The "Return to Skybox" button on the taskbar will provide a clear, persistent way to exit the Box's context and return to the main desktop, triggering a corresponding zoom-out/fade-out animation.

## 6. Future Vision

This proposal lays the foundation for even more powerful features:

*   **Shared Boxes**: With a cloud backend (as envisioned in `cloudseed.md`), the portable export format could be used to share entire Box workspaces with team members.
*   **Deeper `iosk` Integration**: An `iosk` Box could have panels that dynamically represent different aspects of the remote system, such as a panel for each logged-in user, a panel for running processes, or a panel tailing a specific log file.
*   **A Box Marketplace**: Users could create and share pre-configured Box templates for common development environments (e.g., "Python/Django Box", "SvelteKit Box"), which could be imported directly into their desktop.

## 7. Conclusion

The Skybox initiative transforms SKYBOARD from a simple desktop interface into a comprehensive, project-centric workspace management system. By introducing the recursive concepts of "Boxes" and "BOARDs", we create an infinitely flexible and intuitive UI. Elevating `sk local` to a persistent service with a local database ensures that these rich, customized environments are durable and portable. This represents the next logical step in the evolution of the SideKick Suite, fulfilling the "Y-Combinator" promise of SKYBOARD and creating a powerful, scalable platform for human-computer and AI-computer collaboration.
