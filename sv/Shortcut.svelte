<!-- sv/Shortcut.svelte -->
<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { newLocalFileExplorer, newLocalFileViewer } from './windows.js';
    import { desktopView } from './desktop.js';
    import { desktopShortcuts } from './local.js';
    import { get } from 'svelte/store';

    export let id;
    export let name;
    export let type; // 'file' or 'dir'
    export let path;
    export let x;
    export let y;

    function handleDoubleClick() {
        if (type === 'dir') {
            newLocalFileExplorer({ initialPath: path, title: `Files - ${name}` });
        } else if (type === 'file') {
            newLocalFileViewer({ path, title: name });
        }
    }

    function onDragStart(event) {
        event.dataTransfer.setData('application/sidekick-shortcut-move', JSON.stringify({id}));
        event.dataTransfer.effectAllowed = 'move';
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
    }
    .shortcut:hover {
        background-color: rgba(255, 255, 255, 0.1);
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
    style:left="{x}px"
    style:top="{y}px"
    on:dblclick={handleDoubleClick}
    draggable="true"
    on:dragstart={onDragStart}
>
    <div class="icon">{type === 'dir' ? '🗂️' : '📄'}</div>
    <div class="name">{name}</div>
</div>
