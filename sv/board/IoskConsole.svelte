<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate, tick } from 'svelte';
    import { get } from 'svelte/store';
    import { windows } from '../windows.js';
    import { newIoskFileExplorer, newIoskWatch } from '../apps.js';
    import { runningProcesses } from '../bridge.js';
    // --- MODIFICATION START: Import new central connection hub and the new UsersList component ---
    import {
        activeIoskConnections,
        initiateConnection,
        disconnect as disconnectSession,
        sendCommand as sendIoskCommand
    } from '../iosk.js';
    import IoskUsersList from './IoskUsersList.svelte';
    // --- MODIFICATION END ---
    import { desktopSettings, windowSettings } from '../desktop.js';
    import RoomsMenu from './popup/RoomsMenu.svelte';
    import WindowSettingsModal from '../popup/WindowSettingsModal.svelte';
    import { parseAnsi, stripAnsi } from '../ansi.js';

    export let id; // Unique ID from the window manager
    export let groupId;
    export let title;
    export let isActive;
    export let componentName;
    export let x, y, width, height; // Current geometry from Window.svelte

    // --- MODIFICATION START: connectionId is the primary prop for identifying a session ---
    export let connectionId = null;
    // --- MODIFICATION END ---

    // --- MODIFICATION START: Local state for new connection form ---
    let localWsUrl = get(desktopSettings).ioskUrl || 'ws://localhost:4209';
    let localUsername = get(desktopSettings).ioskUsername || 'root';
    // --- MODIFICATION END ---

    let settings;
    desktopSettings.subscribe(value => settings = value);

    // --- MODIFICATION START: All state is derived from the central store ---
    let connectionState = null;
    let isConnected = false;
    let localHostname = '';
    let roomName = null;
    let roomTopic = '';
    let motd = '';
    let roomParticipants = [];
    let availableRooms = [];
    let userColors = {};
    let userTokenStats = {};
    let output = [];
    let commandHistory = [];
    let currentPrompt = '';

    $: {
        if (connectionId && $activeIoskConnections.has(connectionId)) {
            connectionState = $activeIoskConnections.get(connectionId);
            isConnected = connectionState?.status === 'connected';
            localHostname = connectionState?.localHostname || '';
            roomName = connectionState?.roomName || null;
            roomTopic = connectionState?.roomTopic || '';
            motd = connectionState?.motd || '';
            roomParticipants = connectionState?.roomParticipants || [];
            availableRooms = connectionState?.availableRooms || [];
            userColors = connectionState?.userColors || {};
            userTokenStats = connectionState?.userTokenStats || {};
            output = connectionState?.output || [];
            commandHistory = connectionState?.commandHistory || [];
            currentPrompt = connectionState?.currentPrompt || '';
        } else {
            // Reset state if we are detached or the connection disappears from the store
            connectionState = null;
            isConnected = false;
            localHostname = ''; roomName = null; roomTopic = ''; motd = ''; roomParticipants = []; availableRooms = []; userColors = {}; userTokenStats = {}; output = []; commandHistory = []; currentPrompt = '';
            // If the connectionId was set but is no longer valid, clear it to return to the picker.
            if (connectionId && !$activeIoskConnections.has(connectionId)) {
                connectionId = null;
            }
        }
    }
    // --- MODIFICATION END ---

    let showRoomsMenu = false;

    // Internal Component State
    let command = '';
    let historyIndex = 0;
    let unsentCommand = '';

    // DOM element refs
    let terminalEl;
    let commandInput;
    let roomsButton;

    // --- MODIFICATION: Users Panel state is kept here for persistence via getState() ---
    export let usersPanelWidth = 260;
    export let isUsersPanelCollapsed = true;

    let prevRoomName = null;
    $: {
        if (roomName && !prevRoomName) { isUsersPanelCollapsed = false; }
        else if (!roomName && prevRoomName) { isUsersPanelCollapsed = true; }
        prevRoomName = roomName;
    }

    // --- MODIFICATION START: Simplified state for persistence ---
    export function getState() {
        return {
            connectionId,
            usersPanelWidth,
            isUsersPanelCollapsed,
        };
    }
    // --- MODIFICATION END ---

    // --- MODIFICATION: Remove ws instance ---
    let showSettings = false;
    let shouldScroll = true;

    // --- NEW: Derive a list of connectable IOSK boxes from running processes ---
    let runningIoskBoxes = [];
    $: runningIoskBoxes = $runningProcesses.filter(p => p.type === 'iosk' && (p.status === 'running' || p.status === 'paused') && p.port);

    // Lifecycle and Reactive Statements
    afterUpdate(() => {
        if (shouldScroll && terminalEl) {
            terminalEl.scrollTop = terminalEl.scrollHeight;
        }
    });

    async function focusInput() {
        await tick();
        commandInput?.focus();
    }

    function handleClickOnTerminal() {
        if (window.getSelection().isCollapsed) {
            focusInput();
        }
    }

    // --- MODIFICATION: Global click/key handlers simplified or removed ---
    function handleGlobalClick(event) {
        if (showRoomsMenu && roomsButton && !roomsButton.contains(event.target)) {
            showRoomsMenu = false; focusInput();
        }
    }

    onMount(() => {
        window.addEventListener('click', handleGlobalClick);
    });

    onDestroy(() => {
        window.removeEventListener('click', handleGlobalClick);
    });

    $: historyIndex = commandHistory.length;

    // --- MODIFICATION: Update tab props with connectionId ---
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, {
            isConsoleConnected: isConnected,
            connectionId, // Pass the ID instead of connection details
            isSettingsModalOpen: showSettings
        });
    }

    $: if (groupId !== undefined && id !== undefined && title !== undefined) {
        let newTitle;
        if (isConnected && connectionState) {
            const host = (() => { try { return new URL(connectionState.url).hostname } catch { return 'invalid-host' }})();
            const userAtHost = `${connectionState.username}@${host}`;
            newTitle = roomName ? `[${stripAnsi(roomName)}] ${userAtHost}` : userAtHost;
        } else if (connectionState?.status === 'connecting') {
            newTitle = 'Connecting...';
        } else if (connectionState?.status === 'error') {
            newTitle = '[Error] Connection Failed';
        } else if (connectionState?.status === 'disconnected') {
            newTitle = 'Disconnected';
        } else {
            newTitle = 'IOSK Console';
        }
        if (newTitle !== title) {
            windows.updateTabProps(groupId, id, { title: newTitle });
        }
    }

    // --- MODIFICATION: All user-related action functions have been moved to IoskUsersList ---
    function sendSystemCommand(systemCommand) {
        if (!systemCommand.trim()) return;
        if (connectionId) {
            sendIoskCommand(connectionId, systemCommand);
        }
        shouldScroll = true;
    }

    // --- Functions ---
    export function showSettingsDialog() { showSettings = true; }

    let settingsUrl, settingsUsername;
    $: if (showSettings) {
        // Settings are now for global defaults, not this specific instance
        const globalSettings = get(windowSettings)[componentName] || {};
        settingsUrl = globalSettings.defaultUrl || get(desktopSettings).ioskUrl;
        settingsUsername = globalSettings.defaultUsername || get(desktopSettings).ioskUsername;
    }
    function handleSaveComponentSettings() {
        windowSettings.update(allSettings => {
            const existingSettings = allSettings[componentName] || {};
            return { ...allSettings, [componentName]: { ...existingSettings, defaultUrl: settingsUrl, defaultUsername: settingsUsername } };
        });
    }

    // --- MODIFICATION: connect() becomes createAndAttachConnection() ---
    async function createAndAttachConnection() {
        const newConnectionId = initiateConnection(localWsUrl, localUsername);
        connectionId = newConnectionId;
        await tick();
        focusInput();
    }

    // --- MODIFICATION: Disconnect now calls central hub and clears local ID ---
    function disconnect() {
        if (connectionId) {
            // Note: disconnectSession does NOT remove the session from the central store,
            // it only closes the websocket and sets status to 'disconnected'.
            // A separate UI action in the Connections Menu will be needed to truly "forget" a session.
            // For the console, we just detach from it by setting connectionId to null.
            connectionId = null;
        }
    }

    // --- MODIFICATION: sendCommand calls central hub ---
    function sendCommand() {
        if (!command.trim() || !connectionId) return;
        sendIoskCommand(connectionId, command);
        command = '';
        unsentCommand = '';
        historyIndex = commandHistory.length; // Reset history index on send
        shouldScroll = true;
    }

    // --- NEW: Functions to handle connecting from a running box ---
    function populateFromBox(proc) {
        if (!proc || !proc.port) return;
        localWsUrl = `ws://localhost:${proc.port}`;
        localUsername = proc.default_username || 'root';
    }

    async function populateAndConnect(proc) {
        populateFromBox(proc);
        await tick(); // Allow bound values to update
        createAndAttachConnection();
    }

    // --- MODIFICATION: Room/logout actions use sendSystemCommand ---
    function joinRoom(roomToJoin) { sendSystemCommand(`$ room ${roomToJoin}`); showRoomsMenu = false; focusInput(); }
    function closeRoom() { sendSystemCommand('$ clroom'); showRoomsMenu = false; focusInput(); }
    function sendLogout() {
        let logoutCommand = 'logout';
        if (currentPrompt.trim().endsWith('>>')) logoutCommand = '$ logout';
        sendSystemCommand(logoutCommand);
        command = ''; unsentCommand = ''; historyIndex = commandHistory.length; shouldScroll = true;
    }

    // handleKeydown is unchanged, but calls modified sendCommand/sendLogout
    function handleKeydown(e) {
        if (e.ctrlKey) {
            switch (e.key.toLowerCase()) {
                case 'c': e.preventDefault(); command = ''; return;
                case 'd': e.preventDefault(); sendLogout(); return;
                case 'home': e.preventDefault(); if (terminalEl) { terminalEl.scrollTop = 0; shouldScroll = false; } return;
                case 'end': e.preventDefault(); if (terminalEl) { terminalEl.scrollTop = terminalEl.scrollHeight; shouldScroll = true; } return;
            }
        }
        switch (e.key) {
            case 'Enter': e.preventDefault(); sendCommand(); return;
            case 'ArrowUp': e.preventDefault(); if (commandHistory.length === 0) return; if (historyIndex === commandHistory.length) unsentCommand = command; if (historyIndex > 0) command = commandHistory[--historyIndex]; return;
            case 'ArrowDown': e.preventDefault(); if (commandHistory.length === 0) return; if (historyIndex < commandHistory.length - 1) command = commandHistory[++historyIndex]; else if (historyIndex === commandHistory.length - 1) { historyIndex++; command = unsentCommand; } return;
            case 'PageUp': e.preventDefault(); if (terminalEl) { terminalEl.scrollTop -= terminalEl.clientHeight * 0.9; shouldScroll = false; } return;
            case 'PageDown': e.preventDefault(); if (terminalEl) terminalEl.scrollTop += terminalEl.clientHeight * 0.9; return;
        }
    }

    export function toggleRoomsMenu() { showRoomsMenu = !showRoomsMenu; }

    // --- MODIFICATION: Watch Window Function now passes connectionId ---
    function launchWatchWindow() {
        if (!connectionId) return;
        const match = currentPrompt.match(/\[\S+\s+([^\]]+)\]/);
        const pwd = match ? match[1] : '/';
        newIoskWatch({ connectionId, path: pwd });
        focusInput();
    }

