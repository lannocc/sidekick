<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { fileSystemRequests, fileSystemResponses } from './ioskEvents.js';

    export let consoleId;

    let currentPath = '/';
    let items = []; // { name, type, size }
    let errorMessage = '';

    let unsubscribeResponses;

    function requestPath(path) {
        errorMessage = '';
        const request = {
            consoleId,
            command: {
                type: 'fs_list',
                path
            }
        };
        // Use a unique object to ensure svelte store triggers update for same consecutive requests
        fileSystemRequests.set({ ...request, timestamp: Date.now() });
    }

    function handleItemClick(item) {
        if (item.type === 'dir') {
            let newPath;
            if (item.name === '..') {
                // Navigate up
                if (currentPath === '/') return;
                newPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
            } else {
                // Navigate down
                newPath = currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`;
            }
            requestPath(newPath);
        }
        // Future: Could add file view logic here
    }

    onMount(() => {
        unsubscribeResponses = fileSystemResponses.subscribe(response => {
            if (response && response.consoleId === consoleId) {
                const { path, listing, error } = response.data;

                if (error) {
                    errorMessage = error;
                    items = [];
                } else if (listing) {
                    currentPath = path;
                    // Add parent directory ".." for navigation if not at root
                    const parentDir = { name: '..', type: 'dir', size: -1 };
                    const sortedItems = listing.sort((a, b) => {
                        if (a.type === b.type) return a.name.localeCompare(b.name);
                        return a.type === 'dir' ? -1 : 1; // Directories first
                    });
                    items = (path !== '/') ? [parentDir, ...sortedItems] : sortedItems;
                }
            }
        });
        // Initial request for the root directory
        requestPath(currentPath);
    });

    onDestroy(() => {
        if (unsubscribeResponses) {
            unsubscribeResponses();
        }
    });
</script>

<style>
    .explorer-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-size: 14px;
        user-select: none;
    }
    .path-bar {
        padding: 4px 8px;
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
        white-space: nowrap;
        overflow-x: auto;
        flex-shrink: 0; /* Prevents the path bar from shrinking */
    }
    .error-message {
        color: #e74c3c;
        padding: 8px;
        flex-shrink: 0; /* Prevents the error message from shrinking */
    }
    .item-list {
        flex-grow: 1;
        overflow-y: auto;
        padding: 4px;
    }
    .item {
        display: flex;
        padding: 2px 8px;
        cursor: pointer;
        border-radius: 2px;
    }
    .item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .item-icon {
        width: 25px;
        flex-shrink: 0;
    }
    .item-name {
        flex-grow: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .item-size {
        width: 80px;
        text-align: right;
        flex-shrink: 0;
        color: #7f8c8d;
    }
</style>

<div class="explorer-container">
    <div class="path-bar">
        <span>{currentPath}</span>
    </div>
    {#if errorMessage}
        <div class="error-message">{errorMessage}</div>
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
</div>
