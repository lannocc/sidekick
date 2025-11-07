<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { fileSystemRequests, fileSystemResponses } from './ioskEvents.js';
    import { marked } from 'marked';

    export let id; // window id
    export let consoleId;
    export let path;
    
    let content_b64 = '';
    let content_text = '';
    let content_bytes = new Uint8Array(0);
    let isBinary = false;
    let isLoading = true;
    let errorMessage = '';
    let mode = 'rendered'; // 'raw' or 'rendered'

    let unsubscribeResponses;

    onMount(() => {
        // Request file content on mount
        const request = {
            consoleId,
            requesterId: id, // Use window id to identify response
            command: {
                type: 'fs_read',
                path
            }
        };
        fileSystemRequests.set({ ...request, timestamp: Date.now() });

        unsubscribeResponses = fileSystemResponses.subscribe(response => {
            if (response && response.requesterId === id) {
                isLoading = false;
                const { data } = response;
                if (data.error) {
                    errorMessage = data.error;
                } else {
                    isBinary = data.is_binary;
                    content_b64 = data.content_b64;
                    
                    try {
                        const rawString = atob(content_b64);
                        const bytes = new Uint8Array(rawString.length);
                        for (let i = 0; i < rawString.length; i++) {
                            bytes[i] = rawString.charCodeAt(i);
                        }
                        content_bytes = bytes;

                        if (!isBinary) {
                            content_text = new TextDecoder().decode(bytes);
                        }
                    } catch (e) {
                        errorMessage = "Error decoding file content.";
                        console.error(e);
                    }
                    
                    // Default to raw view if rendering isn't supported
                    if (!canRender) {
                        mode = 'raw';
                    }
                }
            }
        });
    });

    onDestroy(() => {
        if (unsubscribeResponses) unsubscribeResponses();
    });

    function formatHex(value) {
        return value.toString(16).padStart(2, '0').toUpperCase();
    }

    function isPrintable(byte) {
        return byte >= 32 && byte <= 126;
    }
    
    function getFileExtension(filename) {
        return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
    }
    
    $: fileExtension = getFileExtension(path);
    $: isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(fileExtension);
    $: isMarkdown = ['md', 'markdown'].includes(fileExtension);
    $: canRender = (isImage && isBinary) || (isMarkdown && !isBinary);

</script>

<style>
    .viewer-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-size: 14px;
        user-select: text;
    }
    .toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 8px;
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
        user-select: none;
    }
    .toolbar-path {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .toolbar-controls button {
        background: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--taskbar-text);
        padding: 2px 8px;
        border-radius: 3px;
        cursor: pointer;
        margin-left: 5px;
    }
    .toolbar-controls button:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .toolbar-controls button.active {
        background-color: var(--taskbar-button-hover-bg);
        border-color: #3498db;
    }
    .toolbar-controls button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .content-area {
        flex-grow: 1;
        overflow: auto;
        padding: 8px;
        white-space: pre-wrap;
        word-break: break-all;
    }
    .status-message {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
        color: #7f8c8d;
        user-select: none;
    }
    .error-message {
        color: #e74c3c;
    }
    .hex-viewer table {
        width: 100%;
        border-collapse: collapse;
    }
    .hex-viewer td {
        padding: 2px 4px;
    }
    .hex-viewer .offset { color: #95a5a6; }
    .hex-viewer .ascii { color: #ecf0f1; }
    .rendered-image-container {
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .rendered-image {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }
    .rendered-markdown {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        white-space: normal;
        word-break: normal;
        padding: 10px;
        background: var(--window-bg);
        color: var(--title-bar-text);
        border-radius: 4px;
    }
</style>

<div class="viewer-container">
    <div class="toolbar">
        <span class="toolbar-path" title={path}>{path}</span>
        <div class="toolbar-controls">
            <button on:click={() => mode = 'raw'} class:active={mode === 'raw'}>Raw</button>
            <button on:click={() => mode = 'rendered'} class:active={mode === 'rendered'} disabled={!canRender}>
                Rendered
            </button>
        </div>
    </div>
    <div class="content-area">
        {#if isLoading}
            <div class="status-message">Loading...</div>
        {:else if errorMessage}
            <div class="status-message error-message">{errorMessage}</div>
        {:else if content_b64}
            {#if mode === 'raw'}
                {#if isBinary}
                    <div class="hex-viewer">
                        <table>
                            <tbody>
                                {#each Array(Math.ceil(content_bytes.length / 16)) as _, i}
                                    {@const slice = content_bytes.slice(i * 16, (i + 1) * 16)}
                                    <tr>
                                        <td class="offset">{(i * 16).toString(16).padStart(8, '0')}</td>
                                        {#each Array(16) as __, j}
                                            <td>{j < slice.length ? formatHex(slice[j]) : ''}</td>
                                        {/each}
                                        <td class="ascii">
                                            {#each slice as byte}
                                                {isPrintable(byte) ? String.fromCharCode(byte) : '.'}
                                            {/each}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                {:else}
                    {content_text}
                {/if}
            {:else if mode === 'rendered' && canRender}
                {#if isImage}
                    <div class="rendered-image-container">
                        <img class="rendered-image" src="data:image/{fileExtension};base64,{content_b64}" alt={path}>
                    </div>
                {:else if isMarkdown}
                    <div class="rendered-markdown">{@html marked(content_text)}</div>
                {/if}
            {:else}
                <!-- Fallback to raw view if mode is 'rendered' but not possible -->
                {content_text}
            {/if}
        {:else}
            <div class="status-message">No content to display.</div>
        {/if}
    </div>
</div>