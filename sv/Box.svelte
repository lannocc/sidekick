<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { newAskWindow, dragState } from './windows.js';
    import { updateBox, deleteBox, savePanelConfig } from './local.js';
    import Board from './Board.svelte';

    export let box;

    // Phase 1: Auto-arrange on desktop. Position is not persisted yet.
    let x = 100 + (box.id % 5) * 200;
    let y = 100 + Math.floor(box.id / 5) * 150;

    let isDragging = false;
    let dragOffsetX, dragOffsetY;
    let boxEl;

    // --- Dynamic Unfold Direction ---
    let unfoldDirection = 'up';

    function updateUnfoldDirection() {
        if (!boxEl || typeof window === 'undefined') return;
        // Check if the vertical midpoint of the box is in the top or bottom half of theviewport
        const boxMidY = y + boxEl.offsetHeight / 2;
        unfoldDirection = boxMidY > window.innerHeight / 2 ? 'up' : 'down';
    }

    // Update direction whenever the 'y' coordinate changes (e.g., during drag)
    $: y, updateUnfoldDirection();


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
    onMount(() => {
        updateUnfoldDirection(); // Set initial direction
        window.addEventListener('click', handleWindowClick);
    });
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
    
    function setCoverImage() {
        closeContextMenu();
        const url = prompt("Enter URL for cover image:");
        if (url) {
            savePanelConfig(box.id, 'cover', 'image', { url });
        }
    }

    // --- Dragging & Drop Target Logic ---
    function onDragStart(event) {
        // Prevent dragging if it's not a left-click, or if the click
        // is on an unfolded side panel (top, bottom, left, right).
        if (event.button !== 0 || event.target.closest('.panel.top, .panel.bottom, .panel.left, .panel.right')) return;
        
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

    function handlePanelMouseEnter(location) {
        const state = get(dragState);
        if (state?.draggingGroupId) {
            dragState.update(s => ({...s, dropTargetBoxPanel: { boxId: box.id, location }}));
        }
    }

    function handlePanelMouseLeave(location) {
        const state = get(dragState);
        if (state?.dropTargetBoxPanel?.boxId === box.id && state?.dropTargetBoxPanel?.location === location) {
            dragState.update(s => ({...s, dropTargetBoxPanel: null}));
        }
    }

    function handleDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'link';
    }

    function handleDrop(event, location) {
        event.preventDefault();
        try {
            const data = JSON.parse(event.dataTransfer.getData('application/json'));
            if (data.type === 'dashLayout') {
                savePanelConfig(box.id, location, 'dash', data.layout);
            }
        } catch(e) {
            console.error("Drop failed:", e);
        }
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
    /* This pseudo-element creates a large, invisible hover area around the box,
       preventing the hover state from being lost when moving the mouse across gaps. */
    .box::after {
        content: '';
        position: absolute;
        /* Sized to be larger than the maximum unfolded state */
        top: -260px;
        bottom: -260px;
        left: -190px;
        right: -190px;
        z-index: -1;
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
        padding: 5px;
    }
    .panel.drop-target {
        border-color: #3498db;
        box-shadow: 0 0 15px 5px rgba(52, 152, 219, 0.6);
    }

    .center {
        z-index: 3;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: move;
    }

    /* When a cover is present and the box is not hovered, the center panel is obscured */
    .box.has-cover:not(:hover) .center {
        pointer-events: none;
    }

    .cover, .top, .bottom, .left, .right {
        z-index: 1;
        opacity: 0;
        transform: scale(0.95);
        pointer-events: none;
    }

    /* If a cover exists, it's visible by default, on top, and draggable */
    .box.has-cover .cover {
        opacity: 1;
        transform: scale(1);
        z-index: 4;
        pointer-events: auto;
        cursor: move;
    }

    /* Dynamic cover panel unfolding */
    .box.unfold-up:hover .cover {
        transform: translateY(-210%);
        opacity: 1;
        pointer-events: auto;
        z-index: 2;
    }
    .box.unfold-down:hover .cover {
        transform: translateY(210%);
        opacity: 1;
        pointer-events: auto;
        z-index: 2;
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
        min-width: 150px;
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
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .context-menu .delete { color: #e74c3c; }
    .context-menu .delete:hover { background-color: #c0392b; color: white; }
</style>

<div
    class="box"
    class:has-cover={box.panels?.cover}
    class:unfold-up={unfoldDirection === 'up'}
    class:unfold-down={unfoldDirection === 'down'}
    bind:this={boxEl}
    style:left="{x}px"
    style:top="{y}px"
    on:contextmenu={handleRightClick}
    on:mousedown={onDragStart}
>
    <!-- Panels for Unfolding Animation -->
    <div class="panel cover" class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'cover'} on:mouseenter={() => handlePanelMouseEnter('cover')} on:mouseleave={() => handlePanelMouseLeave('cover')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'cover')}>
        {#if box.panels?.cover} <Board board_type={box.panels.cover.board_type} board_config={box.panels.cover.board_config} /> {/if}
    </div>
    <div class="panel top" class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'top'} on:mouseenter={() => handlePanelMouseEnter('top')} on:mouseleave={() => handlePanelMouseLeave('top')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'top')}>
        {#if box.panels?.top} <Board board_type={box.panels.top.board_type} board_config={box.panels.top.board_config} /> {/if}
    </div>
    <div class="panel bottom" class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'bottom'} on:mouseenter={() => handlePanelMouseEnter('bottom')} on:mouseleave={() => handlePanelMouseLeave('bottom')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'bottom')}>
        {#if box.panels?.bottom} <Board board_type={box.panels.bottom.board_type} board_config={box.panels.bottom.board_config} /> {/if}
    </div>
    <div class="panel left" class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'left'} on:mouseenter={() => handlePanelMouseEnter('left')} on:mouseleave={() => handlePanelMouseLeave('left')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'left')}>
        {#if box.panels?.left} <Board board_type={box.panels.left.board_type} board_config={box.panels.left.board_config} /> {/if}
    </div>
    <div class="panel right" class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'right'} on:mouseenter={() => handlePanelMouseEnter('right')} on:mouseleave={() => handlePanelMouseLeave('right')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'right')}>
        {#if box.panels?.right} <Board board_type={box.panels.right.board_type} board_config={box.panels.right.board_config} /> {/if}
    </div>

    <!-- Center Panel with Content -->
    <div class="panel center" class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'center'} on:mouseenter={() => handlePanelMouseEnter('center')} on:mouseleave={() => handlePanelMouseLeave('center')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'center')}>
        {#if box.panels?.center}
            <Board board_type={box.panels.center.board_type} board_config={box.panels.center.board_config} />
        {:else}
            <div class="box-name">{box.name}</div>
            <div class="box-context" title={box.context}>{box.context}</div>
        {/if}
    </div>
</div>

{#if contextMenu.visible}
    <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
        <button on:click={askBox}>Ask...</button>
        <button on:click={renameBox}>Rename...</button>
        <div class="menu-separator"></div>
        <button on:click={setCoverImage}>Set Cover Image...</button>
        <div class="menu-separator"></div>
        <button on:click={deleteBoxConfirm} class="delete">Delete</button>
    </div>
{/if}