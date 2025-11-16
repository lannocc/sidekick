<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { fileSystemRequests, fileSystemResponses, fileSystemWatchEvents } from './ioskEvents.js';
    import { newIoskFileViewer, windows } from './windows.js';
    import { windowSettings } from './desktopStore.js';

    export let id; // Window ID, passed from Window.svelte
    export let groupId;
    export let consoleId;
    export let initialPath = '.';
    export let componentName;
    export let x, y, width, height;

    export let consoleConnection = null; // Passed during Dash restore

    let currentPath = (initialPath && initialPath !== '.') ? initialPath : '/';
    let items = []; // { name, type, size, mtime }
    let errorMessage = '';

    let unsubscribeResponses;

    // --- State for Watch feature ---
    let isWatching = false;
    let unsubscribeWatchEvents;

    // --- View State ---
    let viewMode = 'list'; // 'list' or 'tiles'
    let colorMode = 'type'; // 'type' or 'age'

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsModel = { usePwd: true, path: '/' };
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };

    function getFileExtension(name) {
        if (name === '..') return '';
        const lastDot = name.lastIndexOf('.');
        if (lastDot === -1 || lastDot === 0) return '';
        return name.substring(lastDot + 1).toLowerCase();
    }

    function getTileColor(item, mode) {
        if (item.type === 'dir' && item.name === '..') return '#555e64';

        if (mode === 'age') {
            if (item.mtime <= 0) return '#7f8c8d';
            const now = Date.now() / 1000;
            const ageSeconds = now - item.mtime;

            if (ageSeconds < 3600) return '#27ae60';       // < 1 hour (green)
            if (ageSeconds < 86400) return '#2980b9';      // < 1 day (blue)
            if (ageSeconds < 604800) return '#f39c12';     // < 1 week (yellow)
            if (ageSeconds < 2592000) return '#d35400';    // < 1 month (orange)
            return '#c0392b';                              // older (red)
        } else { // mode === 'type'
            if (item.type === 'dir') return '#2980b9'; // Blue for directories

            const ext = getFileExtension(item.name);
            switch (ext) {
                case 'txt': case 'md': case 'json': case 'yml': case 'xml': case 'log':
                    return '#27ae60'; // Green for text-like
                case 'js': case 'py': case 'svelte': case 'html': case 'css': case 'sh': case 'c': case 'cpp':
                    return '#8e44ad'; // Purple for code
                case 'png': case 'jpg': case 'jpeg': case 'gif': case 'svg': case 'ico':
                    return '#c0392b'; // Red for images
                case 'zip': case 'gz': case 'tar': case 'rar':
                    return '#d35400'; // Orange for archives
                default:
                    return '#7f8c8d'; // Grey for others/files without extension
            }
        }
    }


    export function showSettingsDialog() {
        const allSettings = get(windowSettings);
        const currentSettings = allSettings[componentName];

        if (currentSettings && currentSettings.initialPath) {
            settingsModel = {
                usePwd: currentSettings.initialPath === '.',
                path: currentSettings.initialPath !== '.' ? currentSettings.initialPath : '/'
            };
        } else {
            // Default settings if none are saved
            settingsModel = { usePwd: true, path: '/' };
        }

        // Populate window settings for the modal
        const currentWindowSettings = allSettings[componentName] || { positioning: 'auto' };
        windowSettingsForModal = {
            positioning: currentWindowSettings.positioning || 'auto',
            x: currentWindowSettings.x ?? x,
            y: currentWindowSettings.y ?? y,
            width: currentWindowSettings.width ?? width,
            height: currentWindowSettings.height ?? height,
            defaultZoom: currentWindowSettings.defaultZoom ?? 1.0,
        };

        showSettings = true;
    }

    function handleSaveSettings() {
        const componentSettings = {
            initialPath: settingsModel.usePwd ? '.' : (settingsModel.path || '/')
        };

        windowSettings.update(all => ({
            ...all,
            [componentName]: { ...componentSettings, ...windowSettingsForModal }
        }));
        showSettings = false;
    }

    function handleCancelSettings() {
        showSettings = false;
    }

    // Whenever the current path changes, update the central window store
    // so its state can be saved by the Dash.
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { currentPath, consoleId });
    }

    $: if (consoleConnection && $windows) {
        // Check if our current consoleId is still valid
        const currentConsole = $windows.find(w => w.id === consoleId);
        if (!currentConsole || !currentConsole.isConsoleConnected) {
            // If not, clear it.
            if (consoleId) {
                consoleId = null;
                errorMessage = 'Connection lost. Waiting for reconnection...';
                items = [];
            }
        }

        // If we don't have a consoleId, try to find one
        if (!consoleId) {
            const compatibleConsoleTab = $windows.flatMap(w => w.tabs).find(t =>
                t.componentName === 'IoskConsole' &&
                t.isConsoleConnected &&
                t.consoleConnection &&
                t.consoleConnection.url === consoleConnection.url &&
                t.consoleConnection.user === consoleConnection.user
            );

            if (compatibleConsoleTab) {
                // Found one!
                consoleId = compatibleConsoleTab.id;
                requestPath(currentPath);
            } else {
                // Still no connection.
                errorMessage = 'No active IOSK connection available. Waiting for connection...';
                items = [];
            }
        }
    }

    function sendWatchRequest(type, path) {
        if (!consoleId) return;
        const request = {
            consoleId,
            command: { type, path }
        };
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
    }

    function toggleWatch() {
        isWatching = !isWatching;
        if (isWatching) {
            sendWatchRequest('fs_watch_start', currentPath);
        } else {
            sendWatchRequest('fs_watch_stop', currentPath);
        }
    }

    function requestPath(path) {
        errorMessage = '';
        if (!consoleId) {
            items = [];
            return false; // Indicate failure
        }
        const request = {
            consoleId,
            requesterId: id, // Identify this explorer window
            command: {
                type: 'fs_list',
                path
            }
        };
        // Use a unique object to ensure svelte store triggers update for same consecutive requests
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
        return true; // Indicate success
    }

    function handleItemClick(item) {
        if (item.type === 'dir') {
            if (isWatching) {
                sendWatchRequest('fs_watch_stop', currentPath);
                isWatching = false;
            }
            let newPath;
            if (item.name === '..') {
                // Navigate up
                if (currentPath === '/') return;
                newPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
            } else {
                // Navigate down
                newPath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
            }
            requestPath(newPath);
        } else if (item.type === 'file') {
            const filePath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
            newIoskFileViewer(consoleId, filePath);
        }
    }

    onMount(() => {
        unsubscribeResponses = fileSystemResponses.subscribe(response => {
            // Filter responses to only those intended for this specific explorer window
            if (response && response.requesterId === id) {
                // Ensure we only process fs_list_response here
                if (response.data.type !== 'fs_list_response') return;

                const { path, listing, error } = response.data;

                if (error) {
                    errorMessage = error;
                    items = [];
                } else if (listing) {
                    currentPath = path;
                    // Add parent directory ".." for navigation if not at root
                    const parentDir = { name: '..', type: 'dir', size: -1, mtime: -1 };
                    const sortedItems = listing.sort((a, b) => {
                        if (a.type === b.type) return a.name.localeCompare(b.name);
                        return a.type === 'dir' ? -1 : 1; // Directories first
                    });
                    items = (path !== '/') ? [parentDir, ...sortedItems] : sortedItems;
                }
            }
        });

        unsubscribeWatchEvents = fileSystemWatchEvents.subscribe(event => {
            if (event && event.consoleId === consoleId && isWatching && event.data.path === currentPath) {
                requestPath(currentPath);
            }
        });

        // If we are created with a consoleId, request the path immediately.
        // If we are restored (with consoleConnection), the reactive block will handle it.
        if (consoleId) {
            requestPath(currentPath);
        }
    });

    onDestroy(() => {
        if (isWatching) {
            sendWatchRequest('fs_watch_stop', currentPath);
        }
        if (unsubscribeResponses) unsubscribeResponses();
        if (unsubscribeWatchEvents) unsubscribeWatchEvents();
    });
