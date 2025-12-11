# Proposal: Unifying the Local and IOSK File Explorers

**Author:** LANNOCC
**Date:** 12/8/2025
**Status:** Draft

## 1. Introduction & Motivation

Currently, the SKYBOARD environment contains two distinct sets of components for file system interaction: `IoskFileExplorer`/`IoskFileViewer` for remote `iosk` instances, and `LocalFileExplorer`/`LocalFileViewer` for the local machine via the `sk bridge` service.

This separation has led to a significant feature disparity. The `iosk` components are far more advanced, offering multiple view modes (list, tiles, columns), nested directory browsing, live file watching, color-coded listings, and a sophisticated file viewer with syntax highlighting and content tailing. The local components, by contrast, provide only a basic list view and a simple text viewer.

This divergence creates several problems:
*   **Inconsistent User Experience:** Users are presented with a rich interface for remote systems but a minimal one for their local machine.
*   **Increased Maintenance Overhead:** We must maintain two separate codebases for what is conceptually the same task.
*   **Blocked Progress:** As we plan to enhance the `sk bridge` service with features like file watching (as per the `skybox.md` vision), we would have to duplicate the implementation effort on the frontend.

This proposal outlines a plan to unify these components. We will create a single, feature-rich `FileExplorer.svelte` and `FileViewer.svelte` derived from the superior `iosk` implementations. These new components will be engineered to work seamlessly with either the `iosk` or `sk bridge` backend, gracefully adapting their UI to the capabilities of the connected service.

## 2. Core Requirements

1.  **Component Unification:** Replace the four existing file components with two: `FileExplorer.svelte` and `FileViewer.svelte`.
2.  **Feature Preservation:** The new unified components must retain all advanced features from the current `Iosk` versions.
3.  **Backend Agnosticism:** The components must operate correctly when connected to either a remote `iosk` instance or the local `sk bridge` service.
4.  **Graceful Degradation:** UI elements for features not yet supported by the `sk bridge` backend (e.g., "Watch", "Nested View", "Follow") must be automatically hidden or disabled when connected locally.
5.  **Functionality Porting:** Features unique to `LocalFileExplorer` (e.g., the "Box this" right-click context menu) must be ported to the new `FileExplorer.svelte` and enabled only for skybridge (local) connections.

## 3. Proposed Architecture: The Filesystem Adapter

To achieve backend agnosticism without cluttering the component logic, we will introduce a new abstraction layer: the **Filesystem Adapter**. This adapter will provide a consistent interface (methods and Svelte stores) for the UI components to use, while internally handling the communication differences between the two backends.

*   The **IOSK backend** uses a multi-connection model where each `IoskConsole` has its own WebSocket. Communication is targeted using a `consoleId` and funneled through Svelte stores in `sv/board/iosk.js`.
*   The **Local backend** uses a single, global WebSocket connection managed by `sv/bridge.js`, with global Svelte stores for responses.

The adapter will abstract these differences away. A new file, `sv/board/fs_adapter.js`, will export a factory function:

```javascript
// in sv/board/fs_adapter.js
import { writable }_from 'svelte/store';
import { fileSystemRequests, fileSystemResponses, ... } from './iosk.js';
import { sendMessage, fsListResponse, fsReadResponse, ... } from '../bridge.js';

export function createFsAdapter({ connectionType, consoleId, requesterId }) {
    // Stores for the component to subscribe to.
    const listResponse = writable(null);
    const readResponse = writable(null);
    // ... etc. for watch and tail events

    // Subscribe to the appropriate global store and forward relevant messages.
    if (connectionType === 'iosk') {
        fileSystemResponses.subscribe(msg => {
            if (msg && msg.requesterId === requesterId) {
                // Forward fs_list_response, fs_read_response, etc.
                // to the adapter's specific stores.
            }
        });
    } else { // 'skybridge'
        fsListResponse.subscribe(msg => listResponse.set(msg));
        fsReadResponse.subscribe(msg => readResponse.set(msg));
    }

    // Return the public API for the component to use.
    return {
        // Response stores
        listResponse,
        readResponse,

        // Action methods
        requestPath: (path, recursive) => {
            if (connectionType === 'iosk') {
                const command = { type: 'fs_list', path, recursive, ... };
                fileSystemRequests.set({ consoleId, requesterId, command, ... });
            } else {
                sendMessage({ type: 'fs_list', path });
            }
        },

        readFile: (path, offset, length) => {
            // ... similar logic
        },

        // ... other methods for watch, tail, etc.
    };
}
```

This architecture cleanly separates the component's UI logic from the underlying communication mechanism.

