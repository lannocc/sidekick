<!-- sv/IoskWatch.svelte -->
<script>
    import { onMount, onDestroy, tick } from 'svelte';
    import { fileSystemRequests, fileSystemResponses } from './ioskEvents.js';
    import { windows } from './windows.js';

    // --- Color Handling ---
    const ansiCodeToCssVar = {
        '30': 'var(--ansi-black)', '31': 'var(--ansi-red)', '32': 'var(--ansi-green)', '33': 'var(--ansi-yellow)',
        '34': 'var(--ansi-blue)', '35': 'var(--ansi-magenta)', '36': 'var(--ansi-cyan)', '37': 'var(--ansi-white)',
        '90': 'var(--ansi-bright-black)', '91': 'var(--ansi-bright-red)', '92': 'var(--ansi-bright-green)', '93': 'var(--ansi-bright-yellow)',
        '94': 'var(--ansi-bright-blue)', '95': 'var(--ansi-bright-magenta)', '96': 'var(--ansi-bright-cyan)', '97': 'var(--ansi-bright-white)',
    };

    function parseAnsi(text) {
        if (typeof text !== 'string') return '';
        const ansiRegex = /\u001b\[(\d*)m/g; // Use * to also match ESC[m (empty code)
        let openSpan = false;
        
        let sanitizedText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

        let html = sanitizedText.replace(ansiRegex, (match, code) => {
            let newHtml = '';
            if (openSpan) {
                newHtml += '</span>';
                openSpan = false;
            }
            // An empty code or a '0' are both reset codes
            if (code === '0' || code === '') {
                // This is a reset code, we just closed the span.
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

    export let id; // tab id
    export let groupId;
    export let consoleId;
    export let consoleConnection = null; // for dash restore

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
    let statusMessage = '';
    
    let commandInputEl;
    let watchTimer = null;
    const requesterId = `watch-${id}`; // Unique requester for this window

    let unsubscribeResponses;

    // --- Dash Restore Logic ---
    $: if (consoleConnection && $windows) {
        // Find a console if ours is missing
        const consoleTab = $windows.flatMap(w => w.tabs).find(t => t.id === consoleId);
        if (!consoleTab || !consoleTab.isConsoleConnected) {
            const compatibleConsoleTab = $windows.flatMap(w => w.tabs).find(t =>
                t.componentName === 'IoskConsole' &&
                t.isConsoleConnected &&
                t.consoleConnection &&
                t.consoleConnection.url === consoleConnection.url &&
                t.consoleConnection.user === consoleConnection.user
            );

            if (compatibleConsoleTab) {
                if (consoleId !== compatibleConsoleTab.id) {
                    consoleId = compatibleConsoleTab.id;
                }
                statusMessage = '';
                if (watchState === 'watching') {
                    // if it was watching when saved, restart it
                    startWatching();
                }
            } else {
                statusMessage = 'Waiting for IOSK connection...';
            }
        }
    }

    // --- Update window store for Dash saving ---
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { 
            consoleId,
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
                    output = data.output;
                }
            }
        });

        // If restored from Dash and was watching, start immediately.
        if (consoleId && watchState === 'watching') {
            startWatching();
        }

        tick().then(() => commandInputEl?.focus());
    });

    onDestroy(() => {
        if (unsubscribeResponses) unsubscribeResponses();
        if (watchTimer) clearInterval(watchTimer);
    });

    function sendWatchRequest() {
        if (!consoleId) {
            output = '[Error] No active console connection.';
            stopWatching();
            return;
        }
        const request = {
            consoleId,
            requesterId,
            command: {
                type: 'exec_command',
                command_str: command,
                pwd: pwd
            }
        };
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
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
    .status-message { color: var(--ansi-yellow); font-style: italic; }
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
                <button class="start-button" on:click={startWatching} disabled={!command.trim() || !consoleId}>Start Watching</button>
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
    {#if statusMessage}
        <div class="status-message">{statusMessage}</div>
    {/if}
</div>