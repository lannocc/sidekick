<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate, tick } from 'svelte';
    import { windows, newIoskFileExplorer } from './windows.js';
    import { fileSystemRequests, fileSystemResponses } from './ioskEvents.js';
    import { desktopSettings } from './desktopStore.js';

    export let id; // Unique ID from the window manager
    export let title;
    export let isActive;
    export let isConsoleConnected; // Received from the store

    // --- State for Connection & Room Awareness ---
    let wsUrl;
    let username;
    let isConnected = false;
    let roomName = null;
    let roomTopic = '';
    let motd = '';
    let roomParticipants = [];

    // --- Internal Component State ---
    let output = []; // Array of { type: 'prompt'|'output', content: 'text' }
    let command = '';
    let commandHistory = [];
    let historyIndex = 0;
    let unsentCommand = '';
    let currentPrompt = '';

    // --- DOM element refs ---
    let terminalEl;
    let commandInput;
    let settingsUrlInput;

    // --- WebSocket instance for this specific console window ---
    let ws = null;
    const PREAMBLE = "SK1:";

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsUrl, settingsUsername;

    // --- Event bus subscriptions ---
    let requestUnsubscribe;

    // --- Auto-scrolling logic ---
    let shouldScroll = true;

    // --- Lifecycle and Reactive Statements ---
    afterUpdate(() => {
        if (shouldScroll && terminalEl) {
            terminalEl.scrollTop = terminalEl.scrollHeight;
        }
    });

    onMount(() => {
        // Automatically focus the connection URL input on mount
        if (!isConnected) {
            const urlInput = document.querySelector(`#url-input-${id}`);
            urlInput?.focus();
        }
        // Listen for file system requests from explorer windows
        requestUnsubscribe = fileSystemRequests.subscribe(request => {
            if (request && request.consoleId === id && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(request.command));
            }
        });
    });

    onDestroy(() => {
        if (ws) {
            ws.onclose = null; // prevent onclose handler from running on manual close
            ws.close();
        }
        if (requestUnsubscribe) {
            requestUnsubscribe();
        }
    });

    desktopSettings.subscribe(settings => {
        // Only update local details if we are NOT connected.
        if (!isConnected) {
            wsUrl = settings.ioskUrl;
            username = settings.ioskUsername;
        }
    });

    // Reactive statement to update the window store with the connection status
    $: if (id !== undefined) {
        windows.updateWindowProps(id, { isConsoleConnected: isConnected });
    }

    // Reactive statement to update the window title based on connection and room state
    $: if (id !== undefined && title !== undefined) {
        let newTitle;
        if (isConsoleConnected) {
            const host = (() => { try { return new URL(wsUrl).hostname } catch { return 'invalid-host' }})();
            const userAtHost = `${username}@${host}`;
            newTitle = roomName ? `[${roomName}] ${userAtHost}` : userAtHost;
        } else {
            // Let onclose/onerror handlers manage the disconnected title.
            // This prevents this block from overriding an error state title.
            newTitle = title;
        }
        if (newTitle !== title) {
            windows.updateWindowProps(id, { title: newTitle });
        }
    }


    // --- Functions ---
    export function showSettingsDialog() {
        if (isConnected) return;
        settingsUrl = wsUrl;
        settingsUsername = username;
        showSettings = true;
        tick().then(() => settingsUrlInput?.focus());
    }

    function handleSaveSettings() {
        wsUrl = settingsUrl;
        username = settingsUsername;
        showSettings = false;
        desktopSettings.update(settings => ({ ...settings, ioskUrl: wsUrl, ioskUsername: username }));
    }

    function handleCancelSettings() {
        showSettings = false;
    }

    function handleSettingsKeydown(e) {
        if (e.key === 'Escape') handleCancelSettings();
        else if (e.key === 'Enter') {
            e.preventDefault();
            handleSaveSettings();
        }
    }

    export async function connect() {
        if (ws) {
            output = [...output, {type: 'output', content: `Already connected or connecting.`}];
            return;
        }
        output = [...output, {type: 'output', content: `Connecting to ${wsUrl} as ${username}...`}];

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                isConnected = true;
                output = [...output, {type: 'output', content: `Connected.`}];
                const handshake = { type: 'handshake', id: 'client', user: username };
                ws.send(JSON.stringify(handshake));
                setTimeout(() => commandInput?.focus(), 100);
            };

            ws.onmessage = (event) => {
                if (typeof event.data === 'string' && event.data.startsWith(PREAMBLE)) {
                    try {
                        const jsonData = event.data.substring(PREAMBLE.length);
                        const data = JSON.parse(jsonData);

                        if (data.type === 'state_info') {
                            roomName = data.roomName || null;
                            roomTopic = data.roomTopic || '';
                            roomParticipants = data.participants || [];
                            motd = data.motd || '';
                        } else if (data.type === 'room_state_update') {
                            roomName = data.roomName || null;
                            roomTopic = data.roomTopic || '';
                            roomParticipants = data.participants || [];
                            if (!roomName) motd = '';
                        } else if (data.output || data.prompt) {
                            if (data.output) {
                                const clearScreenCode = "\x1b[H\x1b[2J";
                                if (data.output === clearScreenCode) {
                                    output = [];
                                } else {
                                    const lines = data.output.split('\n');
                                    output = [...output, ...lines.map(line => ({type: 'output', content: line}))];
                                }
                            }
                            if (data.prompt) {
                                currentPrompt = data.prompt;
                            }
                        } else if (data.type === 'fs_list_response') {
                            fileSystemResponses.set({ consoleId: id, data: data, timestamp: Date.now() });
                        }
                    } catch (e) {
                        console.error("Error parsing WebSocket message:", e);
                        output = [...output, {type: 'output', content: `[Error] Could not parse message from server.`}];
                    }
                }
            };

            ws.onclose = async () => {
                isConnected = false;
                ws = null;
                roomName = null; roomTopic = ''; motd = ''; roomParticipants = [];
                output = [...output, {type: 'output', content: `Connection closed.`}];
                const host = (() => { try { return new URL(wsUrl).hostname } catch { return 'invalid-host' }})();
                windows.updateWindowProps(id, { title: `[Disconnected] ${username}@${host}` });
                if (isActive) {
                    await tick();
                    const urlInput = document.querySelector(`#url-input-${id}`);
                    urlInput?.focus();
                }
            };

            ws.onerror = (error) => {
                isConnected = false;
                if (ws) { ws.close(); ws = null; }
                output = [...output, {type: 'output', content: `[Error] Could not establish connection to ${wsUrl}.`}];
                const host = (() => { try { return new URL(wsUrl).hostname } catch { return 'invalid-host' }})();
                windows.updateWindowProps(id, { title: `[Error] ${username}@${host}` });
            };

        } catch (e) {
            console.error("Failed to create WebSocket:", e);
            output = [...output, {type: 'output', content: `[Error] Failed to create WebSocket: ${e.message}`}];
        }
    }

    export function disconnect() {
        if (ws) ws.close();
    }

    function sendCommand() {
        if (!command.trim()) return;
        const fullCommand = command;
        output = [...output, {type: 'prompt', content: currentPrompt + fullCommand}];
        if (commandHistory.length === 0 || commandHistory[commandHistory.length - 1] !== fullCommand) {
            commandHistory = [...commandHistory, fullCommand];
        }
        historyIndex = commandHistory.length;
        unsentCommand = '';
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'client_input', data: fullCommand + '\n' };
            ws.send(JSON.stringify(message));
        } else {
            output = [...output, {type: 'output', content: `[Error] Not connected.`}];
        }
        command = '';
        shouldScroll = true;
    }

    function sendLogout() {
        let logoutCommand = 'logout';
        if (currentPrompt.trim().endsWith('>>')) logoutCommand = '$ logout';
        output = [...output, {type: 'prompt', content: currentPrompt + logoutCommand}];
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'client_input', data: logoutCommand + '\n' }));
        } else {
            output = [...output, {type: 'output', content: `[Error] Not connected.`}];
        }
        command = ''; unsentCommand = ''; historyIndex = commandHistory.length; shouldScroll = true;
    }

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
</script>

