<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { connect, sendMessage, fsListResponse, fsReadResponse, fsError, connectionStatus } from './localAgentStore.js';

    let currentPath = '/'; // A reasonable default
    let items = [];
    let errorMessage = '';
    let status = 'disconnected';

    let viewer = {
        visible: false,
        path: '',
        content: '',
        error: ''
    };

    let unsubscribeList, unsubscribeRead, unsubscribeError, unsubscribeStatus;

    function requestPath(path) {
        errorMessage = '';
        sendMessage({ type: 'fs_list', path });
    }

    function handleItemClick(item) {
        if (item.type === 'dir') {
            let newPath;
            if (item.name === '..') {
                if (currentPath === '/') return;
                newPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
            } else {
                newPath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
            }
            requestPath(newPath);
        } else if (item.type === 'file') {
            const filePath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
            viewer = { visible: true, path: filePath, content: 'Loading...', error: '' };
            sendMessage({ type: 'fs_read', path: filePath });
        }
    }

    onMount(() => {
        connect();

        unsubscribeStatus = connectionStatus.subscribe(s => {
            status = s;
            if (s === 'connected') {
                requestPath('.');
            } else if (s === 'disconnected' || s === 'error') {
                errorMessage = "Not connected to local agent. Run 'sk local'.";
                items = [];
            }
        });

        unsubscribeList = fsListResponse.subscribe(response => {
            if (response) {
                currentPath = response.path;
                const parentDir = { name: '..', type: 'dir', size: -1 };
                const sortedItems = (response.entries || []).sort((a, b) => {
                    if (a.type === b.type) return a.name.localeCompare(b.name);
                    return a.type === 'dir' ? -1 : 1;
                });
                items = (response.path !== '/') ? [parentDir, ...sortedItems] : sortedItems;
                errorMessage = '';
            }
        });

        unsubscribeRead = fsReadResponse.subscribe(response => {
            if (response && viewer.visible && viewer.path === response.path) {
                viewer.content = response.content;
                viewer.error = '';
            }
        });

        unsubscribeError = fsError.subscribe(err => {
            if (err) {
                 if (viewer.visible && viewer.path === err.path) {
                    viewer.error = err.error;
                    viewer.content = '';
                } else {
                    errorMessage = err.error;
                }
            }
        });

        return () => {
            if(unsubscribeList) unsubscribeList();
            if(unsubscribeRead) unsubscribeRead();
            if(unsubscribeError) unsubscribeError();
            if(unsubscribeStatus) unsubscribeStatus();
        };
    });

</script>

<style>
    .explorer-container { display: flex; flex-direction: column; height: 100%; font-family: monospace; background-color: var(--console-bg); color: var(--console-text); font-size: 14px; user-select: none; }
    .path-bar { padding: 4px 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); white-space: nowrap; overflow-x: auto; flex-shrink: 0; }
    .status-bar { padding: 4px 8px; font-size: 0.9em; color: #7f8c8d; }
    .status-bar.error { color: #e74c3c; }
    .item-list { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .item { display: flex; padding: 2px 8px; cursor: pointer; border-radius: 2px; }
    .item:hover { background-color: var(--taskbar-button-hover-bg); }
    .item-icon { width: 25px; flex-shrink: 0; }
    .item-name { flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .item-size { width: 80px; text-align: right; flex-shrink: 0; color: #7f8c8d; }
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 80%; height: 80%; display: flex; flex-direction: column; gap: 15px; }
    .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    .modal-header h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; }
    .modal-header button { background: none; border: none; font-size: 1.5em; cursor: pointer; color: var(--title-bar-text); }
    .modal-body { flex-grow: 1; overflow: auto; white-space: pre-wrap; font-family: monospace; }
</style>

<div class="explorer-container">
    <div class="path-bar">
        <span>{currentPath}</span>
    </div>
    {#if errorMessage}
        <div class="status-bar error">{errorMessage}</div>
    {:else}
        <div class="status-bar">Status: {status}</div>
    {/if}
    <div class="item-list">
        {#each items as item (item.name)}
            <div class="item" on:click={() => handleItemClick(item)} title={item.name}>
                <span class="item-icon">{item.type === 'dir' ? '🗂️' : '📄'}</span>
                <span class="item-name">{item.name}</span>
                <span class="item-size">
                    {#if item.type === 'file' && item.size >= 0}
                        {item.size}
                    {/if}
                </span>
            </div>
        {/each}
    </div>

    {#if viewer.visible}
    <div class="modal-overlay" on:click|self={() => viewer.visible = false}>
        <div class="modal-content">
            <div class="modal-header">
                <h3>{viewer.path}</h3>
                <button on:click={() => viewer.visible = false}>&times;</button>
            </div>
            <div class="modal-body">
                {#if viewer.error}
                    <div class="status-bar error">{viewer.error}</div>
                {:else}
                    {viewer.content}
                {/if}
            </div>
        </div>
    </div>
    {/if}
</div>

