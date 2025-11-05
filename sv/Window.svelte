<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher } from 'svelte';
    import { windows } from './windows.js';
    import { desktopSettings } from './desktopStore.js';

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

    const dispatch = createEventDispatcher();

    let settings;
    desktopSettings.subscribe(value => settings = value);

    let isDragging = false;
    let isResizing = false;
    let dragOffsetX, dragOffsetY;

    let resizeDirection = '';
    let initialResizeState = {};
    let focusTimeout = null;


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
    <div class="content-area">
        <svelte:component this={component} {id} bind:title={title} />
    </div>
    <div class="resize-handle" on:mousedown|stopPropagation={onResizeStart}></div>
</div>