</script>

<style>
    .explorer-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-size: 14px;
        user-select: none;
    }
    .path-bar {
        padding: 4px 8px;
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
        white-space: nowrap;
        overflow-x: auto;
        flex-shrink: 0; /* Prevents the path bar from shrinking */
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .path-bar .path-text {
        flex-grow: 1;
        overflow-x: hidden;
        text-overflow: ellipsis;
    }
    .controls-group {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-shrink: 0;
        margin-left: 10px;
    }
    .view-mode-selector, .color-mode-selector {
        display: flex;
        background: var(--taskbar-button-bg);
        border-radius: 3px;
        border: 1px solid var(--border-color);
        overflow: hidden;
    }
    .color-mode-selector {
        padding: 2px 5px;
        gap: 8px;
        font-size: 12px;
    }
    .color-mode-selector label {
        display: flex;
        align-items: center;
        gap: 3px;
        cursor: pointer;
    }
    .view-button {
        background: transparent;
        border: none;
        border-left: 1px solid var(--border-color);
        color: var(--taskbar-text);
        padding: 2px 8px;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
    }
    .view-button:first-child {
        border-left: none;
    }
    .view-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .view-button.active {
        background-color: var(--taskbar-button-hover-bg);
        color: #3498db;
    }
    .watch-button {
        background: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--taskbar-text);
        padding: 2px 8px;
        border-radius: 3px;
        cursor: pointer;
        flex-shrink: 0;
    }
    .watch-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .watch-button.active {
        background-color: var(--taskbar-button-hover-bg);
        border-color: #2980b9;
        color: #3498db;
    }
    .error-message {
        color: #e74c3c;
        padding: 8px;
        flex-shrink: 0; /* Prevents the error message from shrinking */
    }
    .item-list {
        flex-grow: 1;
        overflow-y: auto;
        padding: 4px;
    }
    .item {
        display: flex;
        padding: 2px 8px;
        cursor: pointer;
        border-radius: 2px;
    }
    .item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .item-icon {
        width: 25px;
        flex-shrink: 0;
    }
    .item-name {
        flex-grow: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .item-size {
        width: 80px;
        text-align: right;
        flex-shrink: 0;
        color: #7f8c8d;
    }

    /* Tile View Styles */
    .tile-grid {
        flex-grow: 1;
        overflow-y: auto;
        padding: 8px;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 8px;
    }
    .tile-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
        text-align: center;
        color: white;
        word-break: break-word;
        aspect-ratio: 1 / 1;
        transition: transform 0.1s ease-in-out, box-shadow 0.1s ease-in-out;
    }
    .tile-item:hover {
        transform: scale(1.05);
        box-shadow: 0 0 10px rgba(0,0,0,0.5);
        z-index: 10;
    }
    .tile-icon {
        font-size: 2.5em;
        line-height: 1;
    }
    .tile-name {
        font-size: 12px;
        margin-top: 5px;
        max-height: 2.6em; /* approx 2 lines */
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }


    /* Styles for settings modal (borrowed from IoskConsole) */
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .modal-content label { display: flex; align-items: center; gap: 8px; }
    .modal-content input[type="text"] { background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 8px; border-radius: 3px; font-family: monospace; width: 100%; box-sizing: border-box; }
    .path-input-container { padding-left: 20px; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding-left: 20px; }
    .form-grid label { display: flex; align-items: center; gap: 5px; }
    .form-grid input { width: 80px; }
    .radio-group label { display: inline-flex; align-items: center; gap: 5px; margin-right: 15px; }
