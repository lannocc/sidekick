<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate, tick } from 'svelte';
    import { get } from 'svelte/store';
    import { windows, newIoskFileExplorer, newIoskFileViewer, newIoskPrivateChat } from './windows.js';
    import { fileSystemRequests, fileSystemResponses, consoleCommands, privateMessages, fileSystemWatchEvents, fileSystemTailEvents } from './ioskEvents.js';
    import { desktopSettings, windowSettings } from './desktopStore.js';

    export let id; // Unique ID from the window manager
    export let groupId;
    export let title;
    export let isActive;
    export let componentName;
    export let x, y, width, height; // Current geometry from Window.svelte

    // These will be passed in when restoring a dash layout
    export let wsUrl = undefined;
    export let username = undefined;

    // Local values for the connection form inputs to avoid direct prop binding issues
    let localWsUrl, localUsername;

    let settings;
    desktopSettings.subscribe(value => settings = value);

    // --- State for Connection & Room Awareness ---
    let isConnected = false;
    let roomName = null;
    let roomTopic = '';
    let motd = '';
    let roomParticipants = [];
    let availableRooms = [];
    let showRoomsMenu = false;
    let userColors = {}; // New state for user color mapping

    // --- State for Attach Menu ---
    let showAttachMenu = false;
    let attachDevices = [];
    let attachUsers = [];
    let selectedDevice = null;
    let selectedUser = null;
    let isLoadingDevices = false;
    let isLoadingUsers = false;

    // --- State for User Context Menu ---
    let userContextMenu = {
        visible: false,
        x: 0,
        y: 0,
        user: null,
        showColorPicker: false
    };

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
    let roomsButton;
    let attachButton;

    // --- WebSocket instance for this specific console window ---
    let ws = null;
    const PREAMBLE = "SK1:";

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsUrl, settingsUsername;
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };

    // --- Event bus subscriptions ---
    let requestUnsubscribe;
    let commandsUnsubscribe;

    // --- Auto-scrolling logic ---
    let shouldScroll = true;

    // --- Color Handling ---
    const colorNameToCss = {
        'black': 'var(--ansi-black)', 'red': 'var(--ansi-red)', 'green': 'var(--ansi-green)', 'yellow': 'var(--ansi-yellow)',
        'blue': 'var(--ansi-blue)', 'magenta': 'var(--ansi-magenta)', 'cyan': 'var(--ansi-cyan)', 'white': 'var(--ansi-white)',
        'bright_black': 'var(--ansi-bright-black)', 'bright_red': 'var(--ansi-bright-red)', 'bright_green': 'var(--ansi-bright-green)',
        'bright_yellow': 'var(--ansi-bright-yellow)', 'bright_blue': 'var(--ansi-bright-blue)', 'bright_magenta': 'var(--ansi-bright-magenta)',
        'bright_cyan': 'var(--ansi-bright-cyan)', 'bright_white': 'var(--ansi-bright-white)',
    };

    const ansiCodeToCssVar = {
        '30': 'var(--ansi-black)', '31': 'var(--ansi-red)', '32': 'var(--ansi-green)', '33': 'var(--ansi-yellow)',
        '34': 'var(--ansi-blue)', '35': 'var(--ansi-magenta)', '36': 'var(--ansi-cyan)', '37': 'var(--ansi-white)',
        '90': 'var(--ansi-bright-black)', '91': 'var(--ansi-bright-red)', '92': 'var(--ansi-bright-green)', '93': 'var(--ansi-bright-yellow)',
        '94': 'var(--ansi-bright-blue)', '95': 'var(--ansi-bright-magenta)', '96': 'var(--ansi-bright-cyan)', '97': 'var(--ansi-bright-white)',
    };

    function parseAnsi(text) {
        if (typeof text !== 'string') return '';
        const ansiRegex = /\u001b\[(\d+)m/g;
        let openSpan = false;
        
        let sanitizedText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

        let html = sanitizedText.replace(ansiRegex, (match, code) => {
            let newHtml = '';
            if (openSpan) {
                newHtml += '</span>';
                openSpan = false;
            }
            if (code === '0') {
                // Reset code, just close the span
            } else if (ansiCodeToCssVar[code]) {
                newHtml += `<span style="color: ${ansiCodeToCssVar[code]}">`;
                openSpan = true;
            }
            return newHtml;
        });

        if (openSpan) {
            html += '</span>';
        }
        return html;
    }

    function stripAnsi(text) {
        if (typeof text !== 'string') return '';
        const ansiRegex = /\u001b\[\d+m/g;
        return text.replace(ansiRegex, '');
    }


    // --- Lifecycle and Reactive Statements ---
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

    function handleGlobalClick(event) {
        if (showRoomsMenu && roomsButton && !roomsButton.contains(event.target)) {
            showRoomsMenu = false;
            focusInput();
        }
        if (showAttachMenu && attachButton && !attachButton.contains(event.target) && !event.target.closest('.attach-menu')) {
            showAttachMenu = false;
            focusInput();
        }
        if (userContextMenu.visible && !event.target.closest('.user-context-menu')) {
            closeUserContextMenu();
            focusInput();
        }
    }

    onMount(() => {
        // Initialize local input values from passed-in props
        localWsUrl = wsUrl;
        localUsername = username;

        if (!isConnected) {
            const urlInput = document.querySelector(`#url-input-${id}`);
            urlInput?.focus();
        }
        requestUnsubscribe = fileSystemRequests.subscribe(request => {
            if (request && request.consoleId === id && ws && ws.readyState === WebSocket.OPEN) {
                const payload = { ...request.command };
                if (request.requesterId) {
                    payload.requesterId = request.requesterId;
                }
                ws.send(JSON.stringify(payload));
            }
        });
        commandsUnsubscribe = consoleCommands.subscribe(cmd => {
            if (cmd && cmd.consoleId === id) {
                sendSystemCommand(cmd.command);
            }
        });
        window.addEventListener('click', handleGlobalClick);
    });

    onDestroy(() => {
        if (ws) {
            ws.onclose = null; 
            ws.close();
        }
        if (requestUnsubscribe) {
            requestUnsubscribe();
        }
        if (commandsUnsubscribe) {
            commandsUnsubscribe();
        }
        window.removeEventListener('click', handleGlobalClick);
    });

    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, {
            isConsoleConnected: isConnected,
           consoleConnection: isConnected ? { url: wsUrl, user: username } : null,
           wsUrl,
           username
        });
    }

    $: if (groupId !== undefined && id !== undefined && title !== undefined) {
        let newTitle;
        if (isConnected) {
            const host = (() => { try { return new URL(wsUrl).hostname } catch { return 'invalid-host' }})();
            const userAtHost = `${username}@${host}`;
            newTitle = roomName ? `[${stripAnsi(roomName)}] ${userAtHost}` : userAtHost;
        } else {
            newTitle = title;
        }
        if (newTitle !== title) {
            windows.updateTabProps(groupId, id, { title: newTitle });
        }
    }

    // --- User Context Menu Functions ---
    function handleUserRightClick(event, participant) {
        event.preventDefault();
        event.stopPropagation();
        // Close other menus that might be open
        showRoomsMenu = false;
        showAttachMenu = false;

        userContextMenu = {
            visible: true,
            x: event.clientX,
            y: event.clientY,
            user: participant,
            showColorPicker: false
        };
    }

    function closeUserContextMenu() {
        userContextMenu = { visible: false, x: 0, y: 0, user: null, showColorPicker: false };
    }

    function sendSystemCommand(systemCommand) {
        if (!systemCommand.trim()) return;

        // This command is programmatically sent, but we display it as if typed for user feedback.
        // It is not added to command history.
        output = [...output, {type: 'prompt', content: currentPrompt + systemCommand}];

        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'client_input', data: systemCommand + '\n' };
            ws.send(JSON.stringify(message));
        } else {
            output = [...output, {type: 'output', content: `[Error] Not connected.`}];
        }
        shouldScroll = true;
    }
    
    function openPrivateChat(remoteParticipant) {
        if (!remoteParticipant) return;
        // Don't open chat with self.
        const remoteUsername = remoteParticipant.split('.')[0];
        if (remoteUsername === username) return;

        newIoskPrivateChat(id, username, remoteParticipant);
        closeUserContextMenu();
        focusInput();
    }

    function viewUserLog() {
        if (!userContextMenu.user) return;

        const usernameOnly = userContextMenu.user.split('.')[0];
        
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const dateString = `${year}-${month}-${day}`;

        const logPath = `/var/log/user/${usernameOnly}/${dateString}.log`;

        newIoskFileViewer(id, logPath);
        closeUserContextMenu();
        focusInput();
    }

    function setColorForUser(colorName) {
        if (!userContextMenu.user) return;
        const userNameOnly = userContextMenu.user.split('.')[0];
        const commandToRun = `$ color -u ${userNameOnly} ${colorName}`;
        sendSystemCommand(commandToRun);
        closeUserContextMenu();
        focusInput();
    }

    function handleDetachUser() {
        if (!userContextMenu.user) return;
        const commandToRun = `$ detach ${userContextMenu.user}`;
        sendSystemCommand(commandToRun);
        closeUserContextMenu();
        focusInput();
    }

    // --- Functions ---
    export function showSettingsDialog() {
        if (isConnected) return;
        settingsUrl = wsUrl;
        settingsUsername = username;

        const allSettings = get(windowSettings);
        const currentSettings = allSettings[componentName] || { positioning: 'auto' };
        windowSettingsForModal = {
            positioning: currentSettings.positioning || 'auto',
            x: currentSettings.x ?? x,
            y: currentSettings.y ?? y,
            width: currentSettings.width ?? width,
            height: currentSettings.height ?? height,
            defaultZoom: currentSettings.defaultZoom ?? 1.0,
        };
        
        showSettings = true;
        tick().then(() => settingsUrlInput?.focus());
    }

    function handleSaveSettings() {
        wsUrl = settingsUrl;
        username = settingsUsername;
        // Also update the local values for the connection form to keep them in sync
        localWsUrl = settingsUrl;
        localUsername = settingsUsername;

        windowSettings.update(allSettings => {
            const existingSettings = allSettings[componentName] || {};
            return {
                ...allSettings,
                [componentName]: {
                    ...existingSettings,
                    ...windowSettingsForModal,
                    defaultUrl: settingsUrl,
                    defaultUsername: settingsUsername
                }
            };
        });

        showSettings = false;
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

    function requestFsList(path) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'fs_list', path };
            ws.send(JSON.stringify(message));
        }
    }

    function requestAllDevices() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'fs_list', path: '/dev', recursive: true };
            ws.send(JSON.stringify(message));
        }
    }

    export async function connect() {
        // Sync local input values back to the main props before connecting
        wsUrl = localWsUrl;
        username = localUsername;

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

                        if (data.type === 'private_message') {
                            // This is a new dedicated DM message.
                            // The backend sends this *in addition* to the regular output
                            // for console history, so we just process this for the chat window
                            // and play the bell, but don't add to the console `output` array here.
                            privateMessages.set({
                                from: stripAnsi(data.from),
                                to: data.to,
                                content: data.content,
                                timestamp: Date.now()
                            });

                            // A user can receive a DM confirmation they sent. Don't open a window for that.
                            const remoteUsername = stripAnsi(data.from).split('.')[0];
                            if (remoteUsername !== username) {
                                newIoskPrivateChat(id, username, stripAnsi(data.from));
                            }

                            // Trigger a bell sound/flash.
                            handleBell();
                        } else if (data.type === 'state_info' || data.type === 'room_state_update') {
                            roomName = data.roomName || null;
                            roomTopic = data.roomTopic || '';
                            roomParticipants = data.participants || [];
                            availableRooms = data.availableRooms || [];
                            if (data.userColors) {
                                userColors = data.userColors;
                            }
                            if (data.type === 'state_info') {
                                motd = data.motd || '';
                            }
                        } else if (data.type === 'user_colors_update') {
                            userColors = data.colors;
                        } else if (data.type === 'fs_watch_update') {
                            fileSystemWatchEvents.set({
                                consoleId: id,
                                data: data,
                                timestamp: Date.now()
                            });
                        } else if (data.type === 'fs_tail_update') {
                            fileSystemTailEvents.set({
                                consoleId: id,
                                data: data,
                                timestamp: Date.now()
                            });
                        } else if (data.output || data.prompt) {
                            if (data.output) {
                                const bellCode = "\u0007";
                                let outputToProcess = data.output;
                                let hasRegularBell = false;

                                if (outputToProcess.includes(bellCode)) {
                                    const dmRegex = new RegExp(`^${bellCode}\\s*\\n\\[\\s*(.*?)\\s*->\\s*me.*?\\]\\s*<<\\s*([\\s\\S]*)`, 'm');
                                    let match;
                                    // Loop in case there are multiple DMs in one output block
                                    while ((match = dmRegex.exec(outputToProcess)) !== null) {
                                        const fromUser = match[1].trim();
                                        const content = match[2].trim();
                                        
                                        // A user can receive a DM confirmation from the server they sent, don't open a window for that.
                                        const remoteUsername = stripAnsi(fromUser).split('.')[0];
                                        if (remoteUsername !== username) {
                                            newIoskPrivateChat(id, username, stripAnsi(fromUser));
                                            privateMessages.set({
                                                from: stripAnsi(fromUser),
                                                to: username,
                                                content: content,
                                                timestamp: Date.now()
                                            });
                                        }
                                        // Remove the bell from the matched DM so it doesn't trigger a sound, but leave the message for console history.
                                        outputToProcess = outputToProcess.replace(match[0], match[0].substring(1));
                                    }
                                }

                                // Now check if any other, non-DM bells remain.
                                if (outputToProcess.includes(bellCode)) {
                                    handleBell();
                                    outputToProcess = outputToProcess.replace(new RegExp(bellCode, 'g'), '');
                                }

                                let cleanOutput = outputToProcess;

                                const clearScreenCode = "\x1b[H\x1b[2J";
                                if (cleanOutput === clearScreenCode) {
                                    output = [];
                                } else if (cleanOutput) {
                                    const lines = cleanOutput.split('\n');
                                    output = [...output, ...lines.map(line => ({type: 'output', content: line}))];
                                }
                            }
                            if (data.prompt) {
                                currentPrompt = data.prompt;
                            }
                        } else if (data.type === 'fs_list_response') {
                            if (data.requesterId) {
                                // It's for an external component like File Explorer
                                fileSystemResponses.set({
                                    consoleId: id,
                                    requesterId: data.requesterId,
                                    data: data,
                                    timestamp: Date.now()
                                });
                            } else {
                                // It's for this console's internal UI (attach menu)
                                if (data.path === '/dev') {
                                    // This is the recursive device listing
                                    let items = data.listing || [];
                                    attachDevices = items
                                        .filter(item => {
                                            const basename = item.path.split('/').pop();
                                            if (basename && basename.startsWith('.')) {
                                                return false; // Always ignore dotfiles/dotdirs
                                            }
                                            // Ignore if any path segment starts with '_'
                                            return !item.path.split('/').some(segment => segment.startsWith('_'));
                                        })
                                        .map(item => {
                                            let displayPath = item.path.startsWith('/dev/') ? item.path.substring(5) : item.path;

                                            if (item.type === 'file' && displayPath.endsWith('.py')) {
                                                displayPath = displayPath.slice(0, -3);
                                            }
                                            if (displayPath.endsWith('/')) {
                                                displayPath = displayPath.slice(0, -1);
                                            }

                                            return {
                                                displayName: displayPath || '/', // Handle root case
                                                fullPath: item.path,
                                                type: item.type
                                            };
                                        })
                                        .sort((a, b) => a.displayName.localeCompare(b.displayName));
                                    isLoadingDevices = false;
                                } else if (data.path === '/home') {
                                    // This is the user listing
                                    attachUsers = (data.listing || []).filter(item => item.type === 'dir');
                                    isLoadingUsers = false;
                                }
                            }
                        } else if (data.type === 'fs_read_response') {
                            fileSystemResponses.set({
                                consoleId: id,
                                requesterId: data.requesterId,
                                data: data,
                                timestamp: Date.now()
                            });
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
                roomName = null; roomTopic = ''; motd = ''; roomParticipants = []; availableRooms = []; userColors = {};
                output = [...output, {type: 'output', content: `Connection closed.`}];
                const host = (() => { try { return new URL(wsUrl).hostname } catch { return 'invalid-host' }})();
                windows.updateTabProps(groupId, id, { title: `Disconnected - ${username}@${host}` });
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
                windows.updateTabProps(groupId, id, { title: `[Error] ${username}@${host}` });
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

    function joinRoom(roomToJoin) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'room_action', action: 'join', roomName: roomToJoin };
            ws.send(JSON.stringify(message));
        }
        showRoomsMenu = false;
        focusInput();
    }

    function closeRoom() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'room_action', action: 'close' };
            ws.send(JSON.stringify(message));
        }
        showRoomsMenu = false;
        focusInput();
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

    export function toggleRoomsMenu() {
        showRoomsMenu = !showRoomsMenu;
    }

    export function toggleAttachMenu() {
        showAttachMenu = !showAttachMenu;
        if (showAttachMenu) {
            selectedDevice = null;
            selectedUser = null;
            if (attachDevices.length === 0) {
                isLoadingDevices = true;
                requestAllDevices();
            }
            if (attachUsers.length === 0) {
                isLoadingUsers = true;
                requestFsList('/home');
            }
        }
    }

    function handleDeviceClick(item) {
        selectedDevice = item.displayName;
    }

    function handleUserClick(item) {
        selectedUser = item.name;
    }

    function performAttach() {
        if (!selectedDevice) return;
        const commandToRun = selectedUser
            ? `$ attach ${selectedDevice} ${selectedUser}`
            : `$ attach ${selectedDevice}`;
        output = [...output, {type: 'prompt', content: currentPrompt + commandToRun}];
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'client_input', data: commandToRun + '\n' }));
        }
        showAttachMenu = false;
        focusInput();
    }

    function handleBell() {
        // 1. Play sound
        if (settings?.chimeType && settings.chimeType !== 'none') {
            let src;
            if (settings.chimeType === 'custom') {
                src = settings.chimeUrl;
            } else {
                src = `/assets/${settings.chimeType}`;
            }

            if (src) {
                try {
                    new Audio(src).play().catch(e => console.warn("Audio bell failed to play:", e));
                } catch (e) { console.error("Failed to create audio element for bell:", e); }
            }
        }

        // 2. Flash window
        windows.updateWindowProps(id, { isFlashing: true });
        setTimeout(() => windows.updateWindowProps(id, { isFlashing: false }), 500);
    }