<style>
    .console-container { display: flex; flex-direction: column; height: 100%; background-color: var(--console-bg); color: var(--console-text); font-family: 'Courier New', Courier, monospace; font-size: 14px; position: relative; }
    .connect-form { display: flex; gap: 8px; padding: 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); flex-shrink: 0; align-items: center; }
    .connect-form input { flex-grow: 1; background-color: var(--window-bg); color: var(--title-bar-text); border: 1px solid var(--border-color); padding: 4px; }
    .connect-form .connect-button { background-color: #27c93f; border: 1px solid #1a9c2a; color: white; padding: 4px 8px; cursor: pointer; border-radius: 3px; }
    .connect-form .header-button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 4px 8px; cursor: pointer; border-radius: 3px; }
    .connect-form .header-button:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .connect-form .header-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .connect-form .disconnect-button { background-color: #e74c3c; border-color: #c0392b; color: white; }
    .connect-form .disconnect-button:hover { background-color: #c0392b; }
    .header-info { flex-grow: 1; text-align: center; color: #bdc3c7; font-style: italic; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; padding: 0 10px; }
    .main-flex-area { flex-grow: 1; display: flex; overflow: hidden; }
    .terminal-wrapper { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
    .terminal { flex-grow: 1; overflow-y: auto; padding: 8px; white-space: pre-wrap; word-break: break-all; }
    .terminal-line.prompt { color: var(--console-prompt); }
    .input-area { display: flex; padding: 4px 8px; background-color: var(--title-bar-bg); border-top: 1px solid var(--border-color); flex-shrink: 0; }
    .input-area span { color: var(--console-prompt); padding-right: 5px; white-space: pre; }
    .input-area input { flex-grow: 1; background: transparent; border: none; outline: none; color: var(--console-input); font-family: inherit; font-size: inherit; }
    .users-panel { width: 180px; flex-shrink: 0; border-left: 1px solid var(--border-color); display: flex; flex-direction: column; }
    .panel-header { padding: 4px 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); font-weight: bold; text-align: center; }
    .user-list { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .user-item { padding: 2px 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 400px; display: flex; flex-direction: column; gap: 15px; }
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

<div class="console-container">
    <form class="connect-form" on:submit|preventDefault={connect}>
        {#if !isConnected}
            <input id="url-input-{id}" type="text" bind:value={wsUrl} placeholder="ws://host:port">
            <input type="text" bind:value={username} placeholder="username">
            <button class="connect-button" type="submit">Connect</button>
        {:else}
            <button type="button" class="header-button disconnect-button" on:click={disconnect}>Disconnect</button>
            <div class="header-info" title={roomTopic || motd}>
                {roomTopic || motd}
            </div>
            <button type="button" class="header-button" on:click={() => newIoskFileExplorer(id, title)}>Files</button>
        {/if}
    </form>

    <div class="main-flex-area">
        <div class="terminal-wrapper">
            <div class="terminal" bind:this={terminalEl} on:scroll={() => shouldScroll = (terminalEl.scrollTop + terminalEl.clientHeight >= terminalEl.scrollHeight - 10)}>
                {#each output as line}
                    <div class="terminal-line" class:prompt={line.type === 'prompt'}>
                        {line.content}
                    </div>
                {/each}
            </div>
            {#if isConnected}
                <div class="input-area" on:click={() => commandInput.focus()}>
                    <span>{currentPrompt}</span>
                    <input type="text" bind:this={commandInput} bind:value={command} on:keydown={handleKeydown} spellcheck="false" />
                </div>
            {/if}
        </div>

        {#if roomName}
        <div class="users-panel">
            <div class="panel-header">Users</div>
            <div class="user-list">
                {#each roomParticipants as participant (participant)}
                    <div class="user-item" title={participant}>{participant}</div>
                {/each}
            </div>
        </div>
        {/if}
    </div>

    {#if showSettings}
        <div class="modal-overlay" on:click|self={handleCancelSettings} on:keydown={handleSettingsKeydown}>
            <div class="modal-content">
                <h3>IOSK Default Connection Settings</h3>
                <div class="form-group">
                    <label for="url-setting-{id}">URL</label>
                    <input id="url-setting-{id}" type="text" bind:this={settingsUrlInput} bind:value={settingsUrl}>
                </div>
                <div class="form-group">
                    <label for="user-setting-{id}">Username</label>
                    <input id="user-setting-{id}" type="text" bind:value={settingsUsername}>
                </div>
                <div class="buttons">
                    <button on:click={handleCancelSettings}>Cancel</button>
                    <button class="save-button" on:click={handleSaveSettings}>Save</button>
                </div>
            </div>
        </div>
    {/if}
</div>