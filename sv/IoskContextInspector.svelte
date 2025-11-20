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
</script>

<style>
    .inspector-container {
        padding: 10px;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        height: 100%;
        overflow: auto;
        font-size: 14px;
    }
    h1 {
        font-size: 1.2em;
        margin-top: 0;
        margin-bottom: 10px;
        color: var(--title-bar-text);
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 5px;
    }
    pre {
        white-space: pre-wrap;
        word-break: break-all;
    }
    .waiting-text {
        color: #7f8c8d;
    }
</style>

<div class="inspector-container">
    {#if contextData}
        <!-- UI with tabs/sections for pwd, env, aliases, AI context, etc. -->
        <h1>Context for {contextData.user}</h1>
        <pre>{JSON.stringify(contextData, null, 2)}</pre>
    {:else}
        <p class="waiting-text">Waiting for context data for {targetUser}...</p>
    {/if}
</div>