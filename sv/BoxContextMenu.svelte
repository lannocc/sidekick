<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { get } from 'svelte/store';
    import { createEventDispatcher } from 'svelte';
    import { 
        newAskWindow, 
        newLocalFileExplorer, 
        newLocalTerminal,
        showBoxesAndSelect,
        newIoskConsole,
        newIoskFileExplorer
    } from './apps.js';
    import { 
        updateBox, 
        deleteBox, 
        savePanelConfig, 
        setBoxCover, 
        promoteToIosk, 
        runningProcesses,
        allIoskConfigs,
        startIosk,
        stopProcess,
        pauseProcess,
        resumeProcess
    } from './bridge.js';
    import { activeIoskConnections, initiateConnection } from './iosk.js';

    export let box;
    export let showDelete = true;

    const dispatch = createEventDispatcher();
    function onClose() {
        dispatch('close');
    }

    // --- Logic from Box.svelte ---
    $: activeProcess = $runningProcesses.find(p => p.box_id === box.id && (p.status === 'running' || p.status === 'paused'));
    $: coverPanelLocation = box.cover_panel_location;
    $: canSetCover = !coverPanelLocation;

    let ioskConnections = [];
    let defaultUserConnectionInfo = {
        exists: false,
        connectionId: null,
        username: 'root'
    };

    $: {
        if (box.type === 'iosk' && activeProcess?.port) {
            const urlPart = `ws://localhost:${activeProcess.port}`;
            
            const allConnections = Array.from($activeIoskConnections.entries());
            ioskConnections = allConnections
                .filter(([, conn]) => conn.url === urlPart)
                .map(([id, conn]) => ({ connectionId: id, username: conn.username, status: conn.status }));

            const config = $allIoskConfigs[box.id];
            const defaultUsername = config?.default_username || 'root';
            const defaultConnectionId = `${defaultUsername}@${urlPart}`;
            const defaultConnectionExists = ioskConnections.some(c => c.username === defaultUsername);

            defaultUserConnectionInfo = {
                exists: defaultConnectionExists,
                connectionId: defaultConnectionId,
                username: defaultUsername
            };
        } else {
            ioskConnections = [];
            defaultUserConnectionInfo = { exists: false, connectionId: null, username: 'root' };
        }
    }

    // --- Menu Actions ---
    function renameBox() {
        onClose();
        const newName = prompt(`Rename box "${box.name}":`, box.name);
        if (newName && newName.trim() !== '' && newName !== box.name) {
            updateBox(box.id, newName);
        }
    }

    function deleteBoxConfirm() {
        onClose();
        if (confirm(`Are you sure you want to delete the box "${box.name}"?`)) {
            deleteBox(box.id);
        }
    }

    function askBox() {
        onClose();
        newAskWindow([box.context]);
    }

    function openTerminal() {
        onClose();
        if (box.context) {
            newLocalTerminal({ title: `Terminal - ${box.name}`, initialPath: box.context });
        }
    }

    function openFiles() {
        onClose();
        if (box.context) {
            newLocalFileExplorer({ title: `Local Files - ${box.name}`, initialPath: box.context });
        }
    }

    function handlePromoteToIosk() {
        onClose();
        promoteToIosk(box.id);
    }

    function handleOpenConsole(connectionId, shouldConnect = false) {
        onClose();
        if (shouldConnect) {
            const [username, url] = connectionId.split('@');
            initiateConnection(url, username);
        }
        newIoskConsole({ connectionId });
    }

    function handleOpenFiles(connectionId, shouldConnect = false) {
        onClose();
        if (shouldConnect) {
            const [username, url] = connectionId.split('@');
            initiateConnection(url, username);
            
            const unsubscribe = activeIoskConnections.subscribe(conns => {
                const currentConn = conns.get(connectionId);
                if (currentConn?.status === 'connected') {
                    newIoskFileExplorer({ connectionId });
                    unsubscribe();
                } else if (currentConn?.status === 'error' || currentConn?.status === 'disconnected') {
                    alert(`Failed to connect to IOSK for box "${box.name}".`);
                    unsubscribe();
                }
            });
            setTimeout(() => unsubscribe(), 5000); // 5s timeout
        } else {
            const connState = get(activeIoskConnections).get(connectionId);
            if (connState?.status === 'connected') {
                newIoskFileExplorer({ connectionId });
            } else {
                alert('Connection is not active. Cannot open file explorer.');
            }
        }
    }

    function setCoverImage() {
        onClose();
        if (!canSetCover) {
            alert("A cover image is already set.");
            return;
        }
        const url = prompt("Enter URL for cover image:");
        if (url) {
            const panels = box.panels || {};
            if (panels['0_-1']) {
                alert("The default cover image slot (top) is already occupied. Please clear it first.");
                return;
            }
            const x = 0, y = -1;
            const parent = { x: 0, y: 0 };
            const locationKey = `${x}_${y}`;
            savePanelConfig(box.id, x, y, 'image', { url }, parent);
            setBoxCover(box.id, locationKey);
        }
    }

    function clearCoverImage() {
        onClose();
        if (coverPanelLocation) {
            const [loc_x, loc_y] = coverPanelLocation.split('_').map(Number);
            savePanelConfig(box.id, loc_x, loc_y, 'empty', null, null);
            setBoxCover(box.id, null);
        }
    }
