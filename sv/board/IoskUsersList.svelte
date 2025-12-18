<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { newIoskFileViewer, newIoskPrivateChat, newIoskUserInspector } from '../apps.js';
    import { sendCommand as sendIoskCommand, sendRequest as sendIoskRequest, fileSystemResponses } from '../iosk.js';
    import { calculateWindowContextMenuPosition } from '../desktop.js';
    import AttachMenu from './popup/AttachMenu.svelte';
    import UserContextMenu from './popup/UserContextMenu.svelte';

    // Props from parent component (e.g., IoskConsole.svelte)
    export let connectionId;
    export let localUser;
    export let localHostname;
    export let roomParticipants = [];
    export let userColors = {};
    export let userTokenStats = {};

    // Bindable UI state, allowing parent to persist it
    export let usersPanelWidth = 260;
    export let isUsersPanelCollapsed = true;

    // Internal state
    let isResizing = false;

    // Attach Menu state
    let showAttachMenu = false;
    let attachDevices = [];
    let attachUsers = [];
    let isLoadingDevices = false;
    let isLoadingUsers = false;
    let attachMenuPosition = { x: 0, y: 0 };
    const ATTACH_REQUEST_ID = `userlist-attach-${Math.random().toString(36).substring(2, 9)}`;
    let attachButton;

    // User Context Menu state
    let userContextMenu = { visible: false, x: 0, y: 0, user: null };

    // Token Telemetry state
    let tokenTooltip = { visible: false, x: 0, y: 0, user: null };

    // Helper functions for telemetry display
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

    // Panel resize logic
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

    // Computed properties for user lists
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

    const colorNameToCss = {
        'black': 'var(--ansi-black)', 'red': 'var(--ansi-red)', 'green': 'var(--ansi-green)', 'yellow': 'var(--ansi-yellow)',
        'blue': 'var(--ansi-blue)', 'magenta': 'var(--ansi-magenta)', 'cyan': 'var(--ansi-cyan)', 'white': 'var(--ansi-white)',
        'bright_black': 'var(--ansi-bright-black)', 'bright_red': 'var(--ansi-bright-red)', 'bright_green': 'var(--ansi-bright-green)',
        'bright_yellow': 'var(--ansi-bright-yellow)', 'bright_blue': 'var(--ansi-bright-blue)', 'bright_magenta': 'var(--ansi-bright-magenta)',
        'bright_cyan': 'var(--ansi-bright-cyan)', 'bright_white': 'var(--ansi-bright-white)',
    };

    function handleGlobalClick(event) {
        if (showAttachMenu && attachButton && !event.target.closest('.attach-menu')) {
            showAttachMenu = false;
        }
        if (userContextMenu.visible && !event.target.closest('.user-context-menu')) {
            closeUserContextMenu();
        }
    }

    let fsResponseUnsubscribe;
    onMount(() => {
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
    });

    // --- User Context Menu Functions ---
    function handleUserRightClick(event, participant) {
        event.preventDefault(); event.stopPropagation();
        showAttachMenu = false;
        const { x, y } = calculateWindowContextMenuPosition(event);
        userContextMenu = { visible: true, x, y, user: participant };
    }
    function closeUserContextMenu() { userContextMenu = { visible: false, x: 0, y: 0, user: null }; }

    function sendSystemCommand(systemCommand) {
        if (!systemCommand.trim() || !connectionId) return;
        sendIoskCommand(connectionId, systemCommand);
    }
    function openPrivateChat(remoteParticipant) {
        if (!remoteParticipant || !connectionId || !localUser) return;
        newIoskPrivateChat({ connectionId, localUser, remoteUser: remoteParticipant });
        closeUserContextMenu();
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
        sendSystemCommand(`$ color -u ${userContextMenu.user} ${colorName}`);
        closeUserContextMenu();
    }
    function handleDetachUser(user) {
        if (!user) return;
        sendSystemCommand(`$ detach ${user}`);
        closeUserContextMenu();
    }

    function showTokenTooltip(event, user) {
        const rect = event.currentTarget.getBoundingClientRect();
        tokenTooltip = { visible: true, x: rect.right, y: rect.bottom + 5, user: user };
    }
    function hideTokenTooltip() { tokenTooltip = { ...tokenTooltip, visible: false }; }

    function togglePause(participant) {
        if (!participant || !participant.is_bot) return;
        const command = participant.paused ? `unpause ${participant.name}` : `pause ${participant.name}`;
        sendSystemCommand(`$ ${command}`);
    }

    function handlePanelClick(event) {
        if (isUsersPanelCollapsed) { isUsersPanelCollapsed = false; }
        else if (event.target.classList.contains('user-list')) { isUsersPanelCollapsed = true; }
    }

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

    function requestAttachData() {
        if (showAttachMenu && connectionId) {
            if (attachDevices.length === 0) {
                isLoadingDevices = true;
                sendIoskRequest(connectionId, { type: 'fs_list', path: '/dev', recursive: true, requesterId: ATTACH_REQUEST_ID });
            }
            if (attachUsers.length === 0) {
                isLoadingUsers = true;
                sendIoskRequest(connectionId, { type: 'fs_list', path: '/home', requesterId: ATTACH_REQUEST_ID });
            }
        }
    }

    function handleAttach(event) {
        const { device, user } = event.detail;
        if (!device) return;
        const finalUser = user.trim();
        const commandToRun = finalUser ? `$ attach ${device} ${finalUser}` : `$ attach ${device}`;
        sendSystemCommand(commandToRun);
        showAttachMenu = false;
    }
