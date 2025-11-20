<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onDestroy } from 'svelte';
    import { contextUpdates } from './ioskEvents.js';

    export let targetUser; // Prop passed when window is created
    export let consoleWs; // Reference to the console's WebSocket for unsubscribing

    let contextData = null;
    let activeTab = 'overview';

    const unsubscribeStore = contextUpdates.subscribe(update => {
        if (update && update.targetUser === targetUser) {
            contextData = update.data;
        }
    });

    onDestroy(() => {
        // Unsubscribe from the Svelte store
        unsubscribeStore();

        // Unsubscribe from backend updates
        if (consoleWs && consoleWs.readyState === WebSocket.OPEN) {
            consoleWs.send(JSON.stringify({ type: 'ui_context_unsubscribe', targetUser }));
        }
    });
    
    // --- Helper Functions (copied from IoskConsole.svelte for consistency) ---
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

    function formatBytes(bytes, decimals = 2) {
        if (bytes == null || bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function formatDate(isoString) {
        if (!isoString) return 'N/A';
        try {
            return new Date(isoString).toLocaleString();
        } catch (e) {
            return 'Invalid Date';
        }
    }

    // --- Computed properties for Telemetry ---
    let telemetryData = [];
    $: if (contextData && contextData.tokenStats) {
        const stats = contextData.tokenStats;
        telemetryData = [
            { label: 'Cumulative Input', tokens: stats.cumulative_input_tokens, bytes: stats.cumulative_input_bytes },
            { label: 'Cumulative Output', tokens: stats.cumulative_output_tokens, bytes: stats.cumulative_output_bytes },
            { label: 'Last Trip Input', tokens: stats.last_trip_input_tokens, bytes: stats.last_trip_input_bytes },
            { label: 'Last Trip Output', tokens: stats.last_trip_output_tokens, bytes: stats.last_trip_output_bytes },
            { label: 'Banked Memory', tokens: stats.banked_tokens, bytes: stats.banked_bytes },
            { label: 'Session History', tokens: stats.history_tokens, bytes: stats.history_bytes },
            { label: 'Caching Context', tokens: stats.caching_context_tokens, bytes: stats.caching_context_bytes },
        ];
    }

</script>

<style>
    :global(:root) { /* Ensure ANSI colors are available if not globally defined */
        --ansi-black: #2c3e50; --ansi-red: #c0392b; --ansi-green: #27ae60; --ansi-yellow: #f1c40f; --ansi-blue: #2980b9; --ansi-magenta: #8e44ad; --ansi-cyan: #16a085; --ansi-white: #bdc3c7;
        --ansi-bright-black: #95a5a6; --ansi-bright-red: #e74c3c; --ansi-bright-green: #2ecc71; --ansi-bright-yellow: #f39c12; --ansi-bright-blue: #3498db; --ansi-bright-magenta: #9b59b6; --ansi-bright-cyan: #1abc9c; --ansi-bright-white: #ecf0f1;
    }
    .inspector-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-size: 14px;
    }
    .header {
        padding: 10px;
        flex-shrink: 0;
    }
    h1 {
        font-size: 1.2em;
        margin: 0;
        color: var(--title-bar-text);
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 5px;
    }
    .tabs {
        display: flex;
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
    }
    .tab-button {
        padding: 8px 16px;
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        border-bottom: 2px solid transparent;
        margin-bottom: -1px; /* Overlap the container border */
        outline: none;
    }
    .tab-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .tab-button.active {
        color: var(--ansi-bright-blue);
        border-bottom-color: var(--ansi-bright-blue);
    }
    .tab-content {
        padding: 15px;
        overflow-y: auto;
        flex-grow: 1;
    }
    .waiting-text {
        color: #7f8c8d;
        padding: 15px;
    }
    .section {
        margin-bottom: 20px;
    }
    .section-title {
        font-weight: bold;
        color: var(--title-bar-text);
        margin-bottom: 8px;
        border-bottom: 1px dotted var(--border-color);
        padding-bottom: 4px;
    }
    .key-value-grid {
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 5px 15px;
    }
    .key-value-grid .key {
        color: var(--ansi-cyan);
        text-align: right;
    }
    .key-value-grid .value {
        word-break: break-all;
    }
    .command-history-list {
        list-style: decimal;
        padding-left: 20px;
        margin: 0;
    }
    .command-history-list li {
        padding: 2px 0;
    }
    details {
        border: 1px solid var(--border-color);
        border-radius: 3px;
        margin-bottom: 10px;
    }
    summary {
        padding: 8px;
        cursor: pointer;
        background-color: var(--title-bar-bg);
        font-weight: bold;
    }
    .content-box {
        padding: 10px;
        background-color: var(--window-bg);
        white-space: pre-wrap;
        word-break: break-all;
        max-height: 400px;
        overflow-y: auto;
    }
    .history-entry {
        border-bottom: 1px solid var(--border-color);
        padding: 8px 0;
    }
    .history-entry:last-child {
        border-bottom: none;
    }
    .history-entry-header {
        color: var(--ansi-yellow);
        margin-bottom: 5px;
    }
    .telemetry-grid {
        display: grid;
        grid-template-columns: auto max-content max-content;
        gap: 4px 12px;
        align-items: center;
    }
    .telemetry-grid span:nth-child(3n-2) { /* Label */
        font-weight: bold;
        text-align: right;
        color: var(--title-bar-text);
    }
    .telemetry-grid span:nth-child(3n-1) { /* Bytes */
        text-align: right;
        color: var(--ansi-bright-black);
    }
    .telemetry-grid span:nth-child(3n) { /* Tokens */
        text-align: right;
    }
</style>

<div class="inspector-container">
    {#if contextData}
        <div class="header">
            <h1>Context for {contextData.user}</h1>
        </div>

        <div class="tabs">
            <button class="tab-button" class:active={activeTab === 'overview'} on:click={() => activeTab = 'overview'}>Overview</button>
            <button class="tab-button" class:active={activeTab === 'environment'} on:click={() => activeTab = 'environment'}>Environment</button>
            <button class="tab-button" class:active={activeTab === 'aiContext'} on:click={() => activeTab = 'aiContext'}>AI Context</button>
            <button class="tab-button" class:active={activeTab === 'history'} on:click={() => activeTab = 'history'}>Command History</button>
            <button class="tab-button" class:active={activeTab === 'telemetry'} on:click={() => activeTab = 'telemetry'}>Telemetry</button>
        </div>

        <div class="tab-content">
            {#if activeTab === 'overview'}
                <div class="section">
                    <h2 class="section-title">User Details</h2>
                    <div class="key-value-grid">
                        <span class="key">Login Time:</span>
                        <span class="value">{formatDate(contextData.loginTime)}</span>
                        
                        <span class="key">Bot:</span>
                        <span class="value">{contextData.isBot ? 'Yes' : 'No'}</span>
                        
                        <span class="key">Super User:</span>
                        <span class="value">{contextData.isSuperUser ? 'Yes' : 'No'}</span>
                    </div>
                </div>
                <div class="section">
                    <h2 class="section-title">Session State</h2>
                    <div class="key-value-grid">
                         <span class="key">PWD:</span>
                         <span class="value">{contextData.pwd}</span>
                    </div>
                </div>
            {:else if activeTab === 'environment'}
                <div class="section">
                    <h2 class="section-title">Environment Variables</h2>
                    <div class="key-value-grid">
                        {#each Object.entries(contextData.env) as [key, value]}
                            <span class="key">{key}:</span>
                            <span class="value">{value}</span>
                        {:else}
                            <span class="value">No environment variables set.</span>
                        {/each}
                    </div>
                </div>
                <div class="section">
                    <h2 class="section-title">Aliases</h2>
                    <div class="key-value-grid">
                        {#each Object.entries(contextData.aliases) as [key, value]}
                            <span class="key">{key}:</span>
                            <span class="value">{value}</span>
                        {:else}
                            <span class="value">No aliases defined.</span>
                        {/each}
                    </div>
                </div>
            {:else if activeTab === 'aiContext'}
                <div class="section">
                    <details open>
                        <summary>Preamble</summary>
                        <pre class="content-box">{contextData.aiContext.preamble || '(empty)'}</pre>
                    </details>
                </div>
                <div class="section">
                    <details open>
                        <summary>Memory Banks ({contextData.aiContext.banks.length})</summary>
                        <div class="content-box">
                            {#each contextData.aiContext.banks as bank}
                                <details>
                                    <summary>{bank.name}</summary>
                                    <pre class="content-box" style="background-color: var(--console-bg); margin-top: 5px;">{bank.content}</pre>
                                </details>
                            {:else}
                                No banks loaded.
                            {/each}
                        </div>
                    </details>
                </div>
                <div class="section">
                     <details open>
                        <summary>Session History ({contextData.aiContext.sessionHistory.length} entries)</summary>
                        <div class="content-box">
                            {#each contextData.aiContext.sessionHistory as entry (entry.number)}
                                <div class="history-entry">
                                    <div class="history-entry-header">Entry #{entry.number}</div>
                                    <pre style="margin: 0;">{@html parseAnsi(entry.content)}</pre>
                                </div>
                            {:else}
                                No session history.
                            {/each}
                        </div>
                    </details>
                </div>
            {:else if activeTab === 'history'}
                <div class="section">
                     <h2 class="section-title">Command History</h2>
                     {#if contextData.commandHistory && contextData.commandHistory.length > 0}
                        <ol class="command-history-list">
                            {#each contextData.commandHistory as cmd, i (i)}
                                <li>{cmd}</li>
                            {/each}
                        </ol>
                     {:else}
                        <p>No command history.</p>
                     {/if}
                </div>
            {:else if activeTab === 'telemetry'}
                <div class="section">
                    <h2 class="section-title">Token Statistics</h2>
                    <div class="telemetry-grid">
                        {#each telemetryData as item}
                            <span>{item.label}:</span>
                            <span>({formatBytes(item.bytes)})</span>
                            <span>{item.tokens.toLocaleString('en-US')} tokens</span>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>
    {:else}
        <p class="waiting-text">Waiting for context data for {targetUser}...</p>
    {/if}
</div>