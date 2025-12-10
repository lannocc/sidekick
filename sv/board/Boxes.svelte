<!-- sv/board/Boxes.svelte -->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { 
        boxes, 
        updateBox, 
        deleteBox,
        connectionStatus,
        getShortcuts,
        getBackedWindows,
        getDesktopSettings,
        shortcutListResponse,
        backedWindowListResponse,
        desktopSettingsResponse
    } from '../bridge.js';
    import { currentBoxId } from '../desktop.js';
    import { newBox as createNewBoxEntity } from '../windows.js';

    let selectedBoxId = null;
    let selectedBox = null;
    let nameInput = '';
    let activeTab = 'general';

    // --- State for selected box details ---
    let selectedBoxShortcuts = [];
    let selectedBoxBackedWindows = [];
    let selectedBoxSettings = {};

    // --- State for resizable panel ---
    let leftPanelWidth = 220;
    let isResizing = false;

    // --- State and logic for tree view ---
    let boxTree = [];
    let flatBoxList = [];
    let expanded = { 0: true }; // Root is expanded by default

    function toggleExpand(boxId) {
        expanded[boxId] = !expanded[boxId];
    }

    // When selectedBoxId changes, request its details
    $: if (selectedBoxId !== null && $connectionStatus === 'connected') {
        getShortcuts(selectedBoxId);
        getBackedWindows(selectedBoxId);
        getDesktopSettings(selectedBoxId);
    }

    // Listen to responses and update local state if it's for our selected box
    $: if ($shortcutListResponse && $shortcutListResponse.box_id === selectedBoxId) {
        selectedBoxShortcuts = $shortcutListResponse.shortcuts || [];
    }
    $: if ($backedWindowListResponse && $backedWindowListResponse.box_id === selectedBoxId) {
        selectedBoxBackedWindows = $backedWindowListResponse.windows || [];
    }
    $: if ($desktopSettingsResponse && $desktopSettingsResponse.box_id === selectedBoxId) {
        selectedBoxSettings = $desktopSettingsResponse.settings || {};
    }

    // Rebuild the tree structure when the source box list changes
    $: if ($boxes && $boxes.length > 0) {
        const buildTree = (parentId) => {
            return $boxes
                .filter(box => box.parent_box_id === parentId)
                .map(box => ({
                    ...box,
                    children: buildTree(box.id)
                }))
                .sort((a, b) => a.name.localeCompare(b.name));
        };

        const mainDesktop = $boxes.find(b => b.id === 0);
        if (mainDesktop) {
            boxTree = [{
                ...mainDesktop,
                children: buildTree(0)
            }];
        } else {
            boxTree = [];
        }
    }

    // Flatten the tree for rendering, respecting expanded state
    $: {
        const flatten = (nodes, level = 0) => {
            let result = [];
            for (const node of nodes) {
                result.push({ ...node, level });
                if (node.children && node.children.length > 0 && expanded[node.id]) {
                    result.push(...flatten(node.children, level + 1));
                }
            }
            return result;
        }
        flatBoxList = flatten(boxTree);
    }

    // When boxes store updates, update the selected box object
    $: if ($boxes && selectedBoxId !== null) {
        selectedBox = $boxes.find(b => b.id === selectedBoxId);
        if (selectedBox) {
            nameInput = selectedBox.name;
        } else {
            // If the selected box was deleted, fall back to the main desktop or the first available box
            selectedBoxId = $boxes.find(b => b.id === 0) ? 0 : ($boxes.length > 0 ? $boxes[0].id : null);
        }
    }

    // Initialize selection on mount
    onMount(() => {
        if ($boxes.length > 0 && selectedBoxId === null) {
            selectedBoxId = 0;
        }
    });

    function handleSelectBox(id) {
        if (selectedBoxId !== id) {
            activeTab = 'general';
            // Clear old data to prevent flicker
            selectedBoxShortcuts = [];
            selectedBoxBackedWindows = [];
            selectedBoxSettings = {};
        }
        selectedBoxId = id;
    }

    function handleNameUpdate() {
        if (selectedBox && nameInput && nameInput.trim() !== selectedBox.name) {
            updateBox(selectedBox.id, nameInput.trim());
        }
    }

    function handleDeleteSelectedBox() {
        if (!selectedBox || selectedBox.id === 0) return;
        if (confirm(`Are you sure you want to delete the box "${selectedBox.name}"? This cannot be undone.`)) {
            deleteBox(selectedBox.id);
        }
    }

    function handleNewBox(event) {
        const name = prompt("Enter a name for the new Box:", "My Project Box");
        if (!name) return;

        const context = prompt("Enter the local filesystem path for the Box:", "/home/user/project");
        if (!context) return;
        
        // Create new boxes inside the currently selected box.
        const parent_box_id = selectedBoxId ?? 0;
        createNewBoxEntity({ name, context, sourceEvent: event, parent_box_id });
    }

    // --- Resizer logic ---
    function onMouseDown(event) {
        isResizing = true;
    }
    
    function onMouseMove(event) {
        if (isResizing) {
            leftPanelWidth += event.movementX;
            if (leftPanelWidth < 150) leftPanelWidth = 150; // Min width
            if (leftPanelWidth > 600) leftPanelWidth = 600; // Max width
        }
    }

    function onMouseUp() {
        isResizing = false;
    }

    onMount(() => {
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    });

    onDestroy(() => {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
    });
