<script>
    import { onMount, onDestroy } from 'svelte';
    import { 
        boxes, 
        updateBox, 
        deleteBox,
        connectionStatus,
        getShortcuts,
        getBackedWindows,
        getBoxSpecificSettings,
        shortcutListResponse,
        backedWindowListResponse,
        specificSettingsResponse,
        // ProcBox imports
        getIoskConfig,
        updateIoskConfig,
        startIosk,
        stopProcess,
        ioskConfigResponse,
        runningProcesses
    } from '../bridge.js';
    import { currentBoxId } from '../desktop.js';
    import { newBox as createNewBoxEntity } from '../windows.js';

    let selectedBoxId = null;
    let selectedBox = null;
    let nameInput = '';
    let activeTab = 'properties';

    // --- State for selected box details ---
    let selectedBoxShortcuts = [];
    let selectedBoxBackedWindows = [];
    let selectedBoxSettings = {};
    
    // --- State for IOSK tab ---
    let ioskConfig = null;
    let latestProcess = null; // Most recent process record for the box
    let activeProcess = null; // The process if it's currently running or paused
    let uptime = 'N/A';
    let uptimeInterval;
    let configDebounceTimer;

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
        getBoxSpecificSettings(selectedBoxId);
        const box = $boxes.find(b => b.id === selectedBoxId);
        if (box && box.type === 'iosk') {
            getIoskConfig(selectedBoxId);
        }
    }

    // Listen to responses and update local state
    $: if ($shortcutListResponse && $shortcutListResponse.box_id === selectedBoxId) {
        selectedBoxShortcuts = $shortcutListResponse.shortcuts || [];
    }
    $: if ($backedWindowListResponse && $backedWindowListResponse.box_id === selectedBoxId) {
        selectedBoxBackedWindows = $backedWindowListResponse.windows || [];
    }
    $: if ($specificSettingsResponse && $specificSettingsResponse.box_id === selectedBoxId) {
        selectedBoxSettings = $specificSettingsResponse.settings || {};
    }
    $: if ($ioskConfigResponse && $ioskConfigResponse.box_id === selectedBoxId) {
        ioskConfig = $ioskConfigResponse.config || { mount_point: '', daemon_mode: 1, enable_stdin: 0 };
    }
    // Find the latest process record for the selected box
    $: if ($runningProcesses && selectedBoxId !== null) {
        latestProcess = $runningProcesses.find(p => p.box_id === selectedBoxId) || null;
    }
    // Determine if the process is "active" (i.e., can be interacted with)
    $: activeProcess = (latestProcess && (latestProcess.status === 'running' || latestProcess.status === 'paused')) ? latestProcess : null;


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
            boxTree = [{ ...mainDesktop, children: buildTree(0) }];
        } else {
            boxTree = [];
        }
    }

    // Flatten the tree for rendering
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

    // Update selected box object and tab state when boxes or selection changes
    $: if ($boxes && selectedBoxId !== null) {
        selectedBox = $boxes.find(b => b.id === selectedBoxId);
        if (selectedBox) {
            nameInput = selectedBox.name;
        } else {
            selectedBoxId = $boxes.find(b => b.id === 0) ? 0 : ($boxes.length > 0 ? $boxes[0].id : null);
        }
    }

    // Uptime calculation
    function formatUptime(startTime) {
        if (!startTime) return 'N/A';
        const start = new Date(startTime);
        const now = new Date();
        let seconds = Math.floor((now - start) / 1000);
        let minutes = Math.floor(seconds / 60);
        let hours = Math.floor(minutes / 60);
        let days = Math.floor(hours / 24);

        hours %= 24;
        minutes %= 60;
        seconds %= 60;

        return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    function calculateUptime() {
        if (activeProcess && activeProcess.status === 'running') {
            uptime = formatUptime(activeProcess.start_time);
        } else {
            uptime = 'N/A';
        }
    }

    // Reactive logic to manage the uptime timer interval
    $: {
        calculateUptime();
        if (activeProcess && activeProcess.status === 'running' && !uptimeInterval) {
            uptimeInterval = setInterval(calculateUptime, 1000);
        } else if ((!activeProcess || activeProcess.status !== 'running') && uptimeInterval) {
            clearInterval(uptimeInterval);
            uptimeInterval = null;
        }
    }

    // Initialize selection
    onMount(() => {
        if ($boxes.length > 0 && selectedBoxId === null) {
            selectedBoxId = 0;
        }
    });

    function handleSelectBox(id) {
        const justSelectedBox = $boxes.find(b => b.id === id);
        if (selectedBoxId !== id) {
            activeTab = (justSelectedBox && justSelectedBox.type === 'iosk') ? 'iosk' : 'properties';
            selectedBoxShortcuts = [];
            selectedBoxBackedWindows = [];
            selectedBoxSettings = {};
            ioskConfig = null;
            latestProcess = null;
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
        const parent_box_id = selectedBoxId ?? 0;
        createNewBoxEntity({ name, context, sourceEvent: event, parent_box_id });
    }
    
    function handleConfigChange() {
        clearTimeout(configDebounceTimer);
        configDebounceTimer = setTimeout(() => {
            if (!selectedBoxId || !ioskConfig) return;
            const configPayload = {
                mount_point: ioskConfig.mount_point,
                daemon_mode: ioskConfig.daemon_mode ? 1 : 0,
                enable_stdin: ioskConfig.enable_stdin ? 1 : 0,
            };
            updateIoskConfig(selectedBoxId, configPayload);
        }, 500);
    }

    // --- Resizer logic ---
    function onMouseDown(event) { isResizing = true; }
    function onMouseMove(event) {
        if (isResizing) {
            leftPanelWidth += event.movementX;
            if (leftPanelWidth < 150) leftPanelWidth = 150;
            if (leftPanelWidth > 600) leftPanelWidth = 600;
        }
    }
    function onMouseUp() { isResizing = false; }

    onMount(() => {
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    });

    onDestroy(() => {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        if (uptimeInterval) clearInterval(uptimeInterval);
        clearTimeout(configDebounceTimer);
    });
</script>

<style>
    .boxes-container { display: flex; height: 100%; background-color: transparent; color: var(--text-color); position: relative; }
    .boxes-container.resizing { cursor: col-resize; user-select: none; }
    .left-panel { width: 200px; min-width: 150px; max-width: 600px; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; overflow-y: auto; background-color: hsla(0, 0%, 50%, 0.15); border-radius: 8px 0 0 8px; flex-shrink: 0; }
    .resizer { width: 5px; cursor: col-resize; background: transparent; flex-shrink: 0; position: relative; }
    .resizer:hover, .boxes-container.resizing .resizer { background-color: var(--item-selected-bg); }
    .box-list-item { display: flex; align-items: center; padding: 8px 8px 8px 0; cursor: pointer; gap: 8px; flex-shrink: 0; border-left: 3px solid transparent; }
    .box-list-item:hover { background-color: var(--item-hover-bg); }
    .box-list-item.selected { font-weight: bold; background-color: var(--item-selected-bg); }
    .box-list-item.current { border-left-color: var(--accent-color, #88C0D0); }
    .tree-toggle, .tree-toggle-placeholder { width: 24px; height: 24px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-color-light); font-family: monospace; font-size: 14px; cursor: pointer; }
    .tree-toggle:hover { color: var(--text-color); }
    .box-icon { width: 24px; height: 24px; flex-shrink: 0; }
    .box-name { flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .right-panel { flex-grow: 1; padding: 16px; padding-top: 64px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; overflow-x: hidden; position: relative; }
    .details-group { display: flex; flex-direction: column; gap: 4px; }
    .details-group label { font-size: 0.9em; color: var(--text-color-light); }
    .details-group input { padding: 8px; background-color: var(--input-bg); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-color); font-size: 1em; box-sizing: border-box; }
    .details-group span { padding: 8px; background-color: transparent; border: 1px solid transparent; border-radius: 4px; color: var(--text-color-light); font-size: 1em; font-family: monospace; word-break: break-all; }
    .new-box-btn { position: absolute; top: 12px; right: 12px; width: 40px; height: 40px; padding: 0; display: flex; align-items: center; justify-content: center; background-color: var(--button-bg); border: 1px solid var(--button-border-color); border-radius: 8px; cursor: pointer; z-index: 10; }
    .new-box-btn:hover { background-color: var(--button-hover-bg); }
    .new-box-icon { width: 24px; height: 24px; opacity: 0.9; }
    .plus-badge { position: absolute; bottom: -2px; right: -2px; background-color: #27ae60; color: white; width: 16px; height: 16px; border-radius: 50%; font-size: 14px; font-weight: bold; line-height: 1; display: flex; align-items: center; justify-content: center; border: 2px solid var(--window-bg); }
    .delete-box-btn { position: absolute; top: 12px; left: 12px; padding: 8px 12px; display: flex; align-items: center; justify-content: center; gap: 8px; background-color: #c0392b; color: white; border: 1px solid #e74c3c; border-radius: 8px; cursor: pointer; z-index: 10; font-weight: bold; }
    .delete-box-btn:hover { background-color: #e74c3c; }
    .no-selection { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-color-light); font-style: italic; }
    .tabs { display: flex; border-bottom: 1px solid var(--border-color); }
    .tab-btn { padding: 8px 16px; cursor: pointer; background: none; border: none; color: var(--text-color-light); border-bottom: 2px solid transparent; margin-bottom: -1px; font-size: 0.95em; transition: color 0.2s ease, border-color 0.2s ease; }
    .tab-btn:hover { color: var(--text-color); }
    .tab-btn.active { color: var(--accent-color, #88C0D0); border-bottom-color: var(--accent-color, #88C0D0); font-weight: bold; }
    .tab-content { flex-grow: 1; overflow-y: auto; }
    .tab-pane { padding-top: 16px; display: flex; flex-direction: column; gap: 24px; }
    .tab-pane-placeholder { padding: 16px; color: var(--text-color-light); font-style: italic; text-align: center; }
    .disconnected-overlay { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 8px; color: var(--text-color-light); background-color: hsla(0, 0%, 20%, 0.5); font-size: 1.5em; font-weight: bold; border-radius: 8px; }
    .details-list { list-style-type: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .details-list li { background-color: var(--input-bg); padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); font-family: monospace; font-size: 0.9em; word-break: break-all; }
    .details-list li strong { color: var(--text-color); }
    .details-list li pre { margin-top: 4px; padding: 4px; background-color: rgba(0,0,0,0.2); border-radius: 4px; white-space: pre-wrap; }
    hr { border: none; border-top: 1px solid var(--border-color); margin: 0; }
    /* ProcBox Styles */
    .status-display { display: flex; gap: 16px; align-items: center; background-color: var(--input-bg); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); }
    .status-indicator { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
    .status-indicator.running { background-color: #2ecc71; }
    .status-indicator.stopped { background-color: #e74c3c; }
    .status-indicator.paused { background-color: #f39c12; }
    .status-indicator.error { background-color: #9b59b6; }
    .status-text { font-weight: bold; text-transform: capitalize; }
    .status-details { font-family: monospace; font-size: 0.9em; color: var(--text-color-light); }
    .controls { display: flex; gap: 8px; justify-content: center; align-items: center; }
    .controls button, .quick-link-btn { padding: 8px 16px; border: 1px solid var(--button-border-color); background-color: var(--button-bg); color: var(--text-color); border-radius: 4px; cursor: pointer; font-weight: bold; transition: background-color 0.2s; }
    .controls button:hover, .quick-link-btn:hover { background-color: var(--button-hover-bg); }
    .controls button:disabled { opacity: 0.5; cursor: not-allowed; }
    .controls .icon-btn { width: 40px; height: 40px; padding: 8px; display: flex; align-items: center; justify-content: center; }
    .controls .icon-btn svg { width: 100%; height: 100%; fill: currentColor; }
    .controls .start-btn:not(:disabled) { background-color: #27ae60; border-color: #2ecc71; color: white; }
    .controls .start-btn:not(:disabled):hover { background-color: #2ecc71; }
    .controls .stop-btn:not(:disabled) { background-color: #c0392b; border-color: #e74c3c; color: white; }
    .controls .stop-btn:not(:disabled):hover { background-color: #e74c3c; }
    .config-grid { display: grid; grid-template-columns: auto 1fr; gap: 12px 8px; align-items: center; }
    .config-grid label { font-size: 0.9em; color: var(--text-color-light); justify-self: end; }
    .config-grid input[type="text"] { width: 100%; }
    .checkbox-group { display: flex; align-items: center; gap: 8px; cursor: pointer;}
    .checkbox-group input { width: 16px; height: 16px; }
</style>

{#if $connectionStatus === 'connected'}
<div class="boxes-container" class:resizing={isResizing}>
    <button class="new-box-btn" on:click={handleNewBox} title="New Box">
        <img src="/skybox.png" alt="Box" class="new-box-icon" />
        <span class="plus-badge">+</span>
    </button>
    
    <div class="left-panel" style:width="{leftPanelWidth}px">
        {#each flatBoxList as box (box.id)}
            <div class="box-list-item" class:selected={box.id === selectedBoxId} class:current={box.id === $currentBoxId} on:click={() => handleSelectBox(box.id)} title={box.name} style:padding-left="{box.level * 20 + 8}px">
                {#if box.children && box.children.length > 0}
                    <button class="tree-toggle" on:click|stopPropagation={() => toggleExpand(box.id)}>{expanded[box.id] ? '▼' : '►'}</button>
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
            <button class="delete-box-btn" on:click={handleDeleteSelectedBox} title="Delete Selected Box">Delete Box</button>
        {/if}

        {#if selectedBox}
            <div class="details-group">
                <label for="box-name-input">Name</label>
                <input id="box-name-input" type="text" bind:value={nameInput} on:blur={handleNameUpdate} />
            </div>

            <div class="tabs">
                {#if selectedBox && selectedBox.type === 'iosk'}
                    <button class="tab-btn" class:active={activeTab === 'iosk'} on:click={() => activeTab = 'iosk'}>IOSK</button>
                {/if}
                <button class="tab-btn" class:active={activeTab === 'properties'} on:click={() => activeTab = 'properties'}>Properties</button>
                <button class="tab-btn" class:active={activeTab === 'shortcuts'} on:click={() => activeTab = 'shortcuts'}>Shortcuts</button>
                <button class="tab-btn" class:active={activeTab === 'boards'} on:click={() => activeTab = 'boards'}>Back Boards</button>
                <button class="tab-btn" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>Settings</button>
            </div>

            <div class="tab-content">
                {#if activeTab === 'iosk'}
                    <div class="tab-pane">
                        <div class="details-group">
                            <div class="status-display">
                                <div class="status-indicator" class:running={latestProcess?.status === 'running'} class:stopped={!latestProcess || latestProcess?.status === 'stopped'} class:paused={latestProcess?.status === 'paused'} class:error={latestProcess?.status === 'error'}></div>
                                <span class="status-text">{latestProcess?.status ?? 'Stopped'}</span>
                                <span class="status-details">
                                    {#if activeProcess}
                                        PID: {activeProcess.pid} &nbsp;&nbsp; Uptime: {uptime}
                                    {:else}
                                        Not running.
                                    {/if}
                                </span>
                            </div>
                        </div>

                        <div class="details-group">
                            <div class="controls">
                                <button on:click={() => stopProcess(activeProcess.pid)} disabled={!activeProcess} class="icon-btn stop-btn" title="Stop Process">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>
                                </button>
                                <button class="quick-link-btn" disabled>View in Process Manager</button>
                                <button on:click={() => startIosk(selectedBoxId)} disabled={!!activeProcess} class="icon-btn start-btn" title="Start Process">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                                </button>
                            </div>
                        </div>

                        <hr />

                        {#if ioskConfig}
                        <div class="details-group">
                            <label>Configuration</label>
                            <div class="config-grid">
                                <label for="mount-point">Mount Point</label>
                                <input id="mount-point" type="text" placeholder="(Optional) Path to media directory" bind:value={ioskConfig.mount_point} on:input={handleConfigChange}>
                                
                                <label for="daemon-mode">Daemon Mode</label>
                                <label class="checkbox-group">
                                    <input id="daemon-mode" type="checkbox" bind:checked={ioskConfig.daemon_mode} on:change={handleConfigChange}>
                                    <span>Process can outlive SKYBRIDGE</span>
                                </label>

                                <label for="enable-stdin">Enable STDIN</label>
                                <label class="checkbox-group">
                                    <input id="enable-stdin" type="checkbox" bind:checked={ioskConfig.enable_stdin} on:change={handleConfigChange}>
                                    <span>Allow interactive standard input</span>
                                </label>
                            </div>
                        </div>
                        {:else}
                            <div class="tab-pane-placeholder">Loading IOSK configuration...</div>
                        {/if}
                    </div>
                {:else if activeTab === 'properties'}
                    <div class="tab-pane" style="gap: 16px;">
                        <div class="details-group"><label>ID</label><span>{selectedBox.id}</span></div>
                        <div class="details-group"><label>Type</label><span>{selectedBox.type}</span></div>
                        <div class="details-group"><label>Context Path</label><span>{selectedBox.context}</span></div>
                        <div class="details-group"><label>Parent Box ID</label><span>{selectedBox.parent_box_id ?? 'N/A'}</span></div>
                    </div>
                {:else if activeTab === 'shortcuts'}
                    <div class="tab-pane">
                        {#if selectedBoxShortcuts.length > 0}
                            <ul class="details-list">{#each selectedBoxShortcuts as shortcut}<li><strong>{shortcut.name}</strong> [{shortcut.type}] <br/> {shortcut.path}</li>{/each}</ul>
                        {:else}<div class="tab-pane-placeholder">No shortcuts configured for this box.</div>{/if}
                    </div>
                {:else if activeTab === 'boards'}
                    <div class="tab-pane">
                        {#if selectedBoxBackedWindows.length > 0}
                            <ul class="details-list">{#each selectedBoxBackedWindows as board}<li><strong>ID: {board.id}</strong><br/>Position: ({Math.round(board.x)}, {Math.round(board.y)}), Scale: {board.scale.toFixed(2)}<br/>Config: <pre>{JSON.stringify(board.config, null, 2)}</pre></li>{/each}</ul>
                        {:else}<div class="tab-pane-placeholder">No backed boards found for this box.</div>{/if}
                    </div>
                {:else if activeTab === 'settings'}
                    <div class="tab-pane">
                         {#if Object.keys(selectedBoxSettings).length > 0}
                            <ul class="details-list">{#each Object.entries(selectedBoxSettings) as [key, value]}<li><strong>{key}:</strong> {JSON.stringify(value)}</li>{/each}</ul>
                        {:else}<div class="tab-pane-placeholder">No custom settings for this box. Using defaults.</div>{/if}
                    </div>
                {/if}
            </div>
        {:else}
            <div class="no-selection">Select a box to see its details.</div>
        {/if}
    </div>
</div>
{:else}
    <div class="disconnected-overlay">
        <span>SKYBRIDGE REQUIRED</span>
        <span style="font-size: 0.7em; font-weight: normal; text-transform: capitalize;">Connection Status: {$connectionStatus}</span>
    </div>
{/if}
