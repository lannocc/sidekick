<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { newAskWindow, dragState, windows, generateBoardConfigFromWindow, newWebBrowser, newLocalFileExplorer, newLocalTerminal } from './windows.js';
    import { updateBox, deleteBox, savePanelConfig, updateBoxTransform, setBoxCover } from './local.js';
    import { dashLayouts } from './desktop.js';
    import Board from './Board.svelte';

    export let box;

    // --- Position, Size, and Scale ---
    let x = box.x ?? 100 + (box.id % 5) * 200;
    let y = box.y ?? 100 + Math.floor(box.id / 5) * 150;
    let scale = box.scale ?? 1.0;

    // Make local state reactive to prop changes from the store
    $: if (box.x != null) x = box.x;
    $: if (box.y != null) y = box.y;
    $: if (box.scale != null) scale = box.scale;
    $: coverPanelLocation = box.cover_panel_location;
    $: emptySidePanels = ['top', 'bottom', 'left', 'right'].filter(loc => !box.panels?.[loc]);
    $: canSetCover = emptySidePanels.length > 0 && !coverPanelLocation;

    const BASE_WIDTH = 180;
    let desktopWidth = window.innerWidth;
    let desktopHeight = window.innerHeight - 40; // Approx taskbar height
    let aspectRatio = desktopHeight / desktopWidth;

    $: boxWidth = BASE_WIDTH * scale;
    $: boxHeight = BASE_WIDTH * aspectRatio * scale;

    let isDragging = false;
    let wasDragging = false; // To distinguish between a drag and a click
    let dragOffsetX, dragOffsetY;
    let boxEl;
    let saveTransformTimeout;

    // --- Hover State for Unfolding ---
    let isHovered = false;
    let hoverTimeout;

    function handleMouseEnter() {
        if (hoverTimeout) clearTimeout(hoverTimeout);
        isHovered = true;
    }

    function handleMouseLeave() {
        // Use a timeout to keep the panels open while the mouse travels over the gap
        hoverTimeout = setTimeout(() => {
            isHovered = false;
        }, 150);
    }

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
        if (showBoardPicker && !event.target.closest('.board-picker')) {
            showBoardPicker = false;
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
            newAskWindow([box.context]);
        }
    }

    function openTerminal() {
        closeContextMenu();
        if (box.type === 'local' && box.context) {
            newLocalTerminal({ title: `Terminal - ${box.name}`, initialPath: box.context });
        }
    }

    function openFiles() {
        closeContextMenu();
        if (box.type === 'local' && box.context) {
            newLocalFileExplorer({ title: `Files - ${box.name}`, initialPath: box.context });
        }
    }
    
    function setCoverImage() {
        closeContextMenu();
        if (!canSetCover) {
            alert("No empty side panels available or a cover is already set.");
            return;
        }
        const url = prompt("Enter URL for cover image:");
        if (url) {
            // Pick the first available empty panel
            const location = emptySidePanels[0];
            // Save the image to that panel
            savePanelConfig(box.id, location, 'image', { url });
            // Designate that panel as the cover
            setBoxCover(box.id, location);
        }
    }

    function setCoverImageFromPicker() {
        const { location } = boardPickerProps;
        showBoardPicker = false;
        
        const url = prompt("Enter URL for cover image:");
        if (url) {
            // Save the image to the specific panel that was clicked
            savePanelConfig(box.id, location, 'image', { url });
            // Designate that panel as the cover
            setBoxCover(box.id, location);
        }
    }

    function clearCoverImage() {
        closeContextMenu();
        if (coverPanelLocation) {
            // Set board to empty for that panel, which will delete the panel record
            savePanelConfig(box.id, coverPanelLocation, 'empty', null);
            // Unset the cover location on the box
            setBoxCover(box.id, null);
        }
    }

    // --- Dragging, Scaling & Drop Target Logic ---
    function onDragStart(event) {
        // Prevent dragging if it's not a left-click.
        if (event.button !== 0) return;
        
        wasDragging = false; // Reset for the new interaction
        isDragging = true;
        dragOffsetX = event.clientX - x;
        dragOffsetY = event.clientY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd, { once: true });
        document.body.style.cursor = 'move';
    }

    function onDrag(event) {
        if (!isDragging) return;
        wasDragging = true; // If we move, it's a drag
        x = event.clientX - dragOffsetX;
        y = event.clientY - dragOffsetY;
    }

    function onDragEnd() {
        isDragging = false;
        document.body.style.cursor = 'auto';
        window.removeEventListener('mousemove', onDrag);
        if (wasDragging) {
            updateBoxTransform(box.id, Math.round(x), Math.round(y), scale);
        }
    }
    
    function handleWheel(event) {
        if (event.ctrlKey || event.altKey) {
            event.preventDefault();
            const zoomStep = 0.05;
            const delta = event.deltaY < 0 ? zoomStep : -zoomStep;
            
            scale = Math.max(0.2, scale + delta);

            if (saveTransformTimeout) clearTimeout(saveTransformTimeout);
            saveTransformTimeout = setTimeout(() => {
                updateBoxTransform(box.id, Math.round(x), Math.round(y), scale);
            }, 300);
        }
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

    // --- Board Picker State & Logic ---
    let showBoardPicker = false;
    let boardPickerProps = {}; // { location, x, y }

    function getActiveTabTitle(win) {
        if (!win || !win.tabs) return '...';
        const activeTab = win.tabs.find(t => t.id === win.activeTabId);
        return activeTab ? activeTab.title : (win.tabs[0]?.title || 'Window');
    }

    function selectWindow(group) {
        const { location } = boardPickerProps;
        const board_config = generateBoardConfigFromWindow(group);
        const board_type = group.tabs.length > 1 ? 'tabs' : 'window';
        savePanelConfig(box.id, location, board_type, board_config);
        windows.removeWindow(group.id);
        showBoardPicker = false;
    }

    function selectDash(layout) {
        const { location } = boardPickerProps;
        savePanelConfig(box.id, location, 'dash', layout);
        showBoardPicker = false;
    }

    function handlePanelClick(event, location) {
        if (wasDragging) {
            // This was a drag, not a click. Do nothing.
            return;
        }

        if (showBoardPicker) {
            showBoardPicker = false;
            return;
        }

        const panelConfig = box.panels?.[location];
        const isSidePanel = ['top', 'bottom', 'left', 'right'].includes(location);

        if (!panelConfig || panelConfig.board_type === 'empty') {
            // Handle clicks on empty panels
            if (location === 'center' && box.type === 'local') {
                newLocalFileExplorer({ initialPath: box.context, title: `Local Files - ${box.name}` });
            } else if (isSidePanel) {
                // For side panels, open the board picker.
                // We must stop propagation so the window's 'click' listener doesn't immediately close the picker.
                event.stopPropagation();
                boardPickerProps = {
                    location,
                    x: event.clientX,
                    y: event.clientY,
                };
                showBoardPicker = true;
            }
            // Clicking empty center (non-local) panels does nothing.
        } else {
            // Handle clicks on occupied panels
            const { board_type, board_config } = panelConfig;

            if (board_type === 'image') {
                // Action for any image panel
                if (board_config?.url) {
                    newWebBrowser({ initialUrl: board_config.url });
                }
            } else if (isSidePanel) {
                // For occupied side panels, restore the board
                if (board_type === 'window' || board_type === 'tabs') {
                    windows.restoreWindow(board_config);
                    // savePanelConfig(box.id, location, 'empty', null); // Keep board on panel after restore
                } else if (board_type === 'dash') {
                    if (board_config?.windowGroups) {
                        for (const group of board_config.windowGroups) {
                            windows.restoreWindow(group);
                        }
                    }
                    // savePanelConfig(box.id, location, 'empty', null); // Keep board on panel after restore
                }
            }
            // Clicking occupied center (non-image) panels does nothing for now.
        }
    }
</script>

<style>
    .box {
        position: absolute;
        /* width: 180px; */ /* Now set by style directive */
        /* height: 120px; */ /* Now set by style directive */
        cursor: pointer;
        user-select: none;
        z-index: 10;
        transition: z-index 0s 0.3s; /* Delay z-index change until after animation */
    }

    .box.is-hovered {
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

    /* All side panels start hidden and scaled down */
    .top, .bottom, .left, .right {
        z-index: 1;
        opacity: 0;
        transform: scale(0.95);
        pointer-events: none;
    }


    /* --- Unfolding Animations on Hover --- */

    .box.is-hovered .top {
        transform: translateY(-105%);
        opacity: 1;
        pointer-events: auto;
    }
    .box.is-hovered .bottom {
        transform: translateY(105%);
        opacity: 1;
        pointer-events: auto;
    }
    .box.is-hovered .left {
        transform: translateX(-105%);
        opacity: 1;
        pointer-events: auto;
    }
    .box.is-hovered .right {
        transform: translateX(105%);
        opacity: 1;
        pointer-events: auto;
    }


    /* Skinny/flat styles for empty side panels when hovered */
    .box.is-hovered .top.is-empty {
        transform-origin: bottom center;
        transform: translateY(-105%) scaleY(0.15);
    }
    .box.is-hovered .bottom.is-empty {
        transform-origin: top center;
        transform: translateY(105%) scaleY(0.15);
    }
    .box.is-hovered .left.is-empty {
        transform-origin: right center;
        transform: translateX(-105%) scaleX(0.15);
    }
    .box.is-hovered .right.is-empty {
        transform-origin: left center;
        transform: translateX(105%) scaleX(0.15);
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
    .context-menu button:disabled {
        color: #7f8c8d;
        cursor: not-allowed;
        background-color: transparent;
    }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .context-menu .delete { color: #e74c3c; }
    .context-menu .delete:hover { background-color: #c0392b; color: white; }

    .board-picker {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10001;
        display: flex;
        flex-direction: column;
        padding: 4px 0;
        min-width: 200px;
        max-height: 300px;
        overflow-y: auto;
    }
    .picker-header {
        padding: 4px 12px;
        font-weight: bold;
        color: var(--title-bar-text);
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
    }
    .picker-item {
        background: none;
        border: none;
        color: var(--taskbar-text);
        padding: 8px 12px;
        text-align: left;
        cursor: pointer;
        font-size: 14px;
        width: 100%;
    }
    .picker-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .empty-message {
        padding: 8px 12px;
        color: #7f8c8d;
        font-style: italic;
    }
</style>

<div
    class="box"
    class:unfold-up={unfoldDirection === 'up'}
    class:unfold-down={unfoldDirection === 'down'}
    class:is-hovered={isHovered}
    bind:this={boxEl}
    style:left="{x}px"
    style:top="{y}px"
    style:width="{boxWidth}px"
    style:height="{boxHeight}px"
    on:mouseenter={handleMouseEnter}
    on:mouseleave={handleMouseLeave}
    on:wheel={handleWheel}
>
    <!-- Panels for Unfolding Animation -->
    <div class="panel top" on:click={e => handlePanelClick(e, 'top')} class:is-empty={!box.panels?.top} class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'top'} on:mouseenter={() => handlePanelMouseEnter('top')} on:mouseleave={() => handlePanelMouseLeave('top')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'top')}>
        {#if box.panels?.top} <Board board_type={box.panels.top.board_type} board_config={box.panels.top.board_config} /> {/if}
    </div>
    <div class="panel bottom" on:click={e => handlePanelClick(e, 'bottom')} class:is-empty={!box.panels?.bottom} class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'bottom'} on:mouseenter={() => handlePanelMouseEnter('bottom')} on:mouseleave={() => handlePanelMouseLeave('bottom')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'bottom')}>
        {#if box.panels?.bottom} <Board board_type={box.panels.bottom.board_type} board_config={box.panels.bottom.board_config} /> {/if}
    </div>
    <div class="panel left" on:click={e => handlePanelClick(e, 'left')} class:is-empty={!box.panels?.left} class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'left'} on:mouseenter={() => handlePanelMouseEnter('left')} on:mouseleave={() => handlePanelMouseLeave('left')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'left')}>
        {#if box.panels?.left} <Board board_type={box.panels.left.board_type} board_config={box.panels.left.board_config} /> {/if}
    </div>
    <div class="panel right" on:click={e => handlePanelClick(e, 'right')} class:is-empty={!box.panels?.right} class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'right'} on:mouseenter={() => handlePanelMouseEnter('right')} on:mouseleave={() => handlePanelMouseLeave('right')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'right')}>
        {#if box.panels?.right} <Board board_type={box.panels.right.board_type} board_config={box.panels.right.board_config} /> {/if}
    </div>

    <!-- Center Panel with Content -->
    <div class="panel center" on:mousedown={onDragStart} on:click={e => handlePanelClick(e, 'center')} on:contextmenu={handleRightClick} class:drop-target={$dragState?.dropTargetBoxPanel?.boxId === box.id && $dragState?.dropTargetBoxPanel?.location === 'center'} on:mouseenter={() => handlePanelMouseEnter('center')} on:mouseleave={() => handlePanelMouseLeave('center')} on:dragover={handleDragOver} on:drop={e => handleDrop(e, 'center')}>
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
        <button on:click={askBox} disabled={box.type !== 'local'}>Ask...</button>
        <button on:click={openTerminal} disabled={box.type !== 'local'}>Terminal</button>
        <button on:click={openFiles} disabled={box.type !== 'local'}>Files</button>
        <div class="menu-separator"></div>
        <button on:click={renameBox}>Rename...</button>
        <div class="menu-separator"></div>
        <button on:click={setCoverImage} disabled={!canSetCover}>Set Cover Image...</button>
        <button on:click={clearCoverImage} disabled={!coverPanelLocation}>Clear Cover Image</button>
        <div class="menu-separator"></div>
        <button on:click={deleteBoxConfirm} class="delete">Delete</button>
    </div>
{/if}

<!-- Board Picker UI -->
{#if showBoardPicker}
    <div class="board-picker" style:top="{boardPickerProps.y}px" style:left="{boardPickerProps.x}px" on:click|stopPropagation>
        {#if !coverPanelLocation}
            <button class="picker-item" on:click={setCoverImageFromPicker}>
                Set Cover Image...
            </button>
            <div class="menu-separator"></div>
        {/if}

        <div class="picker-header">Open Windows</div>
        {#each $windows as win (win.id)}
            <button class="picker-item" on:click={() => selectWindow(win)}>
                {getActiveTabTitle(win)}
            </button>
        {:else}
            <div class="empty-message">No open windows</div>
        {/each}

        <div class="picker-header" style="margin-top: 5px;">Saved Dashes</div>
        {#each $dashLayouts as layout (layout.id)}
            <button class="picker-item" on:click={() => selectDash(layout)}>
                {layout.name}
            </button>
        {:else}
            <div class="empty-message">No saved dashes</div>
        {/each}
    </div>
{/if}