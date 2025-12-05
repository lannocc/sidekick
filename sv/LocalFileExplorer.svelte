<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { sendMessage, fsListResponse, fsReadResponse, fsError, connectionStatus, createBox } from './local.js';
    import { newAskWindow, windows } from './windows.js';
    import { fileSelection } from './iosk.js';
    import { get } from 'svelte/store';
    import { windowView, TASKBAR_HEIGHT } from './desktop.js';

    export let id;
    export let groupId;
    export let pickerTargetId = null;
    export let initialPath = '.';

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

    let contextMenu = {
        visible: false,
        x: 0,
        y: 0,
        item: null
    };

    let unsubscribeList, unsubscribeRead, unsubscribeError, unsubscribeStatus;

    function handleRightClick(event, item) {
        event.preventDefault();
        const { panX, panY, zoom } = get(windowView);
        const menuX = (event.clientX - panX) / zoom;
        const menuY = ((event.clientY - TASKBAR_HEIGHT) - panY) / zoom;
        contextMenu = { visible: true, x: menuX, y: menuY, item };
    }

    function closeContextMenu() {
        contextMenu = { visible: false, x: 0, y: 0, item: null };
    }

    function onAsk() {
        if (!contextMenu.item) return;
        const itemPath = contextMenu.item.name === '..'
            ? (currentPath.substring(0, currentPath.lastIndexOf('/')) || '/')
            : (currentPath === '/' ? `/${contextMenu.item.name}` : `${currentPath}/${contextMenu.item.name}`);
        
        newAskWindow([itemPath]);
        closeContextMenu();
    }

    function onBoxThis() {
        if (!contextMenu.item || contextMenu.item.type !== 'dir') return;

        const itemName = contextMenu.item.name;
        const itemPath = itemName === '..'
            ? (currentPath.substring(0, currentPath.lastIndexOf('/')) || '/')
            : (currentPath === '/' ? `/${itemName}` : `${currentPath}/${itemName}`);
        
        const defaultBoxName = itemPath.split('/').pop() || (itemPath === '/' ? 'root' : 'New Box');

        const boxName = prompt(`Enter a name for the new Box for path "${itemPath}":`, defaultBoxName);
        if (!boxName) return;

        createBox(boxName, 'local', itemPath, { screenX: contextMenu.x, screenY: contextMenu.y });
        closeContextMenu();
    }

    function requestPath(path) {
        errorMessage = '';
        sendMessage({ type: 'fs_list', path });
    }

    function selectCurrentPath() {
        if (pickerTargetId) {
            fileSelection.set({ targetId: pickerTargetId, path: currentPath });
            windows.removeWindow(groupId);
        }
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
            if (pickerTargetId) {
                fileSelection.set({ targetId: pickerTargetId, path: filePath });
                windows.removeWindow(groupId);
            } else {
                viewer = { visible: true, path: filePath, content: 'Loading...', error: '' };
                sendMessage({ type: 'fs_read', path: filePath });
            }
        }
    }

    function handleDragStart(event, item) {
        if (!item || item.name === '..') {
            event.preventDefault();
            return;
        }
        const itemPath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
        const data = {
            type: item.type, // 'file' or 'dir'
            path: itemPath,
            name: item.name
        };
        event.dataTransfer.setData('application/sidekick-fs-item', JSON.stringify(data));
        event.dataTransfer.effectAllowed = 'copy';
    }

    onMount(() => {
        window.addEventListener('click', closeContextMenu);

        unsubscribeStatus = connectionStatus.subscribe(s => {
            status = s;
            if (s === 'connected') {
                requestPath(initialPath);
            } else if (s === 'disconnected' || s === 'error') {
                errorMessage = "Not connected to local backend. Run 'sk local'.";
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
            window.removeEventListener('click', closeContextMenu);
        };
    });

</script>

<style>
    .explorer-container { display: flex; flex-direction: column; height: 100%; font-family: monospace; background-color: var(--console-bg); color: var(--console-text); font-size: 14px; user-select: none; }
    .path-bar { padding: 4px 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); white-space: nowrap; overflow-x: auto; flex-shrink: 0; display: flex; justify-content: space-between; align-items: center; }
    .path-bar button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--taskbar-text); padding: 2px 8px; border-radius: 3px; cursor: pointer; margin-left: 10px; flex-shrink: 0; }
    .path-bar button:hover { background-color: var(--taskbar-button-hover-bg); }
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
    .context-menu { position: fixed; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 10001; display: flex; flex-direction: column; padding: 4px 0; min-width: 120px; }
    .context-menu button { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .context-menu button:hover { background-color: var(--taskbar-button-hover-bg); }
</style>

<div class="explorer-container">
    <div class="path-bar">
        <span>{currentPath}</span>
        {#if pickerTargetId}
            <button on:click={selectCurrentPath}>Select Current Folder</button>
        {/if}
    </div>
    {#if errorMessage}
        <div class="status-bar error">{errorMessage}</div>
    {:else}
        <div class="status-bar">Status: {status}</div>
    {/if}
    <div class="item-list">
        {#each items as item (item.name)}
            <div 
                class="item" 
                on:click={() => handleItemClick(item)} 
                on:contextmenu={e => handleRightClick(e, item)} 
                title={item.name}
                draggable="true"
                on:dragstart={e => handleDragStart(e, item)}
            >
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

    {#if contextMenu.visible}
        <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
            <button on:click={onAsk}>Ask...</button>
            {#if contextMenu.item && contextMenu.item.type === 'dir'}
                <button on:click={onBoxThis}>Box this</button>
            {/if}
        </div>
    {/if}
</div>