</script>

<svelte:window on:close-all-context-menus={() => { showAttachMenu = false; closeUserContextMenu(); }} />

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
                <div class="user-item" title={participant.name} on:contextmenu={(e) => handleUserRightClick(e, participant.name)} on:click={() => openPrivateChat(participant.name)}>
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
            {#if localUsers.length > 0 && remoteUsers.length > 0}
                <div class="menu-separator" style="margin: 4px 0;"></div>
            {/if}
            {#each remoteUsers as participant (participant.name)}
                <div class="user-item" title={participant.name} on:contextmenu={(e) => handleUserRightClick(e, participant.name)} on:click={() => openPrivateChat(participant.name)}>
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

<style>
    :global(body.resizing) { cursor: col-resize !important; user-select: none; }
    .users-panel { width: var(--panel-width, 260px); flex-shrink: 0; border-left: 1px solid var(--border-color); display: flex; flex-direction: column; position: relative; transition: width 0.15s ease-out; background-color: var(--console-bg); }
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
    .user-name-display { flex-shrink: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--console-text); }
    .user-name-display.paused { font-style: italic; }
    .user-item-filler { flex-grow: 1; border-bottom: 1px dotted #7f8c8d; margin: 0 4px; position: relative; top: -4px; }
    .token-count-wrapper { position: relative; flex-shrink: 0; display: flex; align-items: center; }
    .token-count { font-weight: bold; color: var(--ansi-yellow); }
    .last-trip-token-count { font-weight: bold; color: var(--ansi-cyan); }
    .token-tooltip { position: fixed; background-color: var(--window-bg); border: 1px solid var(--border-color); padding: 8px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 21001; width: max-content; font-size: 12px; color: var(--console-text); text-align: left; white-space: nowrap; pointer-events: none; }
    .tooltip-grid { display: grid; grid-template-columns: auto max-content max-content; gap: 4px 12px; align-items: center; }
    .tooltip-grid span:nth-child(3n-2) { font-weight: bold; text-align: right; color: var(--title-bar-text); }
    .tooltip-grid span:nth-child(3n-1) { text-align: right; color: var(--ansi-bright-black); }
    .tooltip-grid span:nth-child(3n) { text-align: right; }
    .pause-resume-button { background: none; border: none; cursor: pointer; padding: 0 4px; font-size: 1.1em; margin-left: 4px; line-height: 1; opacity: 0.6; transition: opacity 0.2s; color: var(--title-bar-text); }
    .pause-resume-button:hover { opacity: 1; }
    .menu-separator { height: 3px; background-color: var(--border-color); margin: 0; }
    .attach-menu-wrapper { z-index: 21000; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
</style>