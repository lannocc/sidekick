<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate } from 'svelte';
    import { windows, newIoskFileExplorer } from './windows.js';
    import { fileSystemRequests, fileSystemResponses } from './ioskEvents.js';

    export let id; // Unique ID from the window manager
    export let title;

    export let wsUrl = 'ws://localhost:4209';
    export let username = 'root';
    let isConnected = false;
    let output = []; // Array of { type: 'prompt'|'output', content: 'text' }
    let command = '';
    let commandHistory = [];
    let historyIndex = 0;
    let unsentCommand = '';
    let currentPrompt = '';

    let terminalEl;
    let commandInput;

    // WebSocket instance for this specific console window
    let ws = null;
    const PREAMBLE = "SK1:";

    // Event bus subscriptions
    let requestUnsubscribe;

    // Auto-scrolling logic
    let shouldScroll = true;
    afterUpdate(() => {
        if (shouldScroll && terminalEl) {
            terminalEl.scrollTop = terminalEl.scrollHeight;
        }
    });

    async function connect() {
        if (ws) {
            output = [...output, {type: 'output', content: `Already connected or connecting.`}];
            return;
        }

        output = [...output, {type: 'output', content: `Connecting to ${wsUrl} as ${username}...`}];

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log(`WebSocket connected for console ${id}.`);
                isConnected = true;
                let newTitle;
                try {
                    newTitle = `${username}@${new URL(wsUrl).hostname}`;
                } catch (e) {
                    newTitle = `${username}@invalid-host`;
                }
                windows.updateWindowProps(id, { title: newTitle });

                // Send handshake message to backend `port.py`
                const handshake = { type: 'handshake', id: 'client', user: username };
                ws.send(JSON.stringify(handshake));

                // Focus command input
                setTimeout(() => commandInput?.focus(), 100);
            };

            ws.onmessage = (event) => {
                // The backend `port.py` sends JSON messages with a preamble.
                if (typeof event.data === 'string' && event.data.startsWith(PREAMBLE)) {
                    try {
                        const jsonData = event.data.substring(PREAMBLE.length);
                        const data = JSON.parse(jsonData);

                        // We expect a format like `{"output": "text from iosk..."}`
                        if (data.output || data.prompt) {
                             if (data.output) {
                                // Split by newline to handle multi-line responses cleanly
                                const lines = data.output.split('\n');
                                output = [...output, ...lines.map(line => ({type: 'output', content: line}))];
                            }
                            if (data.prompt) {
                                currentPrompt = data.prompt;
                            }
                        } else if (data.type === 'fs_list_response') {
                            // Publish to the event bus for the file explorer
                            fileSystemResponses.set({ consoleId: id, data: data, timestamp: Date.now() });
                        }
                    } catch (e) {
                        console.error("Error parsing WebSocket message:", e);
                        output = [...output, {type: 'output', content: `[Error] Could not parse message from server.`}];
                    }
                }
            };

            ws.onclose = () => {
                console.log(`WebSocket disconnected for console ${id}.`);
                isConnected = false;
                ws = null; // Allow reconnection
                output = [...output, {type: 'output', content: `Connection closed.`}];
                let newTitle;
                try {
                    newTitle = `[Disconnected] ${username}@${new URL(wsUrl).hostname}`;
                } catch (e) {
                    newTitle = `[Disconnected] ${username}@invalid-host`;
                }
                windows.updateWindowProps(id, { title: newTitle });
            };

            ws.onerror = (error) => {
                console.error(`WebSocket error for console ${id}:`, error);
                isConnected = false;
                if (ws) { // ws might already be null if onclose was called
                    ws.close();
                    ws = null;
                }
                output = [...output, {type: 'output', content: `[Error] Could not establish connection to ${wsUrl}.`}];
                let newTitle;
                try {
                    newTitle = `[Error] ${username}@${new URL(wsUrl).hostname}`;
                } catch (e) {
                    newTitle = `[Error] ${username}@invalid-host`;
                }
                windows.updateWindowProps(id, { title: newTitle });
            };

        } catch (e) {
            console.error("Failed to create WebSocket:", e);
            output = [...output, {type: 'output', content: `[Error] Failed to create WebSocket: ${e.message}`}];
        }
    }

    function sendCommand() {
        if (!command.trim()) return;

        const fullCommand = command;
        const promptText = currentPrompt;
        output = [...output, {type: 'prompt', content: promptText + fullCommand}];

        // Add to history if it's not a consecutive duplicate
        if (commandHistory.length === 0 || commandHistory[commandHistory.length - 1] !== fullCommand) {
            commandHistory = [...commandHistory, fullCommand];
        }
        historyIndex = commandHistory.length;
        unsentCommand = '';

        // Send command to backend via this console's WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            const message = { type: 'client_input', data: fullCommand + '\n' };
            ws.send(JSON.stringify(message));
        } else {
            output = [...output, {type: 'output', content: `[Error] Not connected.`}];
        }

        command = '';
        shouldScroll = true;
    }

    function disconnect() {
        if (ws) {
            ws.close();
        }
    }

    function handleKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendCommand();
            return;
        }

        if (commandHistory.length === 0) {
            return;
        }

        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex === commandHistory.length) {
                // Starting navigation from a new command line
                unsentCommand = command;
            }
            if (historyIndex > 0) {
                historyIndex--;
                command = commandHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                command = commandHistory[historyIndex];
            } else if (historyIndex === commandHistory.length - 1) {
                historyIndex++;
                command = unsentCommand; // Restore the command being typed
            }
        }
    }

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
        // Clean up the websocket connection when the component is destroyed
        if (ws) {
            ws.onclose = null; // prevent onclose handler from running on manual close
            ws.close();
        }
        // Clean up the event bus subscription
        if (requestUnsubscribe) {
            requestUnsubscribe();
        }
    });
