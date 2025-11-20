<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onDestroy } from 'svelte';
    import { contextUpdates } from './ioskEvents.js';
    import { windows } from './windows.js';

    // --- Component Props ---
    export let groupId; // The window group ID for this component instance
    export let consoleId; // The console tab ID this inspector is linked to
    export let targetUser; // The user whose context is being inspected
    export let consoleWs; // Reference to the console's WebSocket for unsubscribing
    export let isDetached = false; // Is this a popped-out view?
    export let detachedView = ''; // If so, which view to display?
    
    // If this component is rendered inline via <svelte:self>, contextData is passed directly.
    // If it's a top-level window, it will be populated by the store subscription.
    export let contextData = null;

    // --- State for the main inspector window ---
    let activeTab = 'overview';
    let detachedTabs = {
        overview: null,
        environment: null,
        history: null,
        aiContext: null,
        telemetry: null,
        json: null,
    };

    const unsubscribeStore = contextUpdates.subscribe(update => {
        if (update && update.consoleId === consoleId && update.targetUser === targetUser) {
            contextData = update.data;
        }
    });

    // Reactive statement to check if a detached window was closed
    $: if (!isDetached && $windows) {
        const openWindowIds = new Set($windows.map(w => w.id));
        let changed = false;
        for (const tabName in detachedTabs) {
            const detachedGroupId = detachedTabs[tabName];
            if (detachedGroupId && !openWindowIds.has(detachedGroupId)) {
                detachedTabs[tabName] = null;
                changed = true;
            }
        }
        if (changed) {
            detachedTabs = detachedTabs; // Trigger reactivity
        }
    }

    onDestroy(() => {
        unsubscribeStore();
        // Only the main inspector window sends the unsubscribe message when it closes.
        // Detached windows are ephemeral views.
        if (!isDetached && consoleWs && consoleWs.readyState === WebSocket.OPEN) {
            consoleWs.send(JSON.stringify({ type: 'ui_context_unsubscribe', targetUser }));
        }
    });

    function popOutTab(viewName) {
        if (!contextData) return;
        const newGroupId = windows.addWindow(IoskContextInspector, {
            title: `${viewName.charAt(0).toUpperCase() + viewName.slice(1)} - ${targetUser}`,
            consoleId: consoleId,
            targetUser: targetUser,
            consoleWs: consoleWs,
            isDetached: true,
            detachedView: viewName,
            width: 600,
            height: 500,
        });
        if (newGroupId) {
            detachedTabs[viewName] = newGroupId;
            detachedTabs = detachedTabs;
        }
    }

    // --- Helper Functions ---
    const ansiCodeToCssVar = {
        '30': 'var(--ansi-black)', '31': 'var(--ansi-red)', '32': 'var(--ansi-green)', '33': 'var(--ansi-yellow)', '34': 'var(--ansi-blue)', '35': 'var(--ansi-magenta)', '36': 'var(--ansi-cyan)', '37': 'var(--ansi-white)', '90': 'var(--ansi-bright-black)', '91': 'var(--ansi-bright-red)', '92': 'var(--ansi-bright-green)', '93': 'var(--ansi-bright-yellow)', '94': 'var(--ansi-bright-blue)', '95': 'var(--ansi-bright-magenta)', '96': 'var(--ansi-bright-cyan)', '97': 'var(--ansi-bright-white)',
    };
    function parseAnsi(text) { /* ... (implementation unchanged) ... */ }
    function formatBytes(bytes, decimals = 2) { /* ... (implementation unchanged) ... */ }
    function formatDate(isoString) { /* ... (implementation unchanged) ... */ }

    // --- Computed properties for Telemetry ---
    let telemetryData = [];
    $: if (contextData && contextData.tokenStats) { /* ... (implementation unchanged) ... */ }
</script>

<style>
    /* ... (all existing styles unchanged) ... */
    .tab-button-container {
        display: flex;
        align-items: center;
        position: relative;
    }
    .pop-out-button {
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        font-size: 1.1em;
        padding: 0 8px;
        opacity: 0.5;
        transition: opacity 0.2s;
    }
    .pop-out-button:hover {
        opacity: 1;
        color: var(--ansi-bright-blue);
    }
    .detached-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        text-align: center;
        color: var(--title-bar-text);
    }
    .detached-placeholder button {
        margin-top: 15px;
        padding: 8px 16px;
        border-radius: 3px;
        cursor: pointer;
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        background-color: var(--taskbar-button-bg);
    }
    .detached-placeholder button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
</style>

