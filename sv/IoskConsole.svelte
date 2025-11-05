<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate } from 'svelte';

    export let id; // Unique ID from the window manager
    export let title;

    let wsUrl = 'ws://localhost:4209';
    let username = 'root';
    let isConnected = false;
    let output = []; // Array of { type: 'prompt'|'output', content: 'text' }
    let command = '';

    let terminalEl;
    let commandInput;

    // Auto-scrolling logic
    let shouldScroll = true;
    afterUpdate(() => {
        if (shouldScroll && terminalEl) {
            terminalEl.scrollTop = terminalEl.scrollHeight;
        }
    });

    // The websocket communication layer expects `sws_send` to send a JSON object.
    // Our backend's `port.py` expects specific message types.
    // This is a direct call to the underlying WebSocket send function in sidekick.js
    // as `sk_call` is a higher-level abstraction we don't need here.
    function sendRaw(messageObject) {
        if(window.sws && window.sws.readyState === WebSocket.OPEN) {
            // The preamble is added by the global sws_send function.
            // We just need to stringify our JSON payload.
            const msg = window.PREAMBLE + JSON.stringify(messageObject);
            window.sws.send(msg);
        }
    }

    function onMessage(data) {
        // The backend `port.py` sends raw text via `send_to_client`.
        // The `sidekick.js` message handler JSON.parses the event.data.
        // We will assume the backend wraps its output in a simple JSON object.
        // Let's design for: `{"output": "text from iosk..."}`
        if (data.output) {
            // Split by newline to handle multi-line responses cleanly
            const lines = data.output.split('\n');
            output = [...output, ...lines.map(line => ({type: 'output', content: line}))];
        }
    }

    async function connect() {
        if (!window.sws) {
            alert("SideKick websocket not initialized. Check sidekick.js");
            return;
        }

        // Use the window id as the unique slot for the message handler
        window.sk_on_message(onMessage, id);

        // Send handshake message
        const handshake = { type: 'handshake', id: 'client', user: username };
        sendRaw(handshake);

        isConnected = true;
        title = `${username}@${new URL(wsUrl).hostname}`;
        output = [...output, {type: 'output', content: `Connecting to ${wsUrl} as ${username}...`}];

        // Wait for connection to be ready before focusing input
        setTimeout(() => commandInput?.focus(), 100);
    }

    function sendCommand() {
        if (!command.trim()) return;

        const fullCommand = command;
        const promptText = `[${username}] $ `;
        output = [...output, {type: 'prompt', content: promptText + fullCommand}];

        // Send command to backend
        const message = { type: 'client_input', data: fullCommand + '\n' };
        sendRaw(message);

        command = '';
        shouldScroll = true;
    }

    onMount(() => {
        // Automatically focus the connection URL input on mount
        const urlInput = document.querySelector(`#url-input-${id}`);
        urlInput?.focus();
    });

    onDestroy(() => {
        // Clean up the message handler when the component is destroyed
        window.sk_on_message(null, id);
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
    .connect-form button {
        background-color: #27c93f;
        border: 1px solid #1a9c2a;
        color: white;
        padding: 4px 8px;
        cursor: pointer;
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
    {#if !isConnected}
        <div class="connect-form">
            <input id="url-input-{id}" type="text" bind:value={wsUrl} placeholder="ws://host:port">
            <input type="text" bind:value={username} placeholder="username">
            <button on:click={connect}>Connect</button>
        </div>
    {/if}

    <div class="terminal" bind:this={terminalEl} on:scroll={() => shouldScroll = (terminalEl.scrollTop + terminalEl.clientHeight >= terminalEl.scrollHeight - 10)}>
        {#each output as line}
            <div class="terminal-line" class:prompt={line.type === 'prompt'}>
                {line.content}
            </div>
        {/each}
    </div>

    {#if isConnected}
        <div class="input-area" on:click={() => commandInput.focus()}>
            <span>[{username}] $</span>
            <input
                type="text"
                bind:this={commandInput}
                bind:value={command}
                on:keydown={e => e.key === 'Enter' && sendCommand()}
                spellcheck="false"
            />
        </div>
    {/if}
</div>