</script>

<svelte:window on:close-all-context-menus={() => { showRoomsMenu = false; }} />

<!-- MODIFICATION: Main container now has an outer if/else for connection state -->
<div class="console-container">
    {#if !connectionId}
        <!-- Initial Screen: Attach to existing or create new connection -->
        <div class="initial-screen">
            <h3>Connect to Running Box</h3>
            <div class="connection-list">
                {#if runningIoskBoxes.length === 0}
                    <div class="no-connections">No running IOSK boxes.</div>
                {:else}
                    {#each runningIoskBoxes as proc (proc.pid)}
                        <button
                            class="connection-item"
                            on:click={() => populateFromBox(proc)}
                            on:dblclick={() => populateAndConnect(proc)}
                            title="Click to populate, Double-click to connect"
                        >
                            <span class="conn-id">{proc.box_name || `Box ID: ${proc.box_id}`}</span>
                            <span class="conn-status {proc.status}">{proc.status}</span>
                        </button>
                    {/each}
                {/if}
            </div>

            <h3>Attach to Session</h3>
            <div class="connection-list">
                {#if $activeIoskConnections.size === 0}
                    <div class="no-connections">No active connections.</div>
                {:else}
                    {#each Array.from($activeIoskConnections.entries()) as [id, conn] (id)}
                        <button class="connection-item" on:click={() => connectionId = id}>
                            <span class="conn-id">{id}</span>
                            <span class="conn-status {conn.status}">{conn.status}</span>
                        </button>
                    {/each}
                {/if}
            </div>

            <div class="separator"><span>OR</span></div>

            <h3>New Connection</h3>
            <form class="connect-form" on:submit|preventDefault={createAndAttachConnection}>
                <input id="url-input-{id}" type="text" bind:value={localWsUrl} placeholder="ws://host:port">
                <input type="text" bind:value={localUsername} placeholder="username">
                <button class="connect-button" type="submit">Connect</button>
            </form>
        </div>
    {:else}
        <!-- Main Console View: Attached to a session -->
        <div class="connect-form">
            <button type="button" class="header-button disconnect-button" on:click={disconnect} title="Detach from this session and return to the connection picker. The session remains active.">Detach</button>
            <button type="button" class="header-button room-button" bind:this={roomsButton} on:click|stopPropagation={toggleRoomsMenu} title={roomName ? `Current Room: ${stripAnsi(roomName)}` : "Available Rooms"} disabled={!isConnected}>
                {#if roomName}
                    {@html parseAnsi(roomName)}
                {:else}
                    Rooms
                {/if}
            </button>
            <div class="header-info" title={stripAnsi(roomTopic || motd)}>
                {@html parseAnsi(roomTopic || motd)}
            </div>
            <button type="button" class="header-button watch-button" on:click={launchWatchWindow} title="Watch a command" disabled={!isConnected}>Watch</button>
            <button type="button" class="header-button files-button" on:click={() => { if (connectionId) { newIoskFileExplorer({ connectionId }); focusInput(); } }} title="Browse files" disabled={!isConnected}>Files</button>
        </div>

        {#if showRoomsMenu}
            <RoomsMenu
                {availableRooms}
                currentRoomName={roomName}
                on:join={e => joinRoom(e.detail)}
                on:close={closeRoom}
            />
        {/if}

        <div class="main-flex-area">
            <div class="terminal-wrapper">
                <div class="terminal" bind:this={terminalEl} on:scroll={() => shouldScroll = (terminalEl.scrollTop + terminalEl.clientHeight >= terminalEl.scrollHeight - 10)} on:click={handleClickOnTerminal}>
                    {#each output as line, i (i)}
                        <div class="terminal-line" class:prompt={line.type === 'prompt'}>
                            {@html parseAnsi(line.content)}
                        </div>
                    {/each}
                </div>
                {#if isConnected}
                    <div class="input-area" on:click={() => commandInput?.focus()}>
                        <span>{@html parseAnsi(currentPrompt)}</span>
                        <input type="text" bind:this={commandInput} bind:value={command} on:keydown={handleKeydown} spellcheck="false" />
                    </div>
                {/if}
            </div>

            <!-- MODIFICATION: Use the new IoskUsersList component -->
            {#if isConnected && roomName}
                <IoskUsersList
                    {connectionId}
                    localUser={connectionState?.username}
                    {localHostname}
                    {roomParticipants}
                    {userColors}
                    {userTokenStats}
                    bind:usersPanelWidth
                    bind:isUsersPanelCollapsed
                />
            {/if}
        </div>
    {/if}

    <WindowSettingsModal
        bind:show={showSettings}
        title="Console Settings"
        {componentName}
        {x} {y} {width} {height}
        on:save={handleSaveComponentSettings}
    >
        <div class="form-group">
            <label for="url-setting-{id}">Default URL</label>
            <input id="url-setting-{id}" type="text" bind:value={settingsUrl}>
        </div>
        <div class="form-group">
            <label for="user-setting-{id}">Default Username</label>
            <input id="user-setting-{id}" type="text" bind:value={settingsUsername}>
        </div>
    </WindowSettingsModal>

</div>

<style>
    /* Add styles for the new initial screen */
    .initial-screen { padding: 20px; display: flex; flex-direction: column; gap: 15px; height: 100%; overflow-y: auto; }
    .initial-screen h3 { margin: 0; font-weight: 500; color: var(--title-bar-text); border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
    .connection-list { display: flex; flex-direction: column; gap: 5px; max-height: 200px; overflow-y: auto; }
    .no-connections { color: #95a5a6; font-style: italic; padding: 10px 0; }
    .connection-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); cursor: pointer; border-radius: 3px; text-align: left; }
    .connection-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .conn-id { font-family: monospace; font-size: 0.9em; }
    .conn-status { font-weight: bold; font-size: 0.8em; text-transform: uppercase; padding: 2px 5px; border-radius: 3px; }
    .conn-status.connected, .conn-status.running { color: #2ecc71; }
    .conn-status.connecting { color: #f39c12; }
    .conn-status.disconnected { color: #95a5a6; }
    .conn-status.error { color: #e74c3c; }
    .conn-status.paused { color: #f39c12; }
    .separator { display: flex; align-items: center; text-align: center; color: #7f8c8d; margin: 10px 0; }
    .separator::before, .separator::after { content: ''; flex: 1; border-bottom: 1px solid var(--border-color); }
    .separator:not(:empty)::before { margin-right: .25em; }
    .separator:not(:empty)::after { margin-left: .25em; }

    /* --- Existing Styles --- */
    :global(:root) { /* Define ANSI colors so they can be themed */
        --ansi-black: #2c3e50; --ansi-red: #c0392b; --ansi-green: #27ae60; --ansi-yellow: #f1c40f; --ansi-blue: #2980b9; --ansi-magenta: #8e44ad; --ansi-cyan: #16a085; --ansi-white: #bdc3c7; --ansi-bright-black: #95a5a6; --ansi-bright-red: #e74c3c; --ansi-bright-green: #2ecc71; --ansi-bright-yellow: #f39c12; --ansi-bright-blue: #3498db; --ansi-bright-magenta: #9b59b6; --ansi-bright-cyan: #1abc9c; --ansi-bright-white: #ecf0f1;
    }
    .console-container { display: flex; flex-direction: column; height: 100%; background-color: var(--console-bg); color: var(--console-text); font-family: monospace; font-size: 14px; position: relative; }
    .connect-form { display: flex; gap: 8px; padding: 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); flex-shrink: 0; align-items: center; }
    .connect-form input { flex-grow: 1; background-color: var(--window-bg); color: var(--title-bar-text); border: 1px solid var(--border-color); padding: 4px; }
    .connect-form .connect-button { background-color: #27c93f; border: 1px solid #1a9c2a; color: white; padding: 4px 8px; cursor: pointer; border-radius: 3px; }
    .connect-form .header-button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 4px 8px; cursor: pointer; border-radius: 3px; }
    .connect-form .header-button:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .connect-form .header-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .connect-form .disconnect-button { background-color: #e74c3c; border-color: #c0392b; color: white; }
    .connect-form .disconnect-button:hover { background-color: #c0392b; }
    .connect-form .room-button { background-color: #ffbd2e; border-color: #e0a320; color: white; position: relative; padding-left: 15px; max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; }
    .connect-form .room-button:hover { background-color: #e0a320; }
    .connect-form .watch-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .connect-form .watch-button:hover { background-color: #1a9c2a; }
    .connect-form .files-button { background-color: #3498db; border-color: #2980b9; color: white; }
    .connect-form .files-button:hover { background-color: #2980b9; }

    .connect-form .room-button::before { content: ''; position: absolute; top: 50%; transform: translateY(-50%); width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 4px solid rgba(255, 255, 255, 0.7); left: 5px; }
    .header-info { flex-grow: 1; text-align: center; color: #bdc3c7; font-style: italic; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; padding: 0 10px; }
    .main-flex-area { flex-grow: 1; display: flex; overflow: hidden; height: 100%; position: relative; }
    .terminal-wrapper { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; height: 100%; }
    .terminal { flex-grow: 1; overflow-y: auto; padding: 8px; white-space: pre-wrap; word-break: break-all; }
    .terminal-line.prompt { color: var(--console-prompt); }
    .input-area { display: flex; padding: 4px 8px; background-color: var(--title-bar-bg); border-top: 1px solid var(--border-color); flex-shrink: 0; }
    .input-area span { color: var(--console-prompt); padding-right: 5px; white-space: pre; }
    .input-area input { flex-grow: 1; background: transparent; border: none; outline: none; color: var(--console-input); font-family: inherit; font-size: inherit; }

    /* MODIFICATION: All users-panel styles have been moved to IoskUsersList.svelte */

    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    .form-group { display: flex; flex-direction: column; gap: 5px; }
    .modal-content label { font-size: 0.9em; color: var(--title-bar-text); }
    .modal-content input { background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 8px; border-radius: 3px; font-family: monospace; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
</style>
