<!-- sv/Shortcut.svelte -->
<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { newLocalFileExplorer, newLocalFileViewer } from './windows.js';
    import { desktopView, selectedItems, wasDraggingItems } from './desktop.js';
    import { desktopShortcuts } from './local.js';
    import { get } from 'svelte/store';

    export let id;
    export let name;
    export let type; // 'file' or 'dir'
    export let path;
    export let x;
    export let y;

    $: isSelected = $selectedItems.has(id);

    function handleClick() {
        if (get(wasDraggingItems)) {
            return;
        }
        if (type === 'dir') {
            newLocalFileExplorer({ initialPath: path, title: `Files - ${name}` });
        } else if (type === 'file') {
            newLocalFileViewer({ path, title: name });
        }
    }
</script>

<style>
    .shortcut {
        position: absolute;
        width: 80px;
        display: flex;
        flex-direction: column;
        align-items: center;
        cursor: pointer;
        user-select: none;
        padding: 4px;
        border-radius: 4px;
        transition: background-color 0.1s ease-in-out;
        pointer-events: auto;
        border: 1px solid transparent;
    }
    .shortcut.selected {
        background-color: rgba(52, 152, 219, 0.3);
        border-color: rgba(52, 152, 219, 0.7);
    }
    .shortcut:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    .shortcut.selected:hover {
        background-color: rgba(52, 152, 219, 0.4);
    }
    .icon {
        font-size: 48px;
        line-height: 1;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.4);
    }
    .name {
        color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
        font-size: 12px;
        text-align: center;
        word-break: break-word;
        margin-top: 4px;
    }
</style>

<div
    class="shortcut"
    class:selected={isSelected}
    data-id={id}
    data-type="shortcut"
    style:left="{x}px"
    style:top="{y}px"
    on:click={handleClick}
>
    <div class="icon">{type === 'dir' ? '🗂️' : '📄'}</div>
    <div class="name">{name}</div>
</div>