</script>

<style>
    :global(:root) { /* Define ANSI colors so they can be themed */
        --ansi-black: #2c3e50;
        --ansi-red: #c0392b;
        --ansi-green: #27ae60;
        --ansi-yellow: #f1c40f;
        --ansi-blue: #2980b9;
        --ansi-magenta: #8e44ad;
        --ansi-cyan: #16a085;
        --ansi-white: #bdc3c7;
        --ansi-bright-black: #95a5a6;
        --ansi-bright-red: #e74c3c;
        --ansi-bright-green: #2ecc71;
        --ansi-bright-yellow: #f39c12;
        --ansi-bright-blue: #3498db;
        --ansi-bright-magenta: #9b59b6;
        --ansi-bright-cyan: #1abc9c;
        --ansi-bright-white: #ecf0f1;
    }
    .console-container { display: flex; flex-direction: column; height: 100%; background-color: var(--console-bg); color: var(--console-text); font-family: 'Courier New', Courier, monospace; font-size: 14px; position: relative; }
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
    .connect-form .files-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .connect-form .files-button:hover { background-color: #1a9c2a; }
    .connect-form .attach-button { background-color: #3498db; border-color: #2980b9; color: white; position: relative; padding-right: 15px; }
    .connect-form .attach-button:hover { background-color: #2980b9; }
    .connect-form .room-button::before, .connect-form .attach-button::after { content: ''; position: absolute; top: 50%; transform: translateY(-50%); width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 4px solid rgba(255, 255, 255, 0.7); }
    .connect-form .room-button::before { left: 5px; }
    .connect-form .attach-button::after { right: 5px; }
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
    .user-item { padding: 2px 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; border-radius: 2px; }
    .user-item:hover { background-color: var(--taskbar-button-hover-bg); }
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
    .rooms-menu { position: absolute; top: 45px; left: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 100; display: flex; flex-direction: column; min-width: 180px; max-height: 250px; overflow-y: auto; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; border-bottom: 1px solid var(--border-color); }
    .menu-item:last-child { border-bottom: none; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; font-style: italic; }
    .menu-item-empty { padding: 8px 12px; color: #7f8c8d; font-style: italic; }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 0; }
    .close-item { color: #e74c3c; }
    .close-item:hover { background-color: #c0392b; color: white; }
    .attach-menu { position: absolute; top: 45px; right: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 100; display: flex; width: 600px; height: 300px; flex-direction: column; }
    .attach-panels { display: flex; flex-grow: 1; overflow: hidden; }
    .attach-panel { width: 35%; display: flex; flex-direction: column; border-right: 1px solid var(--border-color); }
    .attach-panel:first-child { width: 65%; }
    .attach-panel:last-child { border-right: none; }
    .panel-list { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .list-item { padding: 4px 8px; cursor: pointer; border-radius: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .list-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .list-item.selected { background-color: #3498db; color: white; }
    .attach-footer { padding: 8px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; flex-shrink: 0; }
    .attach-footer button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 4px 8px; cursor: pointer; border-radius: 3px; }
    .attach-footer button:disabled { opacity: 0.5; cursor: not-allowed; }
    .attach-footer button.primary { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .path-header { font-size: 0.9em; color: #95a5a6; padding: 2px 8px; flex-shrink: 0; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; margin-top: 15px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding-left: 20px; }
    .form-grid label { display: flex; align-items: center; gap: 5px; }
    .form-grid input { width: 80px; }
    .radio-group label { display: inline-flex; align-items: center; gap: 5px; margin-right: 15px; }

    /* User Context Menu Styles */
    .user-context-menu {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 200; /* Above console content */
        display: flex;
        flex-direction: column;
        padding: 4px;
        min-width: 120px;
    }
    .color-picker-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 4px;
        padding: 4px;
    }
    .color-swatch {
        width: 24px;
        height: 24px;
        border: 1px solid var(--border-color);
        border-radius: 3px;
        cursor: pointer;
        background: none; /* remove default button background */
    }
    .color-swatch:hover {
        border-color: var(--taskbar-button-hover-bg);
        transform: scale(1.1);
    }
</style>

<div class="console-container">
    <form class="connect-form" on:submit|preventDefault={connect}>
        {#if !isConnected}
            <input id="url-input-{id}" type="text" bind:value={localWsUrl} placeholder="ws://host:port">
            <input type="text" bind:value={localUsername} placeholder="username">

            <button class="connect-button" type="submit">Connect</button>
        {:else}
            <button type="button" class="header-button disconnect-button" on:click={disconnect}>Disconnect</button>
            <button type="button" class="header-button room-button" bind:this={roomsButton} on:click|stopPropagation={toggleRoomsMenu} title="Available Rooms">Rooms</button>
            <div class="header-info" title={stripAnsi(roomTopic || motd)}>
                {@html parseAnsi(roomTopic || motd)}
            </div>
            <button type="button" class="header-button files-button" on:click={() => { newIoskFileExplorer(id, title); focusInput(); }}>Files</button>
            <button type="button" class="header-button attach-button" bind:this={attachButton} on:click|stopPropagation={toggleAttachMenu} title="Attach Device/User">Attach</button>
        {/if}
    </form>

    {#if showRoomsMenu}
        <div class="rooms-menu">
            {#each availableRooms as room (room.name)}
                <button class="menu-item" on:click={() => joinRoom(room.name)} disabled={room.name === roomName} title={room.topic || 'No topic'}>
                    {room.name}
                </button>
            {:else}
                <span class="menu-item-empty">No rooms available</span>
            {/each}
            {#if roomName}
                <div class="menu-separator"></div>
                <button class="menu-item close-item" on:click={closeRoom}>
                    Close '{roomName}'
                </button>
            {/if}
        </div>
    {/if}

    {#if showAttachMenu}
        <div class="attach-menu">
            <div class="attach-panels">
                <div class="attach-panel">
                    <div class="panel-header">Device</div>
                    <div class="panel-list">
                        {#if isLoadingDevices}
                            <div class="list-item">Loading...</div>
                        {:else}
                            {#each attachDevices as item (item.fullPath)}
                                <div
                                    class="list-item"
                                    class:selected={selectedDevice === item.displayName}
                                    on:click={() => handleDeviceClick(item)}
                                    title={item.displayName}
                                >
                                    {item.type === 'dir' ? '🗂️' : '🔌'} {item.displayName}
                                </div>
                            {:else}
                                <div class="list-item">(empty)</div>
                            {/each}
                        {/if}
                    </div>
                </div>
                <div class="attach-panel">
                    <div class="panel-header">User (Optional)</div>
                    <div class="path-header">/home</div>
                     <div class="panel-list">
                        {#if isLoadingUsers}
                            <div class="list-item">Loading...</div>
                        {:else}
                            {#each attachUsers as item (item.name)}
                                <div
                                    class="list-item"
                                    class:selected={selectedUser === item.name}
                                    on:click={() => handleUserClick(item)}
                                    title={item.name}
                                >
                                    👤 {item.name}
                                </div>
                            {:else}
                                <div class="list-item">(no users found)</div>
                            {/each}
                        {/if}
                    </div>
                </div>
            </div>
            <div class="attach-footer">
                <button
                    class="primary"
                    disabled={!selectedDevice}
                    on:click={performAttach}>
                    Attach
                </button>
            </div>
        </div>
    {/if}

    <div class="main-flex-area">
        <div class="terminal-wrapper">
            <div class="terminal" bind:this={terminalEl} on:scroll={() => shouldScroll = (terminalEl.scrollTop + terminalEl.clientHeight >= terminalEl.scrollHeight - 10)} on:click={handleClickOnTerminal}>
                {#each output as line}
                    <div class="terminal-line" class:prompt={line.type === 'prompt'}>
                        {@html parseAnsi(line.content)}
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
                    {@const userName = participant.includes('.') ? participant.split('.')[0] : participant}
                    <div
                        class="user-item"
                        title={participant}
                        style="color: {colorNameToCss[userColors[userName]] || 'inherit'}"
                        on:contextmenu={(e) => handleUserRightClick(e, participant)}
                        on:click={() => openPrivateChat(participant)}
                    >
                        {participant}
                    </div>
                {/each}
            </div>
        </div>
        {/if}
    </div>

    {#if showSettings}
        <div class="modal-overlay" on:click|self={handleCancelSettings} on:keydown={handleSettingsKeydown}>
            <div class="modal-content">
                <h3>Settings</h3>
                <div class="form-group">
                    <label for="url-setting-{id}">Default URL</label>
                    <input id="url-setting-{id}" type="text" bind:this={settingsUrlInput} bind:value={settingsUrl}>
                </div>
                <div class="form-group">
                    <label for="user-setting-{id}">Default Username</label>
                    <input id="user-setting-{id}" type="text" bind:value={settingsUsername}>
                </div>

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
                    <div class="form-grid" style="grid-template-columns: 1fr; padding-left: 0;">
                        <label style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Default Zoom</span>
                            <input type="number" bind:value={windowSettingsForModal.defaultZoom} min="0.5" max="3" step="0.1" style="width: 80px;">
                        </label>
                    </div>
                </fieldset>

                <div class="buttons">
                    <button on:click={handleCancelSettings}>Cancel</button>
                    <button class="save-button" on:click={handleSaveSettings}>Save Defaults</button>
                </div>
            </div>
        </div>
    {/if}

    {#if userContextMenu.visible}
        <div
            class="user-context-menu"
            style="top: {userContextMenu.y}px; left: {userContextMenu.x}px;"
            on:click|stopPropagation
        >
            {#if userContextMenu.showColorPicker}
                <div class="color-picker-grid">
                    {#each Object.entries(colorNameToCss) as [name, cssVar] (name)}
                        <button
                            class="color-swatch"
                            style="background-color: {cssVar}"
                            title={name.replace(/_/g, ' ')}
                            on:click={() => setColorForUser(name)}
                        ></button>
                    {/each}
                </div>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => userContextMenu.showColorPicker = false}>
                    &larr; Back
                </button>
            {:else}
                <button class="menu-item" on:click={() => openPrivateChat(userContextMenu.user)}>
                    Private Chat
                </button>
                <button class="menu-item" on:click={viewUserLog}>
                    View Log...
                </button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => userContextMenu.showColorPicker = true}> Set Color... </button>
                <div class="menu-separator"></div>
                <button class="menu-item close-item" on:click={handleDetachUser}>
                    Detach
                </button>
            {/if}
        </div>
    {/if}
</div>