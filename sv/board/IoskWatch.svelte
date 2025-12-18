<!-- sv/board/IoskWatch.svelte -->
<script>
    import { onMount, onDestroy, tick } from 'svelte';
    import { get } from 'svelte/store';
    // Refactored to use the new central connection hub functions
    import { sendRequest, fileSystemResponses } from '../iosk.js';
    import { windows } from '../windows.js';
    import { parseAnsi } from '../ansi.js';

    export let id; // tab id
    export let groupId;
    // The consoleId and consoleConnection props are replaced by a single connectionId.
    export let connectionId;

    // Props for dash restore
    export let initialCommand = '';
    export let initialPwd = '/';
    export let initialInterval = 1;
    export let initialState = 'setup'; // 'setup', 'watching', 'stopped'

    let command = initialCommand;
    let pwd = initialPwd;
    let interval = initialInterval;
    let watchState = initialState; // 'setup', 'watching', 'stopped'
    let output = '';
    
    let commandInputEl;
    let watchTimer = null;
    const requesterId = `watch-${id}`; // Unique requester for this window

    let unsubscribeResponses;

    // --- (REMOVED) Old dash restore logic ---
    // The component now relies on being created with a valid connectionId.

    // --- Update window store for Dash saving ---
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { 
            connectionId, // Persist the connectionId
            initialCommand: command,
            initialPwd: pwd,
            initialInterval: interval,
            initialState: watchState,
            title: watchState === 'setup' ? 'Watch' : `Watching: ${command}`
        });
    }

    onMount(() => {
        unsubscribeResponses = fileSystemResponses.subscribe(response => {
            if (response && response.requesterId === requesterId) {
                const data = response.data;
                if (data.error) {
                    output = data.error;
                    stopWatching();
                } else {
                    const newOutput = data.output;
                    // SENTINEL NOTIFICATION: Trigger if output has changed on an inactive window
                    if (newOutput !== output) {
                        if (!get(windows).find(w => w.id === groupId)?.isActive) {
                            windows.notifyActivity(groupId, id, { summary: `Watch output for '${command}' changed` });
                        }
                    }
                    output = newOutput;
                }
            }
        });

        // If restored from Dash and was watching, start immediately.
        if (connectionId && watchState === 'watching') {
            startWatching();
        }

        tick().then(() => commandInputEl?.focus());
    });

    onDestroy(() => {
        if (unsubscribeResponses) unsubscribeResponses();
        if (watchTimer) clearInterval(watchTimer);
    });

    function sendWatchRequest() {
        if (!connectionId) {
            output = '[Error] No active IOSK connection.';
            stopWatching();
            return;
        }
        // Construct the request object to be sent to the server.
        const request = {
            type: 'exec_command',
            command_str: command,
            pwd: pwd,
            requesterId: requesterId // Include requesterId for the server to echo back.
        };
        // Use the new centralized sendRequest function.
        sendRequest(connectionId, request);
    }

    function startWatching() {
        if (watchState === 'watching' || !command.trim()) return;
        output = 'Executing...';
        watchState = 'watching';
        sendWatchRequest(); // Initial immediate request
        if (watchTimer) clearInterval(watchTimer);
        watchTimer = setInterval(sendWatchRequest, interval * 1000);
    }

    function stopWatching() {
        if (watchTimer) {
            clearInterval(watchTimer);
            watchTimer = null;
        }
        watchState = 'stopped';
    }

</script>

<style>
    .watch-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        padding: 10px;
        gap: 10px;
        box-sizing: border-box;
    }
    .setup-form { display: flex; flex-direction: column; gap: 8px; }
    .form-group { display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 0.9em; }
    input {
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 5px;
        border-radius: 3px;
        font-family: inherit;
    }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 5px; }
    button {
        padding: 6px 12px;
        border-radius: 3px;
        cursor: pointer;
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        background-color: var(--taskbar-button-bg);
    }
    button:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .start-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .stop-button { background-color: #e74c3c; border-color: #c0392b; color: white; }

    .watch-view { display: flex; flex-direction: column; flex-grow: 1; min-height: 0; gap: 10px; }
    h3 { margin: 0; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .output-area {
        flex-grow: 1;
        overflow: auto;
        padding: 8px;
        white-space: pre;
        font-family: monospace;
        background-color: var(--console-bg); /* Changed for a darker, terminal-like look */
        border: 1px solid var(--border-color);
        border-radius: 3px;
    }
</style>

<div class="watch-container">
    {#if watchState === 'setup'}
        <div class="setup-form">
            <h3>Watch Command</h3>
            <div class="form-group">
                <label for="watch-cmd-{id}">Command</label>
                <input id="watch-cmd-{id}" type="text" bind:this={commandInputEl} bind:value={command} required placeholder="e.g., ls -l /var/log">
            </div>
            <div class="form-group">
                <label for="watch-pwd-{id}">Working Directory</label>
                <input id="watch-pwd-{id}" type="text" bind:value={pwd}>
            </div>
            <div class="form-group">
                <label for="watch-interval-{id}">Interval (seconds)</label>
                <input id="watch-interval-{id}" type="number" bind:value={interval} min="1">
            </div>
            <div class="buttons">
                <button class="start-button" on:click={startWatching} disabled={!command.trim() || !connectionId}>Start Watching</button>
            </div>
        </div>
    {:else}
        <div class="watch-view">
            <h3>Watching: <code>{command}</code></h3>
            <div class="output-area">{@html parseAnsi(output)}</div>
            <div class="buttons">
                {#if watchState === 'watching'}
                    <button class="stop-button" on:click={stopWatching}>Stop</button>
                {:else if watchState === 'stopped'}
                    <button class="start-button" on:click={startWatching}>Restart</button>
                {/if}
            </div>
        </div>
    {/if}
</div>