</script>

<button on:click={askBox}><span class="menu-item-icon">?</span>Ask...</button>
<button on:click={openTerminal}><span class="menu-item-icon">&gt;_</span>Terminal</button>
<button on:click={openFiles}><span class="menu-item-icon">📁</span>Files</button>

{#if box.type === 'iosk'}
    <div class="menu-separator"></div>
    
    {#each ioskConnections as conn (conn.connectionId)}
        <div class="menu-subheader">{conn.username}</div>
        <button class="menu-item-indented" on:click={() => handleOpenConsole(conn.connectionId)}>
            <img src="/iosk.png" alt="IOSK" class="menu-item-icon" />
            Console
        </button>
        <button class="menu-item-indented" on:click={() => handleOpenFiles(conn.connectionId)} disabled={conn.status !== 'connected'}>
            <span class="menu-item-icon">📁</span>
            Files
        </button>
    {/each}

    {#if !defaultUserConnectionInfo.exists && activeProcess?.port}
        {#if ioskConnections.length > 0}<div class="menu-separator"></div>{/if}
        <div class="menu-subheader">New as {defaultUserConnectionInfo.username}</div>
        <button class="menu-item-indented" on:click={() => handleOpenConsole(defaultUserConnectionInfo.connectionId, true)}>
            <img src="/iosk.png" alt="IOSK" class="menu-item-icon" />
            Console
        </button>
        <button class="menu-item-indented" on:click={() => handleOpenFiles(defaultUserConnectionInfo.connectionId, true)}>
            <span class="menu-item-icon">📁</span>
            Files
        </button>
    {/if}

    <div class="menu-separator"></div>
    {#if activeProcess}
        {#if activeProcess.status === 'running'}
            <button on:click={() => pauseProcess(activeProcess.pid)}><span class="menu-item-icon">⏸️</span>Pause</button>
        {/if}
        {#if activeProcess.status === 'paused'}
            <button on:click={() => resumeProcess(activeProcess.pid)}><span class="menu-item-icon">▶️</span>Resume</button>
        {/if}
        <button on:click={() => stopProcess(activeProcess.pid)}><span class="menu-item-icon">⏹️</span>Stop</button>
    {:else}
        <button on:click={() => startIosk(box.id)}><span class="menu-item-icon">▶️</span>Start</button>
    {/if}
{/if}

<div class="menu-separator"></div>
{#if box.type === 'local' && box.id !== 0}
    <button on:click={handlePromoteToIosk}><img src="/iosk.png" alt="IOSK" class="menu-item-icon" />Promote to IOSK Box</button>
    <div class="menu-separator"></div>
{/if}
<button on:click={() => { showBoxesAndSelect(box.id); onClose(); }}><span class="menu-item-icon">🔧</span>Configuration...</button>
<button on:click={renameBox}><span class="menu-item-icon">✏️</span>Rename...</button>
<div class="menu-separator"></div>
<button on:click={setCoverImage} disabled={!canSetCover}><span class="menu-item-icon">🖼️</span>Set Cover Image...</button>
<button on:click={clearCoverImage} disabled={!coverPanelLocation}><span class="menu-item-icon">🚫</span>Clear Cover Image</button>
{#if showDelete}
    <div class="menu-separator"></div>
    <button on:click={deleteBoxConfirm} class="delete"><span class="menu-item-icon">🗑️</span>Delete</button>
{/if}

<style>
    .menu-item-icon {
        margin-right: 8px;
        width: 16px;
        height: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 16px;
    }
    img.menu-item-icon {
        object-fit: contain;
    }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .delete { color: #e74c3c; }
    :global(.context-menu .delete:hover), :global(.submenu .delete:hover) {
        background-color: #c0392b;
        color: white;
    }

    .menu-subheader {
        padding: 4px 12px;
        font-size: 12px;
        font-weight: bold;
        color: var(--title-bar-text);
        background-color: var(--title-bar-bg);
        cursor: default;
    }
    /* These need to be global to be applied from the parent component's class */
    :global(.context-menu button.menu-item-indented), :global(.submenu button.menu-item-indented) {
        padding-left: 24px;
    }
</style>