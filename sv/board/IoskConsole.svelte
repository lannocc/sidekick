<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate, tick } from 'svelte';
    import { get } from 'svelte/store';
    import { windows } from '../windows.js';
    import { newIoskFileExplorer, newIoskFileViewer, newIoskPrivateChat, newIoskWatch, newIoskUserInspector } from '../apps.js';
    // --- MODIFICATION START: Import new central connection hub ---
    import {
        activeIoskConnections,
        initiateConnection,
        disconnect as disconnectSession,
        sendCommand as sendIoskCommand,
        sendRequest as sendIoskRequest,
        fileSystemResponses,
    } from '../iosk.js';
    // --- MODIFICATION END ---
    import { desktopSettings, windowSettings, calculateWindowContextMenuPosition } from '../desktop.js';
    import RoomsMenu from './popup/RoomsMenu.svelte';
    import AttachMenu from './popup/AttachMenu.svelte';
    import UserContextMenu from './popup/UserContextMenu.svelte';
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

    // State for Attach Menu (remains local to the component)
    let showAttachMenu = false;
    let attachDevices = [];
    let attachUsers = [];
    let isLoadingDevices = false;
    let isLoadingUsers = false;
    let attachMenuPosition = { x: 0, y: 0 };
    const ATTACH_REQUEST_ID = `console-attach-${id}`;

    // State for User Context Menu (remains local)
    let userContextMenu = { visible: false, x: 0, y: 0, user: null };

    // State for Token Telemetry (remains local)
    let tokenTooltip = { visible: false, x: 0, y: 0, user: null };

    // Internal Component State
    let command = '';
    let historyIndex = 0;
    let unsentCommand = '';

    // DOM element refs
    let terminalEl;
    let commandInput;
    let settingsUrlInput;
    let roomsButton;
    let attachButton;

    // Users Panel State
    export let usersPanelWidth = 260;
    export let isUsersPanelCollapsed = true;
    let isResizing = false;

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

    // Helper functions for telemetry (abbreviateNumber, formatBytes) are unchanged.
    function abbreviateNumber(num) {
        if (num == null) return '';
        if (num < 1000) return num.toString();
        const suffixes = ["", "k", "m", "b", "t"];
        const i = Math.floor(Math.log10(num) / 3);
        let short = num / Math.pow(1000, i);
        let precision = 2;
        if (short >= 100) {
            precision = 0;
        } else if (short >= 10) {
            precision = 1;
        }
        return parseFloat(short.toFixed(precision)) + suffixes[i];
    }
    function formatBytes(bytes, decimals = 2) {
        if (bytes == null || bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    // startResize function is unchanged
    function startResize(event) {
        isResizing = true;
        const initialResizeX = event.clientX;
        const initialResizeWidth = usersPanelWidth;

        function handleResize(e) {
            if (!isResizing) return;
            const dx = e.clientX - initialResizeX;
            const newWidth = initialResizeWidth - dx;
            if (newWidth > 150 && newWidth < 800) {
                usersPanelWidth = newWidth;
            }
        }
        function stopResize() {
            isResizing = false;
            window.removeEventListener('mousemove', handleResize);
            window.removeEventListener('mouseup', stopResize);
            document.body.classList.remove('resizing');
        }
        event.preventDefault();
        document.body.classList.add('resizing');
        window.addEventListener('mousemove', handleResize);
        window.addEventListener('mouseup', stopResize);
    }
    
    // Computed properties for user lists are unchanged, but now rely on derived state.
    let localUsers = [];
    let remoteUsers = [];
    $: {
        const allParticipants = roomParticipants || [];
        if (localHostname) {
            const localSuffix = `.${localHostname}`;
            localUsers = allParticipants
                .filter(p => !p.name.includes('.') || p.name.endsWith(localSuffix))
                .map(p => ({ ...p, displayName: p.name.endsWith(localSuffix) ? p.name.slice(0, -localSuffix.length) : p.name }))
                .sort((a, b) => a.displayName.localeCompare(b.displayName, undefined, { sensitivity: 'base' }));
            remoteUsers = allParticipants
                .filter(p => p.name.includes('.') && !p.name.endsWith(localSuffix))
                .map(p => ({ ...p, displayName: p.name }))
                .sort((a, b) => a.displayName.localeCompare(b.displayName, undefined, { sensitivity: 'base' }));
        } else {
            localUsers = allParticipants
                .filter(p => !p.name.includes('.'))
                .map(p => ({...p, displayName: p.name }))
                .sort((a, b) => a.displayName.localeCompare(b.displayName, undefined, { sensitivity: 'base' }));
            remoteUsers = allParticipants
                .filter(p => p.name.includes('.'))
                .map(p => ({...p, displayName: p.name }))
                .sort((a, b) => a.displayName.localeCompare(b.displayName, undefined, { sensitivity: 'base' }));
        }
    }

    // --- MODIFICATION: Remove ws instance ---
    let showSettings = false;
    let fsResponseUnsubscribe;
    let shouldScroll = true;
    
    // Color Handling is unchanged
    const colorNameToCss = {
        'black': 'var(--ansi-black)', 'red': 'var(--ansi-red)', 'green': 'var(--ansi-green)', 'yellow': 'var(--ansi-yellow)',
        'blue': 'var(--ansi-blue)', 'magenta': 'var(--ansi-magenta)', 'cyan': 'var(--ansi-cyan)', 'white': 'var(--ansi-white)',
        'bright_black': 'var(--ansi-bright-black)', 'bright_red': 'var(--ansi-bright-red)', 'bright_green': 'var(--ansi-bright-green)',
        'bright_yellow': 'var(--ansi-bright-yellow)', 'bright_blue': 'var(--ansi-bright-blue)', 'bright_magenta': 'var(--ansi-bright-magenta)',
        'bright_cyan': 'var(--ansi-bright-cyan)', 'bright_white': 'var(--ansi-bright-white)',
    };
    
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
    
    // handleClickOnTerminal is unchanged
    function handleClickOnTerminal() {
        if (window.getSelection().isCollapsed) {
            focusInput();
        }
    }
    
    // handleGlobalClick and handleGlobalKeyDown are mostly unchanged
    function handleGlobalClick(event) {
        if (showRoomsMenu && roomsButton && !roomsButton.contains(event.target)) {
            showRoomsMenu = false; focusInput();
        }
        if (showAttachMenu && attachButton && !event.target.closest('.attach-menu')) {
            showAttachMenu = false; focusInput();
        }
        if (userContextMenu.visible && !event.target.closest('.user-context-menu')) {
            closeUserContextMenu(); focusInput();
        }
    }
    function handleGlobalKeyDown(event) {
        if (event.key === 'Escape') {
            if (showAttachMenu) {
                showAttachMenu = false;
                focusInput();
            }
        }
    }
    $: if (showAttachMenu) { window.addEventListener('keydown', handleGlobalKeyDown); }
    else { window.removeEventListener('keydown', handleGlobalKeyDown); }
    
    onMount(() => {
        // --- MODIFICATION: Subscribe to file system responses for the attach menu ---
        fsResponseUnsubscribe = fileSystemResponses.subscribe(response => {
            if (!response || response.requesterId !== ATTACH_REQUEST_ID) return;

            const { data } = response;
            if (data.type === 'fs_list_response') {
                if (data.path === '/dev') {
                    let items = data.listing || [];
                    attachDevices = items
                        .filter(item => {
                            const basename = item.path.split('/').pop();
                            if (basename && basename.startsWith('.')) return false;
                            return !item.path.split('/').some(segment => segment.startsWith('_'));
                        })
                        .map(item => {
                            let displayPath = item.path.startsWith('/dev/') ? item.path.substring(5) : item.path;
                            if (item.type === 'file' && displayPath.endsWith('.py')) { displayPath = displayPath.slice(0, -3); }
                            if (displayPath.endsWith('/')) { displayPath = displayPath.slice(0, -1); }
                            return { displayName: displayPath || '/', fullPath: item.path, type: item.type };
                        })
                        .sort((a, b) => a.displayName.localeCompare(b.displayName));
                    isLoadingDevices = false;
                } else if (data.path === '/home') {
                    attachUsers = (data.listing || []).filter(item => item.type === 'dir');
                    isLoadingUsers = false;
                }
            }
        });
        window.addEventListener('click', handleGlobalClick);
    });

    onDestroy(() => {
        if (fsResponseUnsubscribe) fsResponseUnsubscribe();
        window.removeEventListener('click', handleGlobalClick);
        window.removeEventListener('keydown', handleGlobalKeyDown);
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
    
    // User Context Menu Functions (mostly unchanged, just use connectionId)
    function handleUserRightClick(event, participant) {
        event.preventDefault(); event.stopPropagation();
        showRoomsMenu = false; showAttachMenu = false;
        const { x, y } = calculateWindowContextMenuPosition(event);
        userContextMenu = { visible: true, x, y, user: participant };
    }
    function closeUserContextMenu() { userContextMenu = { visible: false, x: 0, y: 0, user: null }; }

    function sendSystemCommand(systemCommand) {
        if (!systemCommand.trim()) return;
        if (connectionId) {
            sendIoskCommand(connectionId, systemCommand);
        }
        shouldScroll = true;
    }
    function openPrivateChat(remoteParticipant) {
        if (!remoteParticipant || !connectionId) return;
        newIoskPrivateChat({ connectionId, localUser: connectionState.username, remoteUser: remoteParticipant });
        closeUserContextMenu();
        focusInput();
    }
    function viewUserLog(user) {
        if (!user || !connectionId) return;
        const usernameOnly = user.split('.')[0];
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const dateString = `${year}-${month}-${day}`;
        const logPath = `/var/log/user/${usernameOnly}/${dateString}.log`;
        newIoskFileViewer({ connectionId, path: logPath });
        closeUserContextMenu();
        focusInput();
    }
    function inspectUserContext(targetUser) {
        if (!connectionId) return;
        newIoskUserInspector({ connectionId, targetUser });
        sendIoskRequest(connectionId, { type: 'ui_context_subscribe', targetUser });
        closeUserContextMenu();
    }
    function handleSetColor(event) {
        const colorName = event.detail;
        if (!userContextMenu.user) return;
        const commandToRun = `$ color -u ${userContextMenu.user} ${colorName}`;
        sendSystemCommand(commandToRun);
        closeUserContextMenu();
        focusInput();
    }
    function handleDetachUser(user) {
        if (!user) return;
        const commandToRun = `$ detach ${user}`;
        sendSystemCommand(commandToRun);
        closeUserContextMenu();
        focusInput();
    }
    
    // Tooltip functions (showTokenTooltip, hideTokenTooltip) are unchanged
    function showTokenTooltip(event, user) {
        const rect = event.currentTarget.getBoundingClientRect();
        tokenTooltip = { visible: true, x: rect.right, y: rect.bottom + 5, user: user };
    }
    function hideTokenTooltip() { tokenTooltip = { ...tokenTooltip, visible: false }; }

    function togglePause(participant) {
        if (!participant || !participant.is_bot) return;
        const command = participant.paused ? `unpause ${participant.name}` : `pause ${participant.name}`;
        sendSystemCommand(`$ ${command}`);
        focusInput();
    }
    
    // handlePanelClick is unchanged
    function handlePanelClick(event) {
        if (isUsersPanelCollapsed) { isUsersPanelCollapsed = false; }
        else if (event.target.classList.contains('user-list')) { isUsersPanelCollapsed = true; }
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

    // --- MODIFICATION: request functions now use sendIoskRequest ---
    function requestFsList(path) {
        if (!connectionId) return;
        sendIoskRequest(connectionId, { type: 'fs_list', path, requesterId: ATTACH_REQUEST_ID });
    }
    function requestAllDevices() {
        if (!connectionId) return;
        sendIoskRequest(connectionId, { type: 'fs_list', path: '/dev', recursive: true, requesterId: ATTACH_REQUEST_ID });
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
            disconnectSession(connectionId);
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

    // --- MODIFICATION: Room/logout actions use sendSystemCommand ---
    function joinRoom(roomToJoin) { sendSystemCommand(`$ join ${roomToJoin}`); showRoomsMenu = false; focusInput(); }
    function closeRoom() { sendSystemCommand('$ close'); showRoomsMenu = false; focusInput(); }
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

    // toggleRoomsMenu is unchanged
    export function toggleRoomsMenu() { showRoomsMenu = !showRoomsMenu; }
    
    // toggleAttachMenu is unchanged, but position calc is important
    export function toggleAttachMenu(event) {
        showAttachMenu = !showAttachMenu;
        if (showAttachMenu) {
            const menuDimensions = { width: 240, height: 350 };
            let positionEvent = event;
            if (!positionEvent && attachButton) {
                const rect = attachButton.getBoundingClientRect();
                positionEvent = { target: attachButton, clientX: rect.left, clientY: rect.bottom };
            }
            if (!positionEvent) { console.error("Could not determine position for Attach menu."); showAttachMenu = false; return; }
            const { x, y } = calculateWindowContextMenuPosition(positionEvent, menuDimensions, { preferredX: 'left' });
            attachMenuPosition = { x, y };
        }
    }
    
    // requestAttachData is unchanged
    function requestAttachData() {
        if (showAttachMenu) {
            if (attachDevices.length === 0) { isLoadingDevices = true; requestAllDevices(); }
            if (attachUsers.length === 0) { isLoadingUsers = true; requestFsList('/home'); }
        }
    }

    // handleAttach now uses sendSystemCommand
    function handleAttach(event) {
        const { device, user } = event.detail;
        if (!device) return;
        const finalUser = user.trim();
        const commandToRun = finalUser ? `$ attach ${device} ${finalUser}` : `$ attach ${device}`;
        sendSystemCommand(commandToRun);
        showAttachMenu = false;
        focusInput();
    }
    
    // Bell sound/notice logic is removed, as it's handled centrally.
    
    // --- MODIFICATION: Watch Window Function now passes connectionId ---
    function launchWatchWindow() {
        if (!connectionId) return;
        const match = currentPrompt.match(/\[\S+\s+([^\]]+)\]/);
        const pwd = match ? match[1] : '/';
        newIoskWatch({ connectionId, path: pwd });
        focusInput();
    }

</script>

<!-- MODIFICATION: Main container now has an outer if/else for connection state -->
<div class="console-container">
    {#if !connectionId}
        <!-- Initial Screen: Attach to existing or create new connection -->
        <div class="initial-screen">
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
            <button type="button" class="header-button disconnect-button" on:click={disconnect} title="Disconnect session and return to connection picker.">Disconnect</button>
            <button type="button" class="header-button room-button" bind:this={roomsButton} on:click|stopPropagation={toggleRoomsMenu} title="Available Rooms" disabled={!isConnected}>Rooms</button>
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

        {#if showAttachMenu}
            <div class="attach-menu-wrapper attach-menu" style="position: fixed; top: {attachMenuPosition.y}px; left: {attachMenuPosition.x}px;">
                <AttachMenu
                    {isLoadingDevices}
                    {attachDevices}
                    {isLoadingUsers}
                    {attachUsers}
                    on:requestData={requestAttachData}
                    on:attach={handleAttach}
                />
            </div>
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

            {#if isConnected && roomName}
            <div class="users-panel" style="--panel-width: {usersPanelWidth}px" class:collapsed={isUsersPanelCollapsed} on:click={handlePanelClick}>
                {#if !isUsersPanelCollapsed}
                    <div class="users-panel-resizer" on:mousedown={startResize}></div>
                {/if}
                <div class="panel-header">
                    {#if !isUsersPanelCollapsed}
                        <span>Users</span>
                    {/if}
                    <div class="panel-header-controls">
                        {#if !isUsersPanelCollapsed}
                            <button class="attach-button" bind:this={attachButton} on:click|stopPropagation={(e) => toggleAttachMenu(e)} title="Attach Device/User">Attach</button>
                        {/if}
                        <button class="collapse-toggle-button" on:click|stopPropagation={() => isUsersPanelCollapsed = !isUsersPanelCollapsed} title={isUsersPanelCollapsed ? 'Expand' : 'Collapse'}>
                            {isUsersPanelCollapsed ? '❮' : '❯'}
                        </button>
                    </div>
                </div>
                {#if !isUsersPanelCollapsed}
                    <div class="user-list">
                        {#each localUsers as participant (participant.name)}
                            <div
                                class="user-item"
                                title={participant.name}
                                on:contextmenu={(e) => handleUserRightClick(e, participant.name)}
                                on:click={() => openPrivateChat(participant.name)}
                            >
                                <span class="user-name-display" class:paused={participant.paused} style="color: {colorNameToCss[userColors[participant.name]] || 'inherit'}">{participant.displayName}</span>
                                {#if participant.is_bot}
                                    <span class="user-item-filler"></span>
                                    {#if userTokenStats[participant.name]}
                                        {@const stats = userTokenStats[participant.name]}
                                        <div class="token-count-wrapper"
                                             on:mouseenter={(e) => showTokenTooltip(e, participant.name)}
                                             on:mouseleave={hideTokenTooltip}>
                                            <span class="last-trip-token-count" title="Last trip input tokens">{abbreviateNumber(stats.last_trip_input_tokens)}</span>
                                            <span style="color: var(--ansi-bright-black); margin: 0 3px;">/</span>
                                            <span class="token-count" title="Cumulative input tokens">{abbreviateNumber(stats.cumulative_input_tokens)}</span>
                                        </div>
                                    {/if}
                                    <button class="pause-resume-button" on:click|stopPropagation={() => togglePause(participant)} title={participant.paused ? `Resume ${participant.displayName}` : `Pause ${participant.displayName}`}>{participant.paused ? '▶' : '⏸'}</button>
                                {/if}
                            </div>
                        {/each}
                        {#if localUsers.length > 0 && remoteUsers.length > 0}
                            <div class="menu-separator" style="margin: 4px 0;"></div>
                        {/if}
                        {#each remoteUsers as participant (participant.name)}
                            <div
                                class="user-item"
                                title={participant.name}
                                on:contextmenu={(e) => handleUserRightClick(e, participant.name)}
                                on:click={() => openPrivateChat(participant.name)}
                            >
                                <span class="user-name-display" class:paused={participant.paused} style="color: {colorNameToCss[userColors[participant.name]] || 'inherit'}">{participant.displayName}</span>
                                {#if participant.is_bot}
                                    <span class="user-item-filler"></span>
                                    {#if userTokenStats[participant.name]}
                                        {@const stats = userTokenStats[participant.name]}
                                         <div class="token-count-wrapper" on:mouseenter={(e) => showTokenTooltip(e, participant.name)} on:mouseleave={hideTokenTooltip}>
                                            <span class="last-trip-token-count" title="Last trip input tokens">{abbreviateNumber(stats.last_trip_input_tokens)}</span>
                                            <span style="color: var(--ansi-bright-black); margin: 0 3px;">/</span>
                                            <span class="token-count" title="Cumulative input tokens">{abbreviateNumber(stats.cumulative_input_tokens)}</span>
                                        </div>
                                    {/if}
                                    <button class="pause-resume-button" on:click|stopPropagation={() => togglePause(participant)} title={participant.paused ? `Resume ${participant.displayName}` : `Pause ${participant.displayName}`}>{participant.paused ? '▶' : '⏸'}</button>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {:else}
                    <div class="collapsed-user-counts" title="Click to expand Users panel">
                        <div title={"Local Users:\n" + localUsers.map(u => u.displayName).join('\n')}>{localUsers.length}</div>
                        {#if remoteUsers.length > 0}
                            <div class="collapsed-count-separator"></div>
                            <div class="remote-user-count" title={"Remote Users:\n" + remoteUsers.map(u => u.displayName).join('\n')}>{remoteUsers.length}</div>
                        {/if}
                    </div>
                {/if}
            </div>
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

    {#if userContextMenu.visible}
        <UserContextMenu
            x={userContextMenu.x}
            y={userContextMenu.y}
            user={userContextMenu.user}
            {colorNameToCss}
            on:inspectContext={e => inspectUserContext(e.detail)}
            on:privateChat={e => openPrivateChat(e.detail)}
            on:viewLog={e => viewUserLog(e.detail)}
            on:setColor={handleSetColor}
            on:detach={e => handleDetachUser(e.detail)}
        />
    {/if}

    {#if tokenTooltip.visible && tokenTooltip.user && userTokenStats[tokenTooltip.user]}
        {@const stats = userTokenStats[tokenTooltip.user]}
        <div class="token-tooltip" style="top: {tokenTooltip.y}px; left: {tokenTooltip.x}px; transform: translateX(-100%);">
            <div class="tooltip-grid">
                <span>Cumulative Input:</span><span>({formatBytes(stats.cumulative_input_bytes)})</span><span>{stats.cumulative_input_tokens.toLocaleString('en-US')} tokens</span>
                <span>Cumulative Output:</span><span>({formatBytes(stats.cumulative_output_bytes)})</span><span>{stats.cumulative_output_tokens.toLocaleString('en-US')} tokens</span>
                <span>Last Trip Input:</span><span>({formatBytes(stats.last_trip_input_bytes)})</span><span>{stats.last_trip_input_tokens.toLocaleString('en-US')} tokens</span>
                <span>Last Trip Output:</span><span>({formatBytes(stats.last_trip_output_bytes)})</span><span>{stats.last_trip_output_tokens.toLocaleString('en-US')} tokens</span>
                <span>Banked Memory:</span><span>({formatBytes(stats.banked_bytes)})</span><span>{stats.banked_tokens.toLocaleString('en-US')} tokens</span>
                <span>Session History:</span><span>({formatBytes(stats.history_bytes)})</span><span>{stats.history_tokens.toLocaleString('en-US')} tokens</span>
                <span>Caching Context:</span><span>({formatBytes(stats.caching_context_bytes)})</span><span>{stats.caching_context_tokens.toLocaleString('en-US')} tokens</span>
            </div>
        </div>
    {/if}
</div>

<style>
    /* Add styles for the new initial screen */
    .initial-screen {
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 15px;
        height: 100%;
        overflow-y: auto;
    }
    .initial-screen h3 {
        margin: 0;
        font-weight: 500;
        color: var(--title-bar-text);
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 8px;
    }
    .connection-list {
        display: flex;
        flex-direction: column;
        gap: 5px;
        max-height: 200px;
        overflow-y: auto;
    }
    .no-connections {
        color: #95a5a6;
        font-style: italic;
        padding: 10px 0;
    }
    .connection-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background-color: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        cursor: pointer;
        border-radius: 3px;
        text-align: left;
    }
    .connection-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .conn-id {
        font-family: monospace;
        font-size: 0.9em;
    }
    .conn-status {
        font-weight: bold;
        font-size: 0.8em;
        text-transform: uppercase;
        padding: 2px 5px;
        border-radius: 3px;
    }
    .conn-status.connected { color: #2ecc71; }
    .conn-status.connecting { color: #f39c12; }
    .conn-status.disconnected { color: #95a5a6; }
    .conn-status.error { color: #e74c3c; }
    .separator {
        display: flex;
        align-items: center;
        text-align: center;
        color: #7f8c8d;
        margin: 10px 0;
    }
    .separator::before, .separator::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid var(--border-color);
    }
    .separator:not(:empty)::before { margin-right: .25em; }
    .separator:not(:empty)::after { margin-left: .25em; }

    /* --- Existing Styles --- */
    :global(body.resizing) { cursor: col-resize !important; user-select: none; }
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
    .connect-form .room-button { background-color: #ffbd2e; border-color: #e0a320; color: white; position: relative; padding-left: 15px; }
    .connect-form .room-button:hover { background-color: #e0a320; }
    .connect-form .watch-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .connect-form .watch-button:hover { background-color: #1a9c2a; }
    .connect-form .files-button { background-color: #3498db; border-color: #2980b9; color: white; }
    .connect-form .files-button:hover { background-color: #2980b9; }

    .connect-form .room-button::before { content: ''; position: absolute; top: 50%; transform: translateY(-50%); width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 4px solid rgba(255, 255, 255, 0.7); left: 5px; }
    .header-info { flex-grow: 1; text-align: center; color: #bdc3c7; font-style: italic; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; padding: 0 10px; }
    .main-flex-area { flex-grow: 1; display: flex; overflow: hidden; height: 100%; position: relative; } /* Fix for flexbox height issue */
    .terminal-wrapper { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; height: 100%; }
    .terminal { flex-grow: 1; overflow-y: auto; padding: 8px; white-space: pre-wrap; word-break: break-all; }
    .terminal-line.prompt { color: var(--console-prompt); }
    .input-area { display: flex; padding: 4px 8px; background-color: var(--title-bar-bg); border-top: 1px solid var(--border-color); flex-shrink: 0; }
    .input-area span { color: var(--console-prompt); padding-right: 5px; white-space: pre; }
    .input-area input { flex-grow: 1; background: transparent; border: none; outline: none; color: var(--console-input); font-family: inherit; font-size: inherit; }
    .users-panel { width: var(--panel-width, 260px); flex-shrink: 0; border-left: 1px solid var(--border-color); display: flex; flex-direction: column; position: relative; transition: width 0.15s ease-out; }
    .users-panel.collapsed { width: 32px; }
    .users-panel-resizer { position: absolute; top: 0; left: -3px; width: 6px; height: 100%; cursor: col-resize; z-index: 10; }
    .panel-header { padding: 4px 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); font-weight: bold; display: flex; justify-content: space-between; align-items: center; overflow: hidden; flex-shrink: 0; }
    .panel-header-controls { display: flex; align-items: center; margin-left: auto; }
    .collapse-toggle-button { background: none; border: none; color: var(--title-bar-text); cursor: pointer; font-size: 1.4em; padding: 0 4px; line-height: 1; opacity: 0.7; transition: opacity 0.2s; height: 100%; }
    .collapse-toggle-button:hover { opacity: 1; }
    .panel-header .attach-button { background-color: #9b59b6; border: 1px solid #8e44ad; color: white; padding: 2px 6px; font-size: 0.9em; cursor: pointer; border-radius: 3px; position: relative; padding-right: 15px; margin-right: 4px; }
    .panel-header .attach-button:hover { background-color: #8e44ad; }
    .panel-header .attach-button::after { content: ''; position: absolute; top: 50%; transform: translateY(-50%); width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 4px solid rgba(255, 255, 255, 0.7); right: 5px; }
    .user-list { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .collapsed-user-counts { display: flex; flex-direction: column; align-items: center; flex-grow: 1; padding-top: 8px; color: var(--title-bar-text); font-weight: bold; font-size: 1.1em; cursor: pointer; user-select: none; }
    .collapsed-count-separator { width: 60%; height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .remote-user-count { color: var(--ansi-cyan); }
    .user-item { padding: 2px 6px; cursor: pointer; border-radius: 2px; display: flex; align-items: center; }
    .user-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .user-name-display { flex-shrink: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .user-name-display.paused { font-style: italic; }
    .user-item-filler { flex-grow: 1; border-bottom: 1px dotted #7f8c8d; margin: 0 4px; position: relative; top: -4px; }
    .token-count-wrapper { position: relative; flex-shrink: 0; display: flex; align-items: center; }
    .token-count { font-weight: bold; color: var(--ansi-yellow); }
    .last-trip-token-count { font-weight: bold; color: var(--ansi-cyan); }
    .token-tooltip { position: fixed; background-color: var(--window-bg); border: 1px solid var(--border-color); padding: 8px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 210; width: max-content; font-size: 12px; color: var(--console-text); text-align: left; white-space: nowrap; pointer-events: none; }
    .tooltip-grid { display: grid; grid-template-columns: auto max-content max-content; gap: 4px 12px; align-items: center; }
    .tooltip-grid span:nth-child(3n-2) { font-weight: bold; text-align: right; color: var(--title-bar-text); }
    .tooltip-grid span:nth-child(3n-1) { text-align: right; color: var(--ansi-bright-black); }
    .tooltip-grid span:nth-child(3n) { text-align: right; }
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
    .pause-resume-button { background: none; border: none; cursor: pointer; padding: 0 4px; font-size: 1.1em; margin-left: 4px; line-height: 1; opacity: 0.6; transition: opacity 0.2s; }
    .pause-resume-button:hover { opacity: 1; }
    .menu-separator { height: 3px; background-color: var(--border-color); margin: 0; }
    .attach-menu-wrapper { z-index: 200; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
</style>