</style>

<div class="explorer-container">
    <div class="path-bar">
        <span class="path-text">{currentPath}</span>
        <div class="controls-group">
            {#if viewMode === 'tiles'}
                <div class="color-mode-selector">
                    <label title="Color by file type">
                        <input type="radio" bind:group={colorMode} value={'type'}> Type
                    </label>
                    <label title="Color by modification time">
                        <input type="radio" bind:group={colorMode} value={'age'}> Age
                    </label>
                </div>
            {/if}
            <div class="view-mode-selector">
                <button class="view-button" class:active={viewMode === 'list'} on:click={() => viewMode = 'list'} title="List View">☰</button>
                <button class="view-button" class:active={viewMode === 'tiles'} on:click={() => viewMode = 'tiles'} title="Tiles View">⊞</button>
            </div>
            <button class="watch-button" class:active={isWatching} on:click={toggleWatch} title="Watch for live updates">
                {isWatching ? 'Watching' : 'Watch'} 👀
            </button>
        </div>
    </div>
    {#if errorMessage}
        <div class="error-message">{errorMessage}</div>
    {/if}

    {#if viewMode === 'list'}
        <div class="item-list">
            {#each items as item (item.name)}
                <div class="item" on:click={() => handleItemClick(item)} title={item.name}>
                    <span class="item-icon">{item.type === 'dir' ? '🗂️' : '📄'}</span>
                    <span class="item-name">{item.name}</span>
                    <span class="item-size">
                        {#if item.type === 'file' && item.size >= 0}
                            {item.size}
                        {/if}
                    </span>
                </div>
            {/each}
        </div>
    {:else if viewMode === 'tiles'}
        <div class="tile-grid">
             {#each items as item (item.name)}
                <div class="tile-item"
                     on:click={() => handleItemClick(item)}
                     title={item.name}
                     style:background-color={getTileColor(item, colorMode)}
                >
                    <div class="tile-icon">{item.type === 'dir' ? '🗂️' : '📄'}</div>
                    <div class="tile-name">{item.name}</div>
                </div>
            {/each}
        </div>
    {/if}

    <!-- Settings Modal Markup -->
    {#if showSettings}
        <div class="modal-overlay" on:click|self={handleCancelSettings}>
            <div class="modal-content" on:keydown|stopPropagation on:keyup|stopPropagation on:keypress|stopPropagation>
                <h3>File Explorer Settings</h3>
                <fieldset>
                    <legend>Initial Directory</legend>
                    <label>
                        <input type="radio" bind:group={settingsModel.usePwd} value={true}>
                        Current working directory (.)
                    </label>
                    <label>
                        <input type="radio" bind:group={settingsModel.usePwd} value={false}>
                        Specific path
                    </label>
                    {#if !settingsModel.usePwd}
                    <div class="path-input-container">
                        <input type="text" bind:value={settingsModel.path} placeholder="e.g., /home/user">
                    </div>
                    {/if}
                </fieldset>

                <fieldset>
                    <legend>Default Window Position & Size</legend>
                    <div class="radio-group">
                        <label><input type="radio" bind:group={windowSettingsForModal.positioning} value="auto"> Auto</label>
                        <label><input type="radio" bind:group={windowSettingsForModal.positioning} value="manual"> Manual</label>
                    </div>
                    {#if windowSettingsForModal.positioning === 'manual'}
                        <div class="form-grid">
                            <label>X: <input type="number" bind:value={windowSettingsForModal.x}></label>
                            <label>Y: <input type="number" bind:value={windowSettingsForModal.y}></label>
                            <label>Width: <input type="number" bind:value={windowSettingsForModal.width}></label>
                            <label>Height: <input type="number" bind:value={windowSettingsForModal.height}></label>
                        </div>
                    {/if}
                </fieldset>

                <fieldset>
                    <legend>Appearance</legend>
                    <div class="form-grid">
                         <label style="grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center;">
                            <span>Default Zoom</span>
                            <input type="number" bind:value={windowSettingsForModal.defaultZoom} min="0.5" max="3" step="0.1" style="width: 80px;">
                        </label>
                    </div>
                </fieldset>

                <div class="buttons">
                    <button on:click={handleCancelSettings}>Cancel</button>
                    <button class="save-button" on:click={handleSaveSettings}>Save Default</button>
                </div>
            </div>
        </div>
    {/if}
</div>