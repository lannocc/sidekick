<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, tick } from 'svelte';
    import { get } from 'svelte/store';
    import { createFsAdapter } from '../fs_adapter.js';
    import { marked } from 'marked';
    import { windows } from '../windows.js';
    import { activeConsoles } from '../apps.js';
    import { parseAnsi } from '../ansi.js';
    import hljs from 'highlight.js/lib/core';
    import javascript from 'highlight.js/lib/languages/javascript';
    import python from 'highlight.js/lib/languages/python';
    import css from 'highlight.js/lib/languages/css';
    import xml from 'highlight.js/lib/languages/xml';
    import 'highlight.js/styles/atom-one-dark.css';

    hljs.registerLanguage('javascript', javascript);
    hljs.registerLanguage('js', javascript);
    hljs.registerLanguage('python', python);
    hljs.registerLanguage('py', python);
    hljs.registerLanguage('css', css);
    hljs.registerLanguage('xml', xml);
    hljs.registerLanguage('html', xml);
    hljs.registerLanguage('svelte', xml);

    export let id;
    export let groupId;
    export let connectionType;
    export let consoleId = null;
    export let path;
    export let consoleConnection = null;
    export let mode = 'rendered';

    let content_b64 = '';
    let content_text = '';
    let content_bytes = new Uint8Array(0);
    let isBinary = false;
    let isLoading = true;
    let errorMessage = '';
    let highlighted_html = '';

    const CHUNK_SIZE = 16384;
    let total_size = 0;
    let loaded_size = 0;
    let isLoadingNextChunk = false;
    let isFollowing = false;
    let content_area_el;
    let fsAdapter;

    $: supportsTail = true;
    $: fileExtension = getFileExtension(path);
    $: isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(fileExtension);
    $: isMarkdown = ['md', 'markdown'].includes(fileExtension);
    $: isSourceCode = ['py', 'html', 'js', 'css', 'svelte', 'c', 'cpp', 'sh', 'json', 'yml', 'xml'].includes(fileExtension);
    $: isAnsiText = !isBinary && !isImage && !isMarkdown && !isSourceCode;
    $: canRender = (isImage && isBinary) || (isMarkdown && !isBinary) || (isSourceCode && !isBinary) || isAnsiText;

    $: if (connectionType === 'iosk' && consoleConnection && $windows) {
        const myConsoleTab = $windows.flatMap(w => w.tabs).find(t => t.id === consoleId);
        if (!myConsoleTab || !myConsoleTab.isConsoleConnected) {
            const key = `${consoleConnection.user}@${consoleConnection.url}`;
            const compatibleConsole = $activeConsoles.get(key);
            if (compatibleConsole) {
                consoleId = compatibleConsole.id;
                errorMessage = '';
                initialRequest();
            } else {
                consoleId = null;
                isLoading = false;
                errorMessage = 'No active IOSK connection available.';
                content_b64 = '';
            }
        }
    }

    function requestFile(offset = 0, length = -1) {
        if ((connectionType === 'iosk' && !consoleId)) {
            isLoading = false; return;
        }
        if (offset === 0) {
            isLoading = true; errorMessage = ''; content_bytes = new Uint8Array(0);
            content_text = ''; content_b64 = ''; total_size = 0; loaded_size = 0;
        }
        isLoadingNextChunk = true;
        fsAdapter.readFile(path, offset, length);
    }

    function initialRequest() {
        if (isImage) requestFile(); else requestFile(0, CHUNK_SIZE);
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
        if (content_area_el) content_area_el.scrollTop = content_area_el.scrollHeight;
    }

    function toggleFollow() {
        if (!supportsTail) return;
        isFollowing = !isFollowing;
        if (isFollowing) {
            if (loaded_size < total_size && total_size > 0) {
                requestFile(loaded_size, total_size - loaded_size);
            }
            fsAdapter.tail(path);
            scrollToBottom();
        } else {
            fsAdapter.untail(path);
        }
    }

    onMount(() => {
        fsAdapter = createFsAdapter({ connectionType, consoleId, requesterId: id });

        fsAdapter.readResponse.subscribe(data => {
            if (data && data.path === path && data.requester_id === id) {
                isLoading = false;
                isLoadingNextChunk = false;
                if (data.error) {
                    errorMessage = data.error;
                } else if (data.content_b64 != null) {
                    errorMessage = ''; // Clear previous errors on success
                    isBinary = data.is_binary;
                    total_size = data.total_size;
                    
                    if (data.length === -1 || isImage) {
                        content_b64 = data.content_b64;
                    }
                    
                    try {
                        const rawString = decodeURIComponent(escape(atob(data.content_b64))); // UTF-8 safe atob
                        const newBytes = new Uint8Array(rawString.length);
                        for (let i = 0; i < rawString.length; i++) newBytes[i] = rawString.charCodeAt(i);
                        
                        const combinedBytes = new Uint8Array(content_bytes.length + newBytes.length);
                        combinedBytes.set(content_bytes);
                        combinedBytes.set(newBytes, content_bytes.length);
                        content_bytes = combinedBytes;
                        loaded_size = content_bytes.length;
                        
                        if (!isBinary) content_text = new TextDecoder().decode(content_bytes);
                    } catch (e) {
                        errorMessage = "Error decoding file content.";
                        console.error(e);
                    }
                    if (!canRender) mode = 'raw';
                }
            }
        });

        fsAdapter.tailEvent.subscribe(event => {
            if (event && isFollowing && event.path === path) {
                if (event.error) {
                    errorMessage = event.error;
                    isFollowing = false; // Stop following on error
                    return;
                }
                if (!get(windows).find(w => w.id === groupId)?.isActive) {
                    windows.notifyActivity(groupId, id, { summary: `Content updated for ${path}` });
                }
                if (!isBinary) {
                    content_text += event.data;
                    scrollToBottom();
                }
            }
        });

        initialRequest();
    });

    onDestroy(() => {
        if (isFollowing) fsAdapter.untail(path);
        if (fsAdapter) fsAdapter.destroy();
    });

    function getFileExtension(filename) { return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase(); }
    function formatHex(value) { return value.toString(16).padStart(2, '0').toUpperCase(); }
    function isPrintable(byte) { return byte >= 32 && byte <= 126; }

    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { canRender, mode, consoleId, path });
    }

    $: if (mode === 'rendered' && isSourceCode && content_text) {
        try {
            // Only attempt to highlight if the language is explicitly registered.
            if (hljs.getLanguage(fileExtension)) {
                highlighted_html = hljs.highlight(content_text, { language: fileExtension, ignoreIllegals: true }).value;
            } else {
                // If language is not found, just render the text as-is, but escaped.
                // This avoids the "Unknown language" warning from highlight.js.
                highlighted_html = content_text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            }
        } catch(e) {
            console.error("Highlighting error:", e);
            highlighted_html = content_text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
    }
    
    export function setMode(newMode) { if (newMode === 'raw' || newMode === 'rendered') mode = newMode; }

</script>

<style>
    .viewer-container { display: flex; flex-direction: column; height: 100%; font-family: monospace; background-color: color-mix(in srgb, var(--console-bg) 42%, transparent); color: var(--console-text); font-size: 14px; user-select: text; }
    .toolbar { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background-color: color-mix(in srgb, var(--title-bar-bg) 42%, transparent); border-bottom: 1px solid var(--border-color); flex-shrink: 0; user-select: none; }
    .toolbar-path { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .toolbar-controls button { background: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--taskbar-text); padding: 2px 8px; border-radius: 3px; cursor: pointer; margin-left: 5px; }
    .toolbar-controls button:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .toolbar-controls button.active { background-color: var(--taskbar-button-hover-bg); border-color: #3498db; }
    .toolbar-controls button:disabled { opacity: 0.5; cursor: not-allowed; }
    .content-area { flex-grow: 1; overflow: auto; padding: 8px; white-space: pre-wrap; word-break: break-all; }
    .status-message { display: flex; justify-content: center; align-items: center; height: 100%; color: #7f8c8d; user-select: none; }
    .error-message { color: #e74c3c; }
    .hex-viewer table { width: 100%; border-collapse: collapse; }
    .hex-viewer td { padding: 2px 4px; }
    .hex-viewer .offset { color: #95a5a6; }
    .hex-viewer .ascii { color: #ecf0f1; }
    .rendered-image-container { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
    .rendered-image { max-width: 100%; max-height: 100%; object-fit: contain; }
    .rendered-markdown { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; white-space: normal; word-break: normal; padding: 10px; background: color-mix(in srgb, var(--window-bg) 42%, transparent); color: var(--title-bar-text); border-radius: 4px; }
    .rendered-code { margin: -8px; }
    .rendered-code .hljs { padding: 8px; font-size: 14px; border-radius: 0; }
    .loading-more { text-align: center; color: #7f8c8d; padding: 10px; }
</style>

<div class="viewer-container">
    <div class="toolbar">
        <span class="toolbar-path" title={path}>{path}</span>
        <div class="toolbar-controls">
            <button on:click={toggleFollow} class:active={isFollowing} disabled={!supportsTail || isBinary || isImage || isSourceCode}>Follow</button>
            <button on:click={() => mode = 'raw'} class:active={mode === 'raw'}>Raw</button>
            <button on:click={() => mode = 'rendered'} class:active={mode === 'rendered'} disabled={!canRender}>Rendered</button>
        </div>
    </div>
    <div class="content-area" bind:this={content_area_el} on:scroll={handleScroll}>
        {#if isLoading}
            <div class="status-message">Loading...</div>
        {:else if errorMessage}
            <div class="status-message error-message">{errorMessage}</div>
        {:else if content_bytes.length > 0}
            {#if mode === 'raw' || !canRender}
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
            {:else if mode === 'rendered'}
                {#if isImage} <div class="rendered-image-container"><img class="rendered-image" src="data:image/{fileExtension};base64,{content_b64}" alt={path}></div>
                {:else if isMarkdown} <div class="rendered-markdown">{@html marked(content_text)}</div>
                {:else if isSourceCode} <pre class="rendered-code"><code class="language-{fileExtension} hljs">{@html highlighted_html}</code></pre>
                {:else if isAnsiText} <div>{@html parseAnsi(content_text)}</div>
                {/if}
            {/if}
            {#if isLoadingNextChunk && !isFollowing}
                 <div class="loading-more">Loading more...</div>
            {/if}
        {:else}
            <div class="status-message">{ total_size === 0 ? 'File is empty.' : 'No content to display.' }</div>
        {/if}
    </div>
</div>