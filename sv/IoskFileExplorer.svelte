<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, createEventDispatcher } from 'svelte';
    import { get } from 'svelte/store';
    import { fileSystemRequests, fileSystemResponses, fileSystemWatchEvents } from './ioskEvents.js';
    import { newIoskFileViewer, windows } from './windows.js';
    import { windowSettings } from './desktopStore.js';

    // --- Component Props & State ---
    export let id; // Window ID, passed from Window.svelte
    export let groupId;
    export let consoleId;
    export let initialPath = '.';
    export let componentName;
    export let x, y, width, height;
    export let consoleConnection = null; // Passed during Dash restore

    // --- Recursive Rendering Props (for <svelte:self>) ---
    export let treeNode = null;
    export let treeLevel = 0;
    // Pass down reactive props needed by the recursive part
    export { viewMode, colorMode, getTileColor, handleItemClick, expandedNodes, toggleNode };


    let currentPath = (initialPath && initialPath !== '.') ? initialPath : '/';
    let items = []; // Flat list: { name, type, size, mtime, path? }
    let errorMessage = '';
    let unsubscribeResponses;

    // --- State for Watch feature ---
    let isWatching = false;
    let unsubscribeWatchEvents;
    let previousItemsMap = new Map();
    let itemChangeStatus = {}; // { [itemName]: 'new' | 'modified' | 'removed' }
    let changeClearTimeout;

    // --- View State ---
    let viewMode = 'list'; // 'list' or 'tiles'
    let colorMode = 'type'; // 'type' or 'age'
    let nestedView = false; // 'nested' or 'flat'
    let treeItems = []; // Hierarchical data for nested views
    let expandedNodes = new Set(); // Stores paths of expanded dirs in nested view

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsModel = { usePwd: true, path: '/' };
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };
    
    const dispatch = createEventDispatcher();

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

    // --- Nested View Logic ---
    function toggleNestedView() {
        // Disable watch mode when entering nested view, as it's not compatible
        if (isWatching) {
            toggleWatch();
        }
        nestedView = !nestedView;
        items = [];
        treeItems = [];
        expandedNodes.clear();
        expandedNodes = expandedNodes;
        requestPath(currentPath);
    }

    function toggleNode(path) {
        if (expandedNodes.has(path)) {
            expandedNodes.delete(path);
        } else {
            expandedNodes.add(path);
        }
        expandedNodes = expandedNodes; // Trigger Svelte reactivity
    }

    function buildTree(flatList, basePath) {
        if (!flatList || flatList.length === 0) return [];
        
        const map = new Map();
        flatList.forEach(item => map.set(item.path, { ...item, children: [] }));

        const roots = [];
        flatList.forEach(item => {
            const node = map.get(item.path);
            const lastSlash = item.path.lastIndexOf('/');
            let parentPath = null;

            if (lastSlash > 0) { // e.g., /foo/bar -> /foo
                parentPath = item.path.substring(0, lastSlash);
            } else if (lastSlash === 0 && item.path.length > 1) { // e.g., /foo -> /
                parentPath = '/';
            }

            if (parentPath === basePath) {
                roots.push(node);
            } else if (parentPath && map.has(parentPath)) {
                map.get(parentPath).children.push(node);
            }
        });

        const sortRecursive = (nodes) => {
            nodes.sort((a, b) => {
                if (a.type === b.type) return a.name.localeCompare(b.name);
                return a.type === 'dir' ? -1 : 1;
            });
            nodes.forEach(node => {
                if (node.children.length > 0) sortRecursive(node.children);
            });
        };
        sortRecursive(roots);
        return roots;
    }

    $: if (nestedView) {
        treeItems = buildTree(items, currentPath);
    }
    
    // --- Data Fetching & Watch ---
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
            previousItemsMap.clear();
            itemChangeStatus = {};
            clearTimeout(changeClearTimeout);
        }
    }

    function requestPath(path) {
        errorMessage = '';
        if (!consoleId) {
            items = [];
            return false;
        }
        const request = {
            consoleId,
            requesterId: id,
            command: {
                type: 'fs_list',
                path,
                recursive: nestedView // Request recursive listing if in nested view
            }
        };
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
        return true;
    }

    function handleItemClick(item) {
        if (itemChangeStatus[item.name] === 'removed' && !nestedView) return;

        if (item.type === 'dir' && !nestedView) {
            if (isWatching) {
                sendWatchRequest('fs_watch_stop', currentPath);
                isWatching = false;
            }
            previousItemsMap.clear();
            itemChangeStatus = {};
            clearTimeout(changeClearTimeout);

            let newPath;
            if (item.name === '..') {
                if (currentPath === '/') return;
                newPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
            } else {
                newPath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
            }
            requestPath(newPath);
        } else if (item.type === 'file') {
            const filePath = item.path || (currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`);
            newIoskFileViewer(consoleId, filePath);
        }
    }

    onMount(() => {
        unsubscribeResponses = fileSystemResponses.subscribe(response => {
            if (response && response.requesterId === id && response.data.type === 'fs_list_response') {
                const { path, listing, error } = response.data;

                if (error) {
                    errorMessage = error;
                    items = [];
                    previousItemsMap.clear();
                } else if (listing) {
                    let finalListing = [...listing];

                    if (isWatching && previousItemsMap.size > 0) {
                        const newItemsMap = new Map(listing.map(item => [item.name, item]));
                        const newChangeStatus = {};
                        newItemsMap.forEach((newItem, name) => {
                            if (!previousItemsMap.has(name)) newChangeStatus[name] = 'new';
                            else {
                                const oldItem = previousItemsMap.get(name);
                                if (newItem.mtime !== oldItem.mtime || newItem.size !== oldItem.size) newChangeStatus[name] = 'modified';
                            }
                        });
                        previousItemsMap.forEach((oldItem, name) => {
                            if (name !== '..' && !newItemsMap.has(name)) {
                                newChangeStatus[name] = 'removed';
                                finalListing.push(oldItem);
                            }
                        });
                        delete newChangeStatus['..'];
                        if (Object.keys(newChangeStatus).length > 0) {
                           itemChangeStatus = { ...itemChangeStatus, ...newChangeStatus };
                           clearTimeout(changeClearTimeout);
                           changeClearTimeout = setTimeout(() => {
                               items = items.filter(item => itemChangeStatus[item.name] !== 'removed');
                               itemChangeStatus = {};
                           }, 1500);
                        }
                    }
                    previousItemsMap = new Map(listing.map(item => [item.name, item]));
                    currentPath = path;

                    if (!nestedView) {
                        const parentDir = { name: '..', type: 'dir', size: -1, mtime: -1 };
                        const sortedItems = finalListing.sort((a, b) => {
                            if (a.type === b.type) return a.name.localeCompare(b.name);
                            return a.type === 'dir' ? -1 : 1;
                        });
                        items = (path !== '/') ? [parentDir, ...sortedItems] : sortedItems;
                    } else {
                        items = finalListing; // For nested view, store flat list for tree processing
                    }
                }
            }
        });

        unsubscribeWatchEvents = fileSystemWatchEvents.subscribe(event => {
            if (event && event.consoleId === consoleId && isWatching && event.data.path === currentPath) {
                requestPath(currentPath);
            }
        });

        if (consoleId) {
            requestPath(currentPath);
        }
    });

    onDestroy(() => {
        if (isWatching) sendWatchRequest('fs_watch_stop', currentPath);
        if (unsubscribeResponses) unsubscribeResponses();
        if (unsubscribeWatchEvents) unsubscribeWatchEvents();
        clearTimeout(changeClearTimeout);
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
    .watch-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
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

    /* Tree View (Nested List) Styles */
    .tree-node-expander {
        width: 15px;
        text-align: center;
        flex-shrink: 0;
    }
    .tree-item {
        padding-left: calc(8px + var(--level) * 20px);
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

    /* Nested Tile View Styles */
    .nested-tile {
        justify-content: flex-start;
        font-size: calc(1em - var(--level, 0) * 0.08em);
        overflow: hidden;
    }
    .nested-tile .tile-icon {
        font-size: calc(2.5em - var(--level, 0) * 0.5em);
    }
    .nested-tile-children {
        width: 100%;
        flex-grow: 1;
        margin-top: 5px;
        padding: 5px;
        background-color: rgba(0,0,0,0.15);
        border-radius: 4px;
        display: grid;
        gap: 4px;
        grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
        overflow-y: auto;
    }

    /* --- Animation styles for Watch updates --- */
    @keyframes green-pop-tile {
        0% { transform: scale(0.5); opacity: 0; box-shadow: 0 0 30px 10px rgba(39, 174, 96, 0.9); }
        50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 15px 5px rgba(39, 174, 96, 0.6); }
        100% { transform: scale(1); opacity: 1; box-shadow: none; }
    }
    @keyframes blue-pulse-tile {
        0% { transform: scale(1); box-shadow: none; }
        25% { transform: scale(1.05); box-shadow: 0 0 25px 8px rgba(41, 128, 185, 0.8); }
        50% { transform: scale(0.95); box-shadow: none; }
        75% { transform: scale(1.05); box-shadow: 0 0 25px 8px rgba(41, 128, 185, 0.8); }
        100% { transform: scale(1); box-shadow: none; }
    }
    @keyframes red-implode-tile {
        from { transform: scale(1) rotate(0deg); opacity: 1; box-shadow: 0 0 20px 5px rgba(231, 76, 60, 0.8); }
        to { transform: scale(0) rotate(90deg); opacity: 0; box-shadow: none; }
    }

    .tile-item.new { animation: green-pop-tile 1.2s ease-out; }
    .tile-item.modified { animation: blue-pulse-tile 1.2s ease-in-out; }
    .tile-item.removed {
        animation: red-implode-tile 1s ease-in forwards;
        pointer-events: none;
    }

    @keyframes green-flash-list {
        from { background-color: rgba(39, 174, 96, 0.4); }
        to { background-color: transparent; }
    }
    @keyframes blue-flash-list {
        from { background-color: rgba(41, 128, 185, 0.4); }
        to { background-color: transparent; }
    }
    @keyframes red-flash-list {
        from { background-color: rgba(231, 76, 60, 0.5); opacity: 1; }
        to { background-color: rgba(231, 76, 60, 0); transform: translateX(-30px); opacity: 0; }
    }
    .item.new { animation: green-flash-list 1.5s ease-out; }
    .item.modified { animation: blue-flash-list 1.5s ease-out; }
    .item.removed {
        animation: red-flash-list 1s ease-out forwards;
        pointer-events: none;
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

{#if !treeNode}
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
             <button class="watch-button" class:active={nestedView} on:click={toggleNestedView} title="Toggle Nested View">Nested</button>
            <button class="watch-button" class:active={isWatching} on:click={toggleWatch} title="Watch for live updates" disabled={nestedView}>
                {isWatching ? 'Watching' : 'Watch'} 👀
            </button>
        </div>
    </div>
    {#if errorMessage}
        <div class="error-message">{errorMessage}</div>
    {/if}

    {#if viewMode === 'list'}
        <div class="item-list">
            {#if nestedView}
                {#each treeItems as item (item.path)}
                    <svelte:self {item} treeNode={item} treeLevel={0} bind:expandedNodes />
                {/each}
            {:else}
                {#each items as item (item.name)}
                    <div class="item" 
                         on:click={() => handleItemClick(item)} 
                         title={item.name}
                         class:new={itemChangeStatus[item.name] === 'new'}
                         class:modified={itemChangeStatus[item.name] === 'modified'}
                         class:removed={itemChangeStatus[item.name] === 'removed'}>
                        <span class="item-icon">{item.type === 'dir' ? '🗂️' : '📄'}</span>
                        <span class="item-name">{item.name}</span>
                        <span class="item-size">
                            {#if item.type === 'file' && item.size >= 0}
                                {item.size}
                            {/if}
                        </span>
                    </div>
                {/each}
            {/if}
        </div>
    {:else if viewMode === 'tiles'}
        <div class="tile-grid">
             {#if nestedView}
                {#each treeItems as item (item.path)}
                    <svelte:self {item} treeNode={item} treeLevel={0} bind:expandedNodes />
                {/each}
             {:else}
                 {#each items as item (item.name)}
                    <div class="tile-item"
                         on:click={() => handleItemClick(item)}
                         title={item.name}
                         style:background-color={getTileColor(item, colorMode)}
                         class:new={itemChangeStatus[item.name] === 'new'}
                         class:modified={itemChangeStatus[item.name] === 'modified'}
                         class:removed={itemChangeStatus[item.name] === 'removed'}>
                        <div class="tile-icon">{item.type === 'dir' ? '🗂️' : '📄'}</div>
                        <div class="tile-name">{item.name}</div>
                    </div>
                {/each}
             {/if}
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
{:else}
    <!-- RECURSIVE TEMPLATE for Nested Views -->
    {#if viewMode === 'list'}
        <div class="tree-node-container" style="--level: {treeLevel}">
            <div class="item tree-item" on:click={() => treeNode.type === 'dir' ? toggleNode(treeNode.path) : handleItemClick(treeNode)}>
                <span class="tree-node-expander">
                    {#if treeNode.type === 'dir' && treeNode.children.length > 0}
                        {expandedNodes.has(treeNode.path) ? '▼' : '►'}
                    {/if}
                </span>
                <span class="item-icon">{treeNode.type === 'dir' ? '🗂️' : '📄'}</span>
                <span class="item-name">{treeNode.name}</span>
                 <span class="item-size">
                    {#if treeNode.type === 'file' && treeNode.size >= 0}
                        {treeNode.size}
                    {/if}
                </span>
            </div>
            {#if treeNode.children && treeNode.children.length > 0 && expandedNodes.has(treeNode.path)}
                {#each treeNode.children as child (child.path)}
                    <svelte:self item={child} treeNode={child} treeLevel={treeLevel + 1} bind:expandedNodes />
                {/each}
            {/if}
        </div>
    {:else} <!-- Nested Tile View -->
        <div class="tile-item nested-tile"
             style:background-color={getTileColor(treeNode, colorMode)}
             style="--level: {treeLevel}"
             on:click={() => treeNode.type === 'dir' ? toggleNode(treeNode.path) : handleItemClick(treeNode)}
             title={treeNode.name}>
             
            <div class="tile-icon">{treeNode.type === 'dir' ? '🗂️' : '📄'}</div>
            <div class="tile-name">{treeNode.name}</div>
            
            {#if treeNode.children && treeNode.children.length > 0 && expandedNodes.has(treeNode.path)}
                <div class="nested-tile-children">
                     {#each treeNode.children as child (child.path)}
                        <svelte:self item={child} treeNode={child} treeLevel={treeLevel + 1} bind:expandedNodes />
                    {/each}
                </div>
            {/if}
        </div>
    {/if}
{/if}