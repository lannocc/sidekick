<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher, tick, onMount, onDestroy } from 'svelte';
    import { windows } from './windows.js';
    import { desktopSettings } from './desktopStore.js';
    import IoskConsole from './IoskConsole.svelte'; // Import for component type checking

    export let id;
    export let component;
    export let title;
    export let x;
    export let y;
    export let width;
    export let height;
    export let zIndex;
    export let minimized;
    export let maximized;
    export let isActive;
    export let lastFocusedElement; // Received from the store via Desktop.svelte
    export let isConsoleConnected; // For IoskConsole, passed from the store

    const dispatch = createEventDispatcher();

    let settings;
    desktopSettings.subscribe(value => settings = value);

    let isDragging = false;
    let isResizing = false;
    let dragOffsetX, dragOffsetY;

    let resizeDirection = '';
    let initialResizeState = {};
    let focusTimeout = null;

    let showOptionsMenu = false;
    let optionsButton; // ref for the hamburger button
    let componentInstance; // ref for the svelte:component instance

    let contentAreaEl;

    function handleWindowClick(event) {
        // If menu is open and click is outside the menu button and the menu itself, close it
        if (showOptionsMenu && optionsButton && !optionsButton.contains(event.target) && !event.target.closest('.options-menu')) {
            showOptionsMenu = false;
        }
    }

    onMount(() => {
        // Use a single listener for all window instances
        window.addEventListener('click', handleWindowClick);
    });

    onDestroy(() => {
        window.removeEventListener('click', handleWindowClick);
    });

    function handleConnect() {
        if (componentInstance && typeof componentInstance.connect === 'function') {
            componentInstance.connect();
        }
        showOptionsMenu = false;
    }

    function handleDisconnect() {
        if (componentInstance && typeof componentInstance.disconnect === 'function') {
            componentInstance.disconnect();
        }
        showOptionsMenu = false;
    }

    async function restoreFocus() {
        // Check if the element to focus is still valid and in the DOM
        if (lastFocusedElement && document.body.contains(lastFocusedElement)) {
            await tick(); // Wait for any potential re-renders to complete
            lastFocusedElement.focus({ preventScroll: true });
        }
    }

    function handleFocusOut(event) {
        // When focus leaves the content area, save the last focused element.
        // `relatedTarget` is where focus is going. If it's outside our content
        // area, we save the element that just lost focus (`event.target`).
        if (contentAreaEl && !contentAreaEl.contains(event.relatedTarget)) {
            if (contentAreaEl.contains(event.target)) {
                windows.updateWindowProps(id, { lastFocusedElement: event.target });
            }
        }
    }

    // When the window becomes active, restore focus to its last known element.
    $: if (isActive) {
        // Use a microtask to ensure any DOM changes from the activation have completed.
        Promise.resolve().then(restoreFocus);
    }


    function getResizeDirection(event) {
        const relativeX = event.clientX - x;
        const relativeY = event.clientY - y;

        // Define a third of the window as the edge area for resize detection
        const borderThird = 1 / 3;

        const onTop = relativeY < height * borderThird;
        const onBottom = relativeY > height * (1 - borderThird);
        const onLeft = relativeX < width * borderThird;
        const onRight = relativeX > width * (1 - borderThird);

        let vertical = '';
        if (onTop) vertical = 'n';
        else if (onBottom) vertical = 's';

        let horizontal = '';
        if (onLeft) horizontal = 'w';
        else if (onRight) horizontal = 'e';

        return vertical + horizontal;
    }


    function onDragStart(event) {
        if (event.target.classList.contains('window-control') || maximized) return;
        isDragging = true;
        dragOffsetX = event.clientX - x;
        dragOffsetY = event.clientY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd);

        if (event.altKey || event.metaKey) {
            windows.setActiveWindow(id);
        } else {
            windows.focusWindow(id);
        }
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
        restoreFocus(); // Restore focus after move is complete
    }

    function onResizeStart(event) {
        if (maximized) return;

        let direction;
        // The dedicated resize handle always resizes from the south-east
        if (event.target.classList.contains('resize-handle')) {
            direction = 'se';
        } else {
            direction = getResizeDirection(event);
        }

        // Do not start resize if click is in the central area of the window
        if (!direction) return;

        isResizing = true;
        resizeDirection = direction;

        initialResizeState = {
            x, y, width, height,
            mouseX: event.clientX,
            mouseY: event.clientY,
        };

        window.addEventListener('mousemove', onResize);
        window.addEventListener('mouseup', onResizeEnd);

        if (event.altKey || event.metaKey) {
            windows.setActiveWindow(id);
        } else {
            windows.focusWindow(id);
        }
    }

    function onResize(event) {
        if (!isResizing) return;

        const { x: ix, y: iy, width: iw, height: ih, mouseX: startX, mouseY: startY } = initialResizeState;
        const dx = event.clientX - startX;
        const dy = event.clientY - startY;

        // Minimum dimensions are set in CSS, we enforce them here to prevent inversion
        const minWidth = 250;
        const minHeight = 150;

        let newX = ix;
        let newY = iy;
        let newWidth = iw;
        let newHeight = ih;

        if (resizeDirection.includes('e')) {
            newWidth = iw + dx;
        }
        if (resizeDirection.includes('w')) {
            newWidth = iw - dx;
            newX = ix + dx;
        }
        if (resizeDirection.includes('s')) {
            newHeight = ih + dy;
        }
        if (resizeDirection.includes('n')) {
            newHeight = ih - dy;
            newY = iy + dy;
        }

        // Clamp to minimum size and adjust position accordingly
        if (newWidth < minWidth) {
            if (resizeDirection.includes('w')) {
                newX = ix + (iw - minWidth);
            }
            newWidth = minWidth;
        }
        if (newHeight < minHeight) {
            if (resizeDirection.includes('n')) {
                newY = iy + (ih - minHeight);
            }
            newHeight = minHeight;
        }

        x = newX;
        y = newY;
        width = newWidth;
        height = newHeight;

        windows.updateWindowProps(id, { x, y, width, height });
    }

    function onResizeEnd() {
        isResizing = false;
        resizeDirection = '';
        initialResizeState = {};
        window.removeEventListener('mousemove', onResize);
        window.removeEventListener('mouseup', onResizeEnd);
        restoreFocus(); // Restore focus after resize is complete
    }

    function handleFrameMouseDown(event) {
        clearTimeout(focusTimeout);

        // Check for Alt/Meta key for special actions, but not on maximized windows
        if ((event.altKey || event.metaKey) && !maximized) {
            if (event.button === 0) { // Left-click for drag
                onDragStart(event);
            } else if (event.button === 2) { // Right-click for resize
                onResizeStart(event);
            }
        } else {
            // A regular click on the frame should focus and raise the window.
            windows.focusWindow(id);
        }
    }

    function handleMouseEnter() {
        if (settings?.focusFollowsMouse && !isActive) {
            focusTimeout = setTimeout(() => {
                windows.setActiveWindow(id);
            }, settings.focusDelay);
        }
    }

    function handleMouseLeave() {
        clearTimeout(focusTimeout);
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
        transition: border-color 0.2s ease-in-out;
    }
    .window-frame:not(.active) {
        border-color: #7f8c8d;
    }
    .window-frame.minimized {
        display: none;
    }
    .window-frame.maximized {
        border-radius: 0;
        /* !important is used to override inline styles */
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
    }
    .window-frame.maximized .resize-handle {
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
        transition: background-color 0.2s ease-in-out;
    }
    .window-frame:not(.active) .title-bar {
        background-color: #7f8c8d; /* Muted color for inactive windows */
    }
    .title-text {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-align: center;
    }
    .window-controls {
        display: flex;
        gap: 5px;
    }
    .window-control {
        width: 14px;
        height: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        color: rgba(0,0,0,0.6);
        font-weight: bold;
        border-radius: 50%;
        cursor: pointer;
        border: 1px solid rgba(0,0,0,0.2);
    }
    .close { background-color: #ff5f56; }
    .minimize { background-color: #ffbd2e; }
    .maximize { background-color: #27c93f; }
    .options-menu-button {
        background-color: #3498db;
        color: white;
    }
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
    .options-menu {
        position: absolute;
        top: 35px;
        left: 50px; /* Positioned under the third button */
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 1000; /* Above window content */
        display: flex;
        flex-direction: column;
        min-width: 150px;
        padding: 4px 0;
        user-select: none;
    }
    .menu-item {
        background: none;
        border: none;
        color: var(--taskbar-text);
        padding: 8px 12px;
        text-align: left;
        cursor: pointer;
        font-size: 14px;
    }
    .menu-item:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .menu-item:disabled {
        color: #7f8c8d;
        cursor: not-allowed;
    }
    .menu-item.close-option {
        color: #e74c3c;
    }
    .menu-item.close-option:hover:not(:disabled) {
        background-color: #c0392b;
        color: white;
    }
    .menu-separator {
        height: 1px;
        background-color: var(--border-color);
        margin: 4px 0;
    }
    .options-menu-button {
        line-height: 0.8; /* Center the hamburger symbol better */
    }
</style>

<div
    class="window-frame"
    class:minimized
    class:maximized
    class:active={isActive}
    style:left="{x}px"
    style:top="{y}px"
    style:width="{maximized ? null : width + 'px'}"
    style:height="{maximized ? null : height + 'px'}"
    style:z-index="{zIndex}"
    on:mousedown={handleFrameMouseDown}
    on:contextmenu={e => (e.altKey || e.metaKey) && e.preventDefault()}
    on:mouseenter={handleMouseEnter}
    on:mouseleave={handleMouseLeave}
>
    <div class="title-bar" on:mousedown|stopPropagation={onDragStart} on:dblclick={() => windows.toggleMaximize(id)}>
        <div class="window-controls">
            <div class="window-control close" title="Close" on:click={() => windows.removeWindow(id)} on:mousedown|stopPropagation></div>
            <div class="window-control minimize" title="Minimize" on:click={() => windows.toggleMinimize(id)} on:mousedown|stopPropagation></div>
            <div
                class="window-control options-menu-button"
                title="Options"
                bind:this={optionsButton}
                on:click|stopPropagation={() => showOptionsMenu = !showOptionsMenu}>
                ≡
            </div>
        </div>
        <span class="title-text">{title}</span>
        <div class="window-controls">
            <div
                class="window-control maximize"
                title={maximized ? 'Restore' : 'Maximize'}
                on:click={() => windows.toggleMaximize(id)}
                on:mousedown|stopPropagation>
            </div>
        </div>
    </div>
    {#if showOptionsMenu}
        <div class="options-menu">
            {#if component === IoskConsole}
                <button class="menu-item" on:click={handleConnect} disabled={isConsoleConnected}>
                    Connect
                </button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={handleDisconnect} disabled={!isConsoleConnected}>
                    Disconnect
                </button>
                <button class="menu-item close-option" on:click={() => { showOptionsMenu = false; windows.removeWindow(id); }}>
                    Close
                </button>
            {:else}
                <button class="menu-item close-option" on:click={() => { showOptionsMenu = false; windows.removeWindow(id); }}>Close</button>
            {/if}
        </div>
    {/if}
    <div class="content-area" bind:this={contentAreaEl} on:focusout={handleFocusOut} >
        <svelte:component bind:this={componentInstance} this={component} {id} bind:title={title} {isActive} {...$$restProps} />
    </div>
    <div class="resize-handle" on:mousedown|stopPropagation={onResizeStart}></div>
</div>
