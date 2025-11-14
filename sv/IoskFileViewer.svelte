<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, tick } from 'svelte';
    import { fileSystemRequests, fileSystemResponses, fileSystemTailEvents } from './ioskEvents.js';
    import { marked } from 'marked';
    import { windows } from './windows.js';

    export let id; // window id
    export let groupId;
    export let consoleId;
    export let path;
    export let consoleConnection = null; // Passed during Dash restore

    let content_b64 = '';
    let content_text = '';
    let content_bytes = new Uint8Array(0);
    let isBinary = false;
    let isLoading = true;
    let errorMessage = '';
    export let mode = 'rendered'; // 'raw' or 'rendered', now exported to be settable via props

    // --- State for Chunking & Tailing ---
    const CHUNK_SIZE = 16384; // 16KB
    let total_size = 0;
    let loaded_size = 0;
    let isLoadingNextChunk = false;
    let isFollowing = false;
    let content_area_el;
    let unsubscribeResponses;
    let unsubscribeTailEvents;


    $: if (consoleConnection && $windows) {
        // Check if our current consoleId is still valid
        const currentConsole = $windows.find(w => w.id === consoleId);
        if (!currentConsole || !currentConsole.isConsoleConnected) {
            // If not, clear it.
            if (consoleId) {
                consoleId = null;
                isLoading = false;
                errorMessage = 'Connection lost. Waiting for reconnection...';
                content_b64 = '';
            }
        }

        // If we don't have a consoleId, try to find one
        if (!consoleId) {
            const compatibleConsoleTab = $windows.flatMap(w => w.tabs).find(t =>
                t.componentName === 'IoskConsole' &&
                t.isConsoleConnected &&
                t.consoleConnection &&
                t.consoleConnection.url === consoleConnection.url &&
                t.consoleConnection.user === consoleConnection.user
            );

            if (compatibleConsoleTab) {
                // Found one!
                consoleId = compatibleConsoleTab.id;
                initialRequest();
            } else {
                // Still no connection.
                isLoading = false;
                errorMessage = 'No active IOSK connection available. Waiting for connection...';
                content_b64 = '';
            }
        }
    }

    function requestFile(offset = 0, length = -1) {
        if (!consoleId) {
            isLoading = false;
            return false;
        }

        if (offset === 0) {
            isLoading = true;
            errorMessage = '';
            content_bytes = new Uint8Array(0);
            content_text = '';
            content_b64 = '';
            total_size = 0;
            loaded_size = 0;
        }

        isLoadingNextChunk = true;
        const request = {
            consoleId,
            requesterId: id,
            command: { type: 'fs_read', path, offset, length }
        };
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
        return true;
    }

    function initialRequest() {
        if (isImage) {
            requestFile(); // Request whole image file
        } else {
            requestFile(0, CHUNK_SIZE); // Start chunked loading for others
        }
    }

    function handleScroll() {
        if (!content_area_el || isLoadingNextChunk || isFollowing) return;
        if (loaded_size >= total_size && total_size > 0) return;

        const el = content_area_el;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 200) {
            requestFile(loaded_size, CHUNK_SIZE);
        }
    }

    async function scrollToBottom() {
        await tick();
        if (content_area_el) {
            content_area_el.scrollTop = content_area_el.scrollHeight;
        }
    }

    function sendTailRequest(type) {
        if (!consoleId) return;
        const request = {
            consoleId,
            command: { type, path }
        };
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
    }

    function toggleFollow() {
        isFollowing = !isFollowing;
        if (isFollowing) {
            if (loaded_size < total_size && total_size > 0) {
                requestFile(loaded_size, total_size - loaded_size);
            }
            sendTailRequest('fs_tail_start');
            scrollToBottom();
        } else {
            sendTailRequest('fs_tail_stop');
        }
    }

    onMount(() => {
        unsubscribeResponses = fileSystemResponses.subscribe(response => {
            if (response && response.requesterId === id && response.data.type === 'fs_read_response') {
                isLoading = false;
                isLoadingNextChunk = false;
                const { data } = response;
                if (data.error) {
                    errorMessage = data.error;
                } else {
                    isBinary = data.is_binary;
                    total_size = data.total_size;

                    if (data.length === -1) { // Heuristic for full file load (images)
                        content_b64 = data.content_b64;
                    }

                    try {
                        const rawString = atob(data.content_b64);
                        const newBytes = new Uint8Array(rawString.length);
                        for (let i = 0; i < rawString.length; i++) {
                            newBytes[i] = rawString.charCodeAt(i);
                        }
                        
                        const combinedBytes = new Uint8Array(content_bytes.length + newBytes.length);
                        combinedBytes.set(content_bytes);
                        combinedBytes.set(newBytes, content_bytes.length);
                        content_bytes = combinedBytes;
                        loaded_size = content_bytes.length;

                        if (!isBinary) {
                            content_text = new TextDecoder().decode(content_bytes);
                        }
                    } catch (e) {
                        errorMessage = "Error decoding file content.";
                        console.error(e);
                    }

                    if (!canRender) {
                        mode = 'raw';
                    }
                }
            }
        });

        unsubscribeTailEvents = fileSystemTailEvents.subscribe(event => {
            if (event && event.consoleId === consoleId && isFollowing && event.data.path === path) {
                if (!isBinary) {
                    content_text += event.data.data;
                    scrollToBottom();
                }
            }
        });

        if (consoleId) {
            initialRequest();
        }
    });

    onDestroy(() => {
        if (isFollowing) {
            sendTailRequest('fs_tail_stop');
        }
        if (unsubscribeResponses) unsubscribeResponses();
        if (unsubscribeTailEvents) unsubscribeTailEvents();
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
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { canRender, mode, consoleId });
    }

    export function setMode(newMode) {
        if (newMode === 'raw' || newMode === 'rendered') {
            mode = newMode;
        }
    }

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
    .loading-more {
        text-align: center;
        color: #7f8c8d;
        padding: 10px;
    }
</style>

<div class="viewer-container">
    <div class="toolbar">
        <span class="toolbar-path" title={path}>{path}</span>
        <div class="toolbar-controls">
            <button on:click={toggleFollow} class:active={isFollowing} disabled={isBinary || isImage}>Follow</button>
            <button on:click={() => mode = 'raw'} class:active={mode === 'raw'}>Raw</button>
            <button on:click={() => mode = 'rendered'} class:active={mode === 'rendered'} disabled={!canRender}>
                Rendered
            </button>
        </div>
    </div>
    <div class="content-area" bind:this={content_area_el} on:scroll={handleScroll}>
        {#if isLoading}
            <div class="status-message">Loading...</div>
        {:else if errorMessage}
            <div class="status-message error-message">{errorMessage}</div>
        {:else if content_bytes.length > 0}
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
            {#if isLoadingNextChunk && !isFollowing}
                 <div class="loading-more">Loading more...</div>
            {/if}
        {:else}
            <div class="status-message">{ total_size === 0 ? 'File is empty.' : 'No content to display.' }</div>
        {/if}
    </div>
</div>