</script>

<style>
    .boxes-container {
        display: flex;
        height: 100%;
        background-color: transparent;
        color: var(--text-color);
        position: relative;
    }
    .boxes-container.resizing {
        cursor: col-resize;
        user-select: none;
    }
    .left-panel {
        width: 200px; /* Default, will be overridden by style prop */
        min-width: 150px;
        max-width: 600px;
        border-right: 1px solid var(--border-color);
        display: flex;
        flex-direction: column;
        overflow-y: auto;
        background-color: hsla(0, 0%, 50%, 0.15);
        border-radius: 8px 0 0 8px;
        flex-shrink: 0;
    }
    .resizer {
        width: 5px;
        cursor: col-resize;
        background: transparent;
        flex-shrink: 0;
        position: relative;
    }
    .resizer:hover, .boxes-container.resizing .resizer {
        background-color: var(--item-selected-bg);
    }

    .box-list-item {
        display: flex;
        align-items: center;
        padding: 8px 8px 8px 0; /* Adjusted padding */
        cursor: pointer;
        border-bottom: 1px solid var(--border-color-light);
        gap: 8px;
        flex-shrink: 0;
        border-left: 3px solid transparent;
    }
    .box-list-item:hover {
        background-color: var(--item-hover-bg);
    }
    .box-list-item.selected {
        background-color: var(--item-selected-bg);
    }
    .box-list-item.current { /* Style for the active desktop box */
        border-left-color: var(--accent-color, #88C0D0);
    }

    .tree-toggle, .tree-toggle-placeholder {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: none;
        border: none;
        color: var(--text-color-light);
        font-family: monospace;
        font-size: 14px;
        cursor: pointer;
    }
    .tree-toggle:hover {
        color: var(--text-color);
    }
    .box-icon {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
    }
    .box-name {
        flex-grow: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .right-panel {
        flex-grow: 1;
        padding: 16px;
        padding-top: 64px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        overflow-y: auto;
        position: relative; /* For child positioning */
    }
    .details-group {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .details-group label {
        font-size: 0.9em;
        color: var(--text-color-light);
    }
    .details-group input {
        padding: 8px;
        background-color: var(--input-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        color: var(--text-color);
        font-size: 1em;
    }
    .details-group span {
        padding: 8px;
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        color: var(--text-color-light);
        font-size: 1em;
        font-family: monospace;
        word-break: break-all;
    }

    /* --- Buttons --- */
    .new-box-btn {
        position: absolute;
        top: 12px;
        right: 12px;
        width: 40px;
        height: 40px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--button-bg);
        border: 1px solid var(--button-border-color);
        border-radius: 8px;
        cursor: pointer;
        z-index: 10;
    }
    .new-box-btn:hover {
        background-color: var(--button-hover-bg);
    }
    .new-box-icon {
        width: 24px;
        height: 24px;
        opacity: 0.9;
    }
    .plus-badge {
        position: absolute;
        bottom: -2px;
        right: -2px;
        background-color: #27ae60;
        color: white;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        font-size: 14px;
        font-weight: bold;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid var(--window-bg);
    }
    .delete-box-btn {
        position: absolute;
        top: 12px;
        left: 12px;
        padding: 8px 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        background-color: #c0392b;
        color: white;
        border: 1px solid #e74c3c;
        border-radius: 8px;
        cursor: pointer;
        z-index: 10;
        font-weight: bold;
    }
    .delete-box-btn:hover {
        background-color: #e74c3c;
    }

    .no-selection {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: var(--text-color-light);
        font-style: italic;
    }

    /* --- Tab Styles --- */
    .tabs {
        display: flex;
        border-bottom: 1px solid var(--border-color);
    }
    .tab-btn {
        padding: 8px 16px;
        cursor: pointer;
        background: none;
        border: none;
        color: var(--text-color-light);
        border-bottom: 2px solid transparent;
        margin-bottom: -1px; /* Aligns with the container's border */
        font-size: 0.95em;
        transition: color 0.2s ease, border-color 0.2s ease;
    }
    .tab-btn:hover {
        color: var(--text-color);
    }
    .tab-btn.active {
        color: var(--accent-color, #88C0D0);
        border-bottom-color: var(--accent-color, #88C0D0);
        font-weight: bold;
    }
    .tab-content {
        flex-grow: 1;
        overflow-y: auto;
    }
    .tab-pane {
        padding-top: 16px;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    .tab-pane-placeholder {
        padding: 16px;
        color: var(--text-color-light);
        font-style: italic;
        text-align: center;
    }
    .disconnected-overlay {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        gap: 8px;
        color: var(--text-color-light);
        background-color: hsla(0, 0%, 20%, 0.5);
        font-size: 1.5em;
        font-weight: bold;
        border-radius: 8px;
    }
    .details-list {
        list-style-type: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .details-list li {
        background-color: var(--input-bg);
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--border-color);
        font-family: monospace;
        font-size: 0.9em;
        word-break: break-all;
    }
    .details-list li strong {
        color: var(--text-color);
    }
    .details-list li pre {
        margin-top: 4px;
        padding: 4px;
        background-color: rgba(0,0,0,0.2);
        border-radius: 4px;
        white-space: pre-wrap;
    }
</style>

{#if $connectionStatus === 'connected'}
<div class="boxes-container" class:resizing={isResizing}>
    <button class="new-box-btn" on:click={handleNewBox} title="New Box">
        <img src="/skybox.png" alt="Box" class="new-box-icon" />
        <span class="plus-badge">+</span>
    </button>
    
    <div class="left-panel" style:width="{leftPanelWidth}px">
        {#each flatBoxList as box (box.id)}
            <div 
                class="box-list-item" 
                class:selected={box.id === selectedBoxId}
                class:current={box.id === $currentBoxId}
                on:click={() => handleSelectBox(box.id)}
                title={box.name}
                style:padding-left="{box.level * 20 + 8}px"
            >
                {#if box.children && box.children.length > 0}
                    <button class="tree-toggle" on:click|stopPropagation={() => toggleExpand(box.id)}>
                        {expanded[box.id] ? '▼' : '►'}
                    </button>
                {:else}
                    <div class="tree-toggle-placeholder"></div>
                {/if}

                <img src="/skybox.png" alt="Box" class="box-icon" />
                <span class="box-name">{box.name}</span>
            </div>
        {/each}
    </div>

    <div class="resizer" on:mousedown={onMouseDown}></div>

    <div class="right-panel">
        {#if selectedBox && selectedBox.id !== 0}
            <button class="delete-box-btn" on:click={handleDeleteSelectedBox} title="Delete Selected Box">
                Delete Box
            </button>
        {/if}

        {#if selectedBox}
            <div class="details-group">
                <label for="box-name-input">Name</label>
                <input id="box-name-input" type="text" bind:value={nameInput} on:blur={handleNameUpdate} disabled={selectedBox.id === 0} />
            </div>

            <div class="tabs">
                <button class="tab-btn" class:active={activeTab === 'general'} on:click={() => activeTab = 'general'}>General</button>
                <button class="tab-btn" class:active={activeTab === 'shortcuts'} on:click={() => activeTab = 'shortcuts'}>Shortcuts</button>
                <button class="tab-btn" class:active={activeTab === 'boards'} on:click={() => activeTab = 'boards'}>Back Boards</button>
                <button class="tab-btn" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>Settings</button>
            </div>

            <div class="tab-content">
                {#if activeTab === 'general'}
                    <div class="tab-pane">
                        <div class="details-group">
                            <label>ID</label>
                            <span>{selectedBox.id}</span>
                        </div>
                        <div class="details-group">
                            <label>Type</label>
                            <span>{selectedBox.type}</span>
                        </div>
                        <div class="details-group">
                            <label>Context Path</label>
                            <span>{selectedBox.context}</span>
                        </div>
                        <div class="details-group">
                            <label>Parent Box ID</label>
                            <span>{selectedBox.parent_box_id ?? 'N/A'}</span>
                        </div>
                    </div>
                {:else if activeTab === 'shortcuts'}
                    <div class="tab-pane">
                        {#if selectedBoxShortcuts.length > 0}
                            <ul class="details-list">
                                {#each selectedBoxShortcuts as shortcut}
                                    <li><strong>{shortcut.name}</strong> [{shortcut.type}] <br/> {shortcut.path}</li>
                                {/each}
                            </ul>
                        {:else}
                            <div class="tab-pane-placeholder">No shortcuts configured for this box.</div>
                        {/if}
                    </div>
                {:else if activeTab === 'boards'}
                    <div class="tab-pane">
                        {#if selectedBoxBackedWindows.length > 0}
                            <ul class="details-list">
                                {#each selectedBoxBackedWindows as board}
                                    <li>
                                        <strong>ID: {board.id}</strong><br/>
                                        Position: ({Math.round(board.x)}, {Math.round(board.y)}), Scale: {board.scale.toFixed(2)}<br/>
                                        Config: <pre>{JSON.stringify(board.config, null, 2)}</pre>
                                    </li>
                                {/each}
                            </ul>
                        {:else}
                            <div class="tab-pane-placeholder">No backed boards found for this box.</div>
                        {/if}
                    </div>
                {:else if activeTab === 'settings'}
                    <div class="tab-pane">
                         {#if Object.keys(selectedBoxSettings).length > 0}
                            <ul class="details-list">
                                {#each Object.entries(selectedBoxSettings) as [key, value]}
                                    <li><strong>{key}:</strong> {JSON.stringify(value)}</li>
                                {/each}
                            </ul>
                        {:else}
                            <div class="tab-pane-placeholder">No custom settings for this box. Using defaults.</div>
                        {/if}
                    </div>
                {/if}
            </div>

        {:else}
            <div class="no-selection">
                Select a box to see its details.
            </div>
        {/if}
    </div>
</div>
{:else}
    <div class="disconnected-overlay">
        <span>SKYBRIDGE REQUIRED</span>
        <span style="font-size: 0.7em; font-weight: normal; text-transform: capitalize;">
            Connection Status: {$connectionStatus}
        </span>
    </div>
{/if}