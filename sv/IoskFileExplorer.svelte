<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { fileSystemRequests, fileSystemResponses } from './ioskEvents.js';
    import { newIoskFileViewer, windows } from './windows.js';
    import { windowSettings } from './desktopStore.js';

    export let id; // Window ID, passed from Window.svelte
    export let consoleId;
    export let initialPath = '.';
    export let componentName;
    export let x, y, width, height;

    export let consoleConnection = null; // Passed during Dash restore

    let currentPath = (initialPath && initialPath !== '.') ? initialPath : '/';
    let items = []; // { name, type, size }
    let errorMessage = '';

    let unsubscribeResponses;

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsModel = { usePwd: true, path: '/' };
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };

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
    $: if (id !== undefined) {
        windows.updateWindowProps(id, { currentPath, consoleId });
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
            const compatibleConsole = $windows.find(w =>
                w.componentName === 'IoskConsole' &&
                w.isConsoleConnected &&
                w.consoleConnection &&
                w.consoleConnection.url === consoleConnection.url &&
                w.consoleConnection.user === consoleConnection.user
            );

            if (compatibleConsole) {
                // Found one!
                consoleId = compatibleConsole.id;
                requestPath(currentPath);
            } else {
                // Still no connection.
                errorMessage = 'No active IOSK connection available. Waiting for connection...';
                items = [];
            }
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
                    const parentDir = { name: '..', type: 'dir', size: -1 };
                    const sortedItems = listing.sort((a, b) => {
                        if (a.type === b.type) return a.name.localeCompare(b.name);
                        return a.type === 'dir' ? -1 : 1; // Directories first
                    });
                    items = (path !== '/') ? [parentDir, ...sortedItems] : sortedItems;
                }
            }
        });

        // If we are created with a consoleId, request the path immediately.
        // If we are restored (with consoleConnection), the reactive block will handle it.
        if (consoleId) {
            requestPath(currentPath);
        }
    });

    onDestroy(() => {
        if (unsubscribeResponses) unsubscribeResponses();
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
        <span>{currentPath}</span>
    </div>
    {#if errorMessage}
        <div class="error-message">{errorMessage}</div>
    {/if}
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

                <div class="buttons">
                    <button on:click={handleCancelSettings}>Cancel</button>
                    <button class="save-button" on:click={handleSaveSettings}>Save Default</button>
                </div>
            </div>
        </div>
    {/if}
</div>