</script>

<style>
    .console-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
    }
    .connect-form {
        display: flex;
        gap: 8px;
        padding: 8px;
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
    }
    .connect-form input {
        flex-grow: 1;
        background-color: var(--window-bg);
        color: var(--title-bar-text);
        border: 1px solid var(--border-color);
        padding: 4px;
    }
    .connect-form .connect-button {
        background-color: #27c93f;
        border: 1px solid #1a9c2a;
        color: white;
        padding: 4px 8px;
        cursor: pointer;
        border-radius: 3px;
    }
    .connect-form .header-button {
        background-color: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 4px 8px;
        cursor: pointer;
        border-radius: 3px;
    }
    .connect-form .header-button:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .connect-form .header-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .connect-form .disconnect-button {
        background-color: #e74c3c;
        border-color: #c0392b;
        color: white;
    }
    .connect-form .disconnect-button:hover {
        background-color: #c0392b;
    }
    .terminal {
        flex-grow: 1;
        overflow-y: auto;
        padding: 8px;
        white-space: pre-wrap;
        word-break: break-all;
    }
    .terminal-line.prompt {
        color: var(--console-prompt);
    }
    .input-area {
        display: flex;
        padding: 4px 8px;
        background-color: var(--title-bar-bg);
        border-top: 1px solid var(--border-color);
    }
    .input-area span {
        color: var(--console-prompt);
        padding-right: 5px;
        white-space: pre;
    }
    .input-area input {
        flex-grow: 1;
        background: transparent;
        border: none;
        outline: none;
        color: var(--console-input);
        font-family: inherit;
        font-size: inherit;
    }
</style>

<div class="console-container">
    <div class="connect-form">
        {#if !isConnected}
            <input id="url-input-{id}" type="text" bind:value={wsUrl} placeholder="ws://host:port">
            <input type="text" bind:value={username} placeholder="username">
            <button class="connect-button" on:click={connect}>Connect</button>
        {:else}
            <button class="header-button" on:click={() => newIoskFileExplorer(id, title)}>Files</button>
            <button class="header-button disconnect-button" style="margin-left: auto;" on:click={disconnect}>Disconnect</button>
        {/if}
    </div>

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
            <input
                type="text"
                bind:this={commandInput}
                bind:value={command}
                on:keydown={handleKeydown}
                spellcheck="false"
            />
        </div>
    {/if}
</div>