<div class="inspector-container">
    {#if !isDetached}
        <!-- MAIN INSPECTOR UI (with tabs) -->
        <div class="header">
            {#if contextData}
                <h1>Context for {contextData.user}</h1>
            {:else}
                <h1>Context for {targetUser}</h1>
            {/if}
        </div>

        <div class="tabs">
            {#each Object.keys(detachedTabs) as tabName, i (tabName)}
                {@const name = ['Overview', 'Environment', 'Commands', 'Session', 'Telemetry', 'JSON'][i]}
                <div class="tab-button-container">
                    <button class="tab-button" class:active={activeTab === tabName} on:click={() => activeTab = tabName}>
                        {name}
                    </button>
                    <button class="pop-out-button" title="Pop out to new window" on:click|stopPropagation={() => popOutTab(tabName)}>
                        ⇲
                    </button>
                </div>
            {/each}
        </div>

        <div class="tab-content">
            {#if !contextData}
                <p class="waiting-text">Waiting for context data for {targetUser}...</p>
            {:else if detachedTabs[activeTab]}
                <div class="detached-placeholder">
                    <p>Content is in a separate window.</p>
                    <button on:click={() => windows.focusWindow(detachedTabs[activeTab])}>
                        Focus Window
                    </button>
                </div>
            {:else}
                <!-- Render content inline using a recursive call to self in detached mode -->
                <svelte:self {contextData} isDetached={true} detachedView={activeTab} />
            {/if}
        </div>

    {:else if contextData}
        <!-- DETACHED/INLINE VIEW UI (no tabs) -->
        {#if detachedView === 'overview'}
            <div class="section">
                <h2 class="section-title">User Details</h2>
                <div class="key-value-grid">
                    <span class="key">Login Time:</span><span class="value">{formatDate(contextData.loginTime)}</span>
                    <span class="key">Bot:</span><span class="value">{contextData.isBot ? 'Yes' : 'No'}</span>
                    <span class="key">Super User:</span><span class="value">{contextData.isSuperUser ? 'Yes' : 'No'}</span>
                </div>
            </div>
            <div class="section">
                <h2 class="section-title">Session State</h2>
                <div class="key-value-grid">
                     <span class="key">PWD:</span><span class="value">{contextData.pwd}</span>
                </div>
            </div>
        {:else if detachedView === 'environment'}
            <div class="section">
                <h2 class="section-title">Environment Variables</h2>
                <div class="key-value-grid">{#each Object.entries(contextData.env) as [key, value]}<span class="key">{key}:</span><span class="value">{value}</span>{:else}<span class="value">No environment variables set.</span>{/each}</div>
            </div>
            <div class="section">
                <h2 class="section-title">Aliases</h2>
                <div class="key-value-grid">{#each Object.entries(contextData.aliases) as [key, value]}<span class="key">{key}:</span><span class="value">{value}</span>{:else}<span class="value">No aliases defined.</span>{/each}</div>
            </div>
        {:else if detachedView === 'aiContext'}
            <div class="section"><details open><summary>Preamble</summary><pre class="content-box">{contextData.aiContext.preamble || '(empty)'}</pre></details></div>
            <div class="section"><details open><summary>Memory Banks ({contextData.aiContext.banks.length})</summary><div class="content-box">{#each contextData.aiContext.banks as bank}<details><summary>{bank.name}</summary><pre class="content-box" style="background-color: var(--console-bg); margin-top: 5px;">{bank.content}</pre></details>{:else}No banks loaded.{/each}</div></details></div>
            <div class="section"><details open><summary>Session History ({contextData.aiContext.sessionHistory.length} entries)</summary><div class="content-box">{#each contextData.aiContext.sessionHistory as entry (entry.number)}<div class="history-entry"><div class="history-entry-header">Entry #{entry.number}</div><pre style="margin: 0;">{@html parseAnsi(entry.content)}</pre></div>{:else}No session history.{/each}</div></details></div>
        {:else if detachedView === 'history'}
            <div class="section">
                 <h2 class="section-title">Command History</h2>
                 {#if contextData.commandHistory && contextData.commandHistory.length > 0}<ol class="command-history-list">{#each contextData.commandHistory as cmd, i (i)}<li>{cmd}</li>{/each}</ol>{:else}<p>No command history.</p>{/if}
            </div>
        {:else if detachedView === 'telemetry'}
            <div class="section">
                <h2 class="section-title">Token Statistics</h2>
                <div class="telemetry-grid">{#each telemetryData as item}<span>{item.label}:</span><span>({formatBytes(item.bytes)})</span><span>{item.tokens.toLocaleString('en-US')} tokens</span>{/each}</div>
            </div>
        {:else if detachedView === 'json'}
            <div class="section">
                <h2 class="section-title">Raw Context Data</h2>
                <pre class="content-box">{JSON.stringify(contextData, null, 2)}</pre>
            </div>
        {/if}
    {/if}
</div>