```
+---------------------+      +----------------------+      +--------------------+
| FileExplorer.svelte |----->| Filesystem Adapter   |----->| sv/board/iosk.js   | (for 'iosk')
+---------------------+      |                      |      +--------------------+
                             | - requestPath()      |
                             | - readFile()         |      +--------------------+
                             | - listResponse store |----->| sv/bridge.js       | (for 'skybridge')
                             | - ...                |      +--------------------+
                             +----------------------+
```

## 4. Implementation Plan

### Phase 1: Frontend Unification

This phase focuses on creating the unified components and the adapter, without requiring any backend changes.

1.  **Component Consolidation:**
    *   Rename `sv/board/IoskFileExplorer.svelte` to `sv/board/FileExplorer.svelte`.
    *   Rename `sv/board/IoskFileViewer.svelte` to `sv/board/FileViewer.svelte`.
    *   Delete `LocalFileExplorer.svelte` and `LocalFileViewer.svelte`.

2.  **Adapter Implementation:**
    
    *   Create the `sv/board/fs_adapter.js` file and implement the `createFsAdapter` function as described in the architecture section. It will need to handle requests and responses for `list`, `read`, `watch`, and `tail`.
    
3.  **Refactor `FileExplorer.svelte`:**
    *   Add new props: `export let connectionType; // 'iosk' or 'skybridge'`. The `consoleId` prop will now only be used for `iosk` connections.
    *   Remove all direct imports from `sv/board/iosk.js`.
    *   In the `<script>` section, instantiate the adapter: `let fsAdapter; onMount(() => { fsAdapter = createFsAdapter({ connectionType, consoleId, requesterId: id }); });`
    *   Replace all data requests (e.g., `fileSystemRequests.set(...)`) and store subscriptions (e.g., `fileSystemResponses.subscribe(...)`) with calls to the adapter's methods and stores.
    *   **Implement Feature Flags:** Conditionally render or disable UI elements based on backend capabilities.
        ```javascript
        $: supportsWatch = connectionType === 'iosk';
        $: supportsRecursive = connectionType === 'iosk'; // For 'Nested' and 'Columns' views
        ```
        ```svelte
        {#if supportsWatch}
            <button class="watch-button" on:click={toggleWatch}>...</button>
        {/if}
        {#if supportsRecursive}
            <button ... on:click={toggleNestedView}>Nested</button>
        {/if}
        ```
    *   **Port Local Features:** Integrate the right-click context menu and `handleDragStart` logic from the old `LocalFileExplorer`. The "Box this" option should only be shown if `connectionType === 'skybridge'`.

4.  **Refactor `FileViewer.svelte`:**
    *   Apply the same pattern: add the `connectionType` prop, instantiate and use the `fs_adapter.js`.
    *   Implement a feature flag for the "Follow" button, as tailing is not yet supported on the skybridge backend.
        ```javascript
        $: supportsTail = connectionType === 'iosk';
        ```
        ```svelte
        <button on:click={toggleFollow} disabled={!supportsTail}>Follow</button>
        ```

5.  **Update Window Management:**
    *   Modify `sv/windows.js` (and any other relevant files) to remove references to the old components.
    *   Create new helper functions like `newFileExplorer({ connectionType, consoleId, initialPath })`.
    *   Update menus and actions that open file explorers/viewers to call these new functions with the correct `connectionType`.

### Phase 2: Backend Parity (Future Work)

This phase outlines the planned enhancements to the skybridge backend, which will be simplified by the frontend unification already being in place.

1.  **Enhance `sk bridge` Service:**
    *   Implement a `recursive` flag for the `fs_list` command to return entire directory trees.
    *   Add `fs_watch_start` / `fs_watch_stop` commands and a new server-to-client `fs_watch_event` message to provide live updates.
    *   Add `fs_tail_start` / `fs_tail_stop` commands and a new `fs_tail_event` message for live file content streaming.
2.  **Enable Features on Frontend:**
    *   As each feature is added to the `sk bridge` backend, the corresponding feature flag in the Svelte components can be updated or removed (e.g., `$: supportsWatch = true;`).
    *   No major component refactoring will be needed; the UI will simply light up with new functionality as the backend's capabilities grow.

## 5. Conclusion

Unifying our file system components is a critical step towards a cleaner, more maintainable codebase and a more consistent, powerful user experience. By introducing a Filesystem Adapter, we can elegantly handle the differences between our skybridge and iosk backends while building on our most feature-rich components. This work not only resolves current inconsistencies but also paves the way for future enhancements to the `sk bridge` service, ensuring our frontend architecture is ready to support them from day one.

