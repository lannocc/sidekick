<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher } from 'svelte';
    import { windows } from './windows.js';

    export let id;
    export let component;
    export let title;
    export let x;
    export let y;
    export let width;
    export let height;
    export let zIndex;
    export let minimized;

    const dispatch = createEventDispatcher();

    let isDragging = false;
    let isResizing = false;
    let dragOffsetX, dragOffsetY;

    function onDragStart(event) {
        if (event.target.classList.contains('window-control')) return;
        isDragging = true;
        dragOffsetX = event.clientX - x;
        dragOffsetY = event.clientY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd);
        windows.focusWindow(id);
    }

    function onDrag(event) {
        if (!isDragging) return;
        x = event.clientX - dragOffsetX;
        y = event.clientY - dragOffsetY;
        windows.updateWindowProps(id, { x, y });
    }

    function onDragEnd() {
        isDragging = false;
        window.removeEventListener('mousemove', onDrag);
        window.removeEventListener('mouseup', onDragEnd);
    }

    function onResizeStart(event) {
        isResizing = true;
        dragOffsetX = event.clientX;
        dragOffsetY = event.clientY;
        window.addEventListener('mousemove', onResize);
        window.addEventListener('mouseup', onResizeEnd);
        windows.focusWindow(id);
    }

    function onResize(event) {
        if (!isResizing) return;
        const dx = event.clientX - dragOffsetX;
        const dy = event.clientY - dragOffsetY;
        width += dx;
        height += dy;
        dragOffsetX = event.clientX;
        dragOffsetY = event.clientY;
        windows.updateWindowProps(id, { width, height });
    }

    function onResizeEnd() {
        isResizing = false;
        window.removeEventListener('mousemove', onResize);
        window.removeEventListener('mouseup', onResizeEnd);
    }

    function handleFocus() {
        windows.focusWindow(id);
    }
</script>

<style>
    .window-frame {
        position: absolute;
        border: 1px solid var(--border-color);
        background-color: var(--window-bg);
        border-radius: 6px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        display: flex;
        flex-direction: column;
        min-width: 250px;
        min-height: 150px;
    }
    .window-frame.minimized {
        display: none;
    }
    .title-bar {
        height: 30px;
        background-color: var(--title-bar-bg);
        color: var(--title-bar-text);
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 8px;
        cursor: move;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        user-select: none;
    }
    .title-text {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .window-controls {
        display: flex;
        gap: 5px;
    }
    .window-control {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        cursor: pointer;
        border: 1px solid rgba(0,0,0,0.2);
    }
    .close { background-color: #ff5f56; }
    .minimize { background-color: #ffbd2e; }
    .maximize { background-color: #27c93f; }
    .content-area {
        flex-grow: 1;
        overflow: auto;
        padding: 5px;
    }
    .resize-handle {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 12px;
        height: 12px;
        cursor: se-resize;
    }
</style>

<div
    class="window-frame"
    class:minimized
    style:left="{x}px"
    style:top="{y}px"
    style:width="{width}px"
    style:height="{height}px"
    style:z-index="{zIndex}"
    on:mousedown={handleFocus}
>
    <div class="title-bar" on:mousedown={onDragStart}>
        <span class="title-text">{title}</span>
        <div class="window-controls">
            <div class="window-control close" title="Close" on:click={() => windows.removeWindow(id)}></div>
            <div class="window-control minimize" title="Minimize" on:click={() => windows.toggleMinimize(id)}></div>
            <div class="window-control maximize" title="Maximize (Not Implemented)"></div>
        </div>
    </div>
    <div class="content-area">
        <svelte:component this={component} {id} bind:title={title} />
    </div>
    <div class="resize-handle" on:mousedown={onResizeStart}></div>
</div>

