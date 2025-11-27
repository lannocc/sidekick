<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { newAskWindow } from './windows.js';
    import { updateBox, deleteBox } from './local.js';

    export let box;

    // Phase 1: Auto-arrange on desktop. Position is not persisted yet.
    let x = 100 + (box.id % 5) * 200;
    let y = 100 + Math.floor(box.id / 5) * 150;

    let isDragging = false;
    let dragOffsetX, dragOffsetY;
    let boxEl;

    // --- Context Menu State ---
    let contextMenu = { visible: false, x: 0, y: 0 };

    function handleRightClick(event) {
        event.preventDefault();
        event.stopPropagation();
        contextMenu = { visible: true, x: event.clientX, y: event.clientY };
    }
    function closeContextMenu() {
        contextMenu.visible = false;
    }

    // Close menu on outside click
    function handleWindowClick(event) {
        if (contextMenu.visible && !event.target.closest('.context-menu')) {
            closeContextMenu();
        }
    }
    onMount(() => window.addEventListener('click', handleWindowClick));
    onDestroy(() => window.removeEventListener('click', handleWindowClick));

    // --- Context Menu Actions ---
    function renameBox() {
        closeContextMenu();
        const newName = prompt(`Rename box "${box.name}":`, box.name);
        if (newName && newName.trim() !== '' && newName !== box.name) {
            updateBox(box.id, newName);
        }
    }

    function deleteBoxConfirm() {
        closeContextMenu();
        if (confirm(`Are you sure you want to delete the box "${box.name}"?`)) {
            deleteBox(box.id);
        }
    }

    function askBox() {
        closeContextMenu();
        if (box.type === 'local') {
            newAskWindow([{ path: box.context, type: 'dir' }]);
        } else {
            alert(`"Ask..." for 'iosk' boxes is not yet implemented.`);
        }
    }

    // --- Dragging Logic ---
    function onDragStart(event) {
        if (event.button !== 0 || event.target.closest('.panel:not(.center)')) return;
        isDragging = true;
        dragOffsetX = event.clientX - x;
        dragOffsetY = event.clientY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd, { once: true });
        document.body.style.cursor = 'move';
    }

    function onDrag(event) {
        if (!isDragging) return;
        x = event.clientX - dragOffsetX;
        y = event.clientY - dragOffsetY;
    }

    function onDragEnd() {
        isDragging = false;
        document.body.style.cursor = 'auto';
        window.removeEventListener('mousemove', onDrag);
        // Position persistence will be handled in a later phase
    }
</script>

<style>
    .box {
        position: absolute;
        width: 180px;
        height: 120px;
        cursor: pointer;
        user-select: none;
        z-index: 10;
        transition: z-index 0s 0.3s; /* Delay z-index change until after animation */
    }
    .box:hover {
        z-index: 100;
        transition-delay: 0s;
    }

    .panel {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        box-sizing: border-box;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        color: var(--title-bar-text);
        text-align: center;
    }

    .center {
        z-index: 2;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px;
        cursor: move;
    }

    .top, .bottom, .left, .right {
        z-index: 1;
        opacity: 0;
        transform: scale(0.95);
        pointer-events: none;
    }

    .box:hover .top {
        transform: translateY(-105%);
        opacity: 1;
        pointer-events: auto;
    }
    .box:hover .bottom {
        transform: translateY(105%);
        opacity: 1;
        pointer-events: auto;
    }
    .box:hover .left {
        transform: translateX(-105%);
        opacity: 1;
        pointer-events: auto;
    }
    .box:hover .right {
        transform: translateX(105%);
        opacity: 1;
        pointer-events: auto;
    }

    .box-name {
        font-size: 1.1em;
        font-weight: bold;
        word-break: break-word;
    }
    .box-context {
        font-size: 0.8em;
        opacity: 0.7;
        margin-top: 5px;
        word-break: break-all;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .context-menu {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10001;
        display: flex;
        flex-direction: column;
        padding: 4px 0;
        min-width: 120px;
    }
    .context-menu button {
        background: none;
        border: none;
        color: var(--taskbar-text);
        padding: 8px 12px;
        text-align: left;
        cursor: pointer;
        font-size: 14px;
    }
    .context-menu button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .context-menu .delete {
        color: #e74c3c;
    }
    .context-menu .delete:hover {
        background-color: #c0392b;
        color: white;
    }
</style>

<div
    class="box"
    bind:this={boxEl}
    style:left="{x}px"
    style:top="{y}px"
    on:contextmenu={handleRightClick}
>
    <!-- Panels for Unfolding Animation -->
    <div class="panel top"></div>
    <div class="panel bottom"></div>
    <div class="panel left"></div>
    <div class="panel right"></div>

    <!-- Center Panel with Content -->
    <div class="panel center" on:mousedown={onDragStart}>
        <div class="box-name">{box.name}</div>
        <div class="box-context" title={box.context}>{box.context}</div>
    </div>
</div>

{#if contextMenu.visible}
    <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
        <button on:click={askBox}>Ask...</button>
        <button on:click={renameBox}>Rename...</button>
        <div style="height: 1px; background-color: var(--border-color); margin: 4px 0;"></div>
        <button on:click={deleteBoxConfirm} class="delete">Delete</button>
    </div>
{/if}