<!-- sv/LocalFileViewer.svelte -->
<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { sendMessage, fsReadResponse, fsError } from '../bridge.js';

    export let path; // The full path to the file to view

    let content = 'Loading...';
    let error = '';

    let unsubscribeRead, unsubscribeError;

    onMount(() => {
        sendMessage({ type: 'fs_read', path });

        unsubscribeRead = fsReadResponse.subscribe(response => {
            if (response && response.path === path) {
                content = response.content;
                error = '';
            }
        });

        unsubscribeError = fsError.subscribe(err => {
            if (err && err.path === path) {
                error = err.error;
                content = '';
            }
        });

        return () => {
            if (unsubscribeRead) unsubscribeRead();
            if (unsubscribeError) unsubscribeError();
        };
    });
</script>

<style>
    .viewer-container {
        height: 100%;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-family: monospace;
        font-size: 14px;
        overflow: auto;
        white-space: pre-wrap;
        padding: 8px;
        box-sizing: border-box;
    }
    .error {
        color: #e74c3c;
    }
</style>

<div class="viewer-container">
    {#if error}
        <div class="error">Error loading file: {error}</div>
    {:else}
        {content}
    {/if}
</div>
