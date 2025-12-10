<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows, newIoskConnection, newCalculator, newSettings, newWebBrowser, newLocalTerminal, newLocalFileExplorer, newAskWindow, newNotificationCenter } from './windows.js';
    import { dashActive, unreadNoticeCount, windowView, desktopSettings, wasDraggingItems } from './desktop.js';
    import { createBox, connectionStatus } from './bridge.js';
    import Clock from './Clock.svelte';
    import { get } from 'svelte/store';

    let showMenu = false; // For Start menu
    let startButton;

    let showWindowsMenu = false; // For Windows list menu
    let windowsButton;

    let screenWidth;
    let menuBackgroundStyle = '';

    $: tbSettings = $desktopSettings.sky?.frame;
    $: tbHeight = tbSettings?.height || 40;

    $: if (tbSettings) {
        if (tbSettings.bgType === 'color') {
            menuBackgroundStyle = `background-color: ${tbSettings.bgColor};`;
        } else if (tbSettings.bgType === 'gradient') {
            menuBackgroundStyle = `background-color: ${tbSettings.bgGradientStart};`;
        } else {
            menuBackgroundStyle = `background-color: ${tbSettings.bgColor};`;
        }
    }

    function generateBgStyle(bgSettings) {
        if (!bgSettings) return null;
        if (bgSettings.bgType === 'gradient') {
            return `linear-gradient(45deg, ${bgSettings.bgGradientStart} 0%, ${bgSettings.bgGradientEnd} 100%)`;
        } else if (bgSettings.bgType === 'color') {
            return bgSettings.bgColor;
        } else if (bgSettings.bgType === 'image' && bgSettings.bgImage) {
            let size = 'cover';
            let repeat = 'no-repeat';
            let position = 'center center';

            switch (bgSettings.bgImageDisplayMode) {
                case 'contain': size = 'contain'; break;
                case 'stretch': size = '100% 100%'; break;
                case 'tile': size = 'auto'; repeat = 'repeat'; position = '0 0'; break;
                case 'cover': default: break;
            }
            return `url('${bgSettings.bgImage}') ${position} / ${size} ${repeat}`;
        }
        return null;
    }

    // Elements for layout calculation
    let leftSectionEl, centerSectionEl, rightSectionEl;

    // Map to store measured sizes of task items
    let taskItemSizes = new Map();

    // Object to store final calculated layouts
    let taskItemLayouts = {};

    const GAP = 5; // px gap between items

    // Svelte action to measure an element's size using ResizeObserver
    function measure(node, id) {
        const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
                let newWidth, newHeight;
                if (entry.borderBoxSize && entry.borderBoxSize.length > 0) {
                    newWidth = entry.borderBoxSize[0].inlineSize;
                    newHeight = entry.borderBoxSize[0].blockSize;
                } else {
                    const rect = entry.target.getBoundingClientRect();
                    newWidth = rect.width;
                    newHeight = rect.height;
                }
                const currentSize = taskItemSizes.get(id);
                if (currentSize?.width !== newWidth || currentSize?.height !== newHeight) {
                    taskItemSizes.set(id, { width: newWidth, height: newHeight });
                    taskItemSizes = taskItemSizes;
                }
            }
        });
        ro.observe(node);

        return {
            destroy() {
                ro.disconnect();
                if (taskItemSizes.has(id)) {
                    taskItemSizes.delete(id);
                    taskItemSizes = taskItemSizes;
                }
            }
        };
    }

    function getActiveTabTitle(win) {
        if (!win || !win.tabs) return '...';
        const activeTab = win.tabs.find(t => t.id === win.activeTabId);
        return activeTab ? activeTab.title : (win.tabs[0]?.title || 'Window');
    }

    function getIdealButtonLeft(win, buttonWidth) {
        // Fix #1: Use restored geometry for maximized windows
        const winX = win.maximized && typeof win.prevX === 'number' ? win.prevX : win.x;
        const winWidth = win.maximized && typeof win.prevWidth === 'number' ? win.prevWidth : win.width;

        // Fix #2: Account for sky frame width for correct alignment
        const frameWidth = tbSettings?.width ?? 0;

        // Convert window "world" coordinates to "screen" coordinates, relative to the desktop container
        const screenWinX = winX * $windowView.zoom + $windowView.panX;
        const screenWinWidth = winWidth * $windowView.zoom;

        // The width of the desktop container in screen pixels
        const screenDesktopWidth = screenWidth - (2 * frameWidth);

        // Center of window relative to the desktop container
        const windowCenterInDesktop = screenWinX + screenWinWidth / 2;

        // Progress of the window's center across the desktop container
        const progress = screenDesktopWidth > 0
            ? Math.max(0, Math.min(1, windowCenterInDesktop / screenDesktopWidth))
            : 0.5;

        // The final button position is relative to the full screen. We need to add the left frame's width as an offset.
        const leftAlignedPos = screenWinX + frameWidth;
        const rightAlignedPos = screenWinX + screenWinWidth - buttonWidth + frameWidth;

        let idealLeft = leftAlignedPos * (1 - progress) + rightAlignedPos * progress;

        // Clamp the ideal position to be above the desktop area, respecting side frames.
        // This provides a much better starting point for the collision logic.
        const desktopScreenRight = screenWidth - frameWidth;
        idealLeft = Math.max(frameWidth, Math.min(idealLeft, desktopScreenRight - buttonWidth));

        return idealLeft;
    }

    function getIdealButtonTop(win, buttonHeight) {
        // Fix #1: Use restored geometry for maximized windows
        const winY = win.maximized && typeof win.prevY === 'number' ? win.prevY : win.y;
        const winHeight = win.maximized && typeof win.prevHeight === 'number' ? win.prevHeight : win.height;

        const frameSettings = get(desktopSettings).sky?.frame;
        const th = frameSettings?.height ?? 40;
        const bottomFrameHeight = frameSettings?.width ?? 0;
        const screenWinY = winY * $windowView.zoom + $windowView.panY;
        const screenWinHeight = (winHeight || 0) * $windowView.zoom;
        const screenDesktopHeight = window.innerHeight - th - bottomFrameHeight;

        // This logic treats the button as a minimap of the window's vertical position
        // by mapping the window's movable range to the button's movable range.
        const windowMovableSpace = screenDesktopHeight - screenWinHeight;
        const buttonMovableSpace = th - buttonHeight;

        if (windowMovableSpace <= 0 || buttonMovableSpace <= 0) {
            return 0; // Default to top if no space to move
        }

        // Calculate progress of the window within its movable space
        const progress = Math.max(0, Math.min(1, screenWinY / windowMovableSpace));
        const idealTop = progress * buttonMovableSpace;

        return Math.max(0, Math.min(idealTop, th - buttonHeight));
    }


    $: if (screenWidth && leftSectionEl && centerSectionEl && rightSectionEl && $windows.length > 0 && $windowView) {
        const allSizesKnown = $windows.every(win => taskItemSizes.has(win.id));
        if (allSizesKnown) {
            const leftRect = leftSectionEl.getBoundingClientRect();
            const centerRect = centerSectionEl.getBoundingClientRect();
            const rightRect = rightSectionEl.getBoundingClientRect();

            const items = $windows
                .map(win => {
                    const size = taskItemSizes.get(win.id) || { width: 100, height: 28 };
                    return {
                        id: win.id,
                        width: size.width,
                        height: size.height,
                        idealLeft: getIdealButtonLeft(win, size.width),
                        idealTop: getIdealButtonTop(win, size.height),
                    };
                })
                .sort((a, b) => a.idealLeft - b.idealLeft);

            const newLayouts = {};
            const placedRects = [
                { left: 0, top: 0, right: leftRect.right + GAP, bottom: tbHeight },
                { left: centerRect.left - GAP, top: 0, right: centerRect.right + GAP, bottom: tbHeight },
                { left: rightRect.left - GAP, top: 0, right: screenWidth, bottom: tbHeight }
            ];

            function intersects(r1, r2) {
                return !(r2.left >= r1.right || r2.right <= r1.left || r2.top >= r1.bottom || r2.bottom <= r1.top);
            }

            for (const item of items) {
                let left = item.idealLeft;
                let top = item.idealTop;

                for (let i = 0; i < 50; i++) { // Failsafe iteration limit
                    top = Math.max(0, Math.min(top, tbHeight - item.height)); // Clamp top
                    const currentRect = { left, top, right: left + item.width, bottom: top + item.height };

                    const collisionIndex = placedRects.findIndex(r => intersects(currentRect, r));
                    if (collisionIndex === -1) break; // Found a spot

                    const collision = placedRects[collisionIndex];

                    if (collisionIndex === 2) { // 0: left, 1: center, 2: right
                        left = collision.left - item.width; // Push left of the boundary
                        top = item.idealTop; // Reset vertical position to try again
                    } else if (currentRect.left < collision.right) {
                        const newLeft = collision.right;
                        // Check if pushing right would collide with the right-hand side controls
                        if (newLeft + item.width > placedRects[2].left) {
                            // It would collide. So we must push down instead of right.
                            top = collision.bottom + GAP;
                            left = item.idealLeft; // Reset horizontal position for the new "row"
                        } else {
                            left = newLeft; // Push right from other items/controls
                            top = item.idealTop; // Reset vertical position when pushed horizontally
                        }
                    } else {
                        top = collision.bottom + GAP; // Vertically blocked, move down to stack
                    }
                }

                newLayouts[item.id] = { left, top };
                placedRects.push({ left, top, right: left + item.width, bottom: top + item.height });
            }

            taskItemLayouts = newLayouts;
        }
    } else if ($windows.length === 0) {
        taskItemLayouts = {};
    }

    // --- Window Dragging from Taskbar Logic ---
    let dragInfo = null; // { win, startX, startY, initialWinX, initialWinY, isDragging }
    let middleClickTimeouts = new Map();

    function onTaskItemMouseDown(event, win) {
        if (event.button === 1) { // Middle click
            event.preventDefault();

            // Double-click detection
            if (middleClickTimeouts.has(win.id)) {
                clearTimeout(middleClickTimeouts.get(win.id));
                middleClickTimeouts.delete(win.id);
                windows.toggleCloak(win.id);
                return;
            }

            const timeout = setTimeout(() => {
                middleClickTimeouts.delete(win.id);
            }, 250);
            middleClickTimeouts.set(win.id, timeout);

            // Drag detection: if the mouse moves, cancel the double-click timer and start dragging.
            const onMove = (moveEvent) => {
                const dx = moveEvent.clientX - event.clientX;
                const dy = moveEvent.clientY - event.clientY;

                if (Math.abs(dx) > 3 || Math.abs(dy) > 3) { // Drag threshold
                    clearTimeout(middleClickTimeouts.get(win.id));
                    middleClickTimeouts.delete(win.id);

                    window.removeEventListener('mousemove', onMove);
                    window.removeEventListener('mouseup', onUp);

                    // Start the drag
                    dragInfo = {
                        win,
                        startX: event.clientX,
                        startY: event.clientY,
                        initialWinX: win.x,
                        initialWinY: win.y,
                        isDragging: false
                    };

                    window.addEventListener('mousemove', handleDragMove);
                    window.addEventListener('mouseup', handleDragEnd, { once: true });

                    handleDragMove(moveEvent);
                }
            };

            const onUp = () => {
                window.removeEventListener('mousemove', onMove);
            };

            window.addEventListener('mousemove', onMove);
            // Fix #1: Make onUp listener self-removing for robustness
            window.addEventListener('mouseup', onUp, { once: true });
        }
    }

    function handleDragMove(event) {
        if (!dragInfo) return;

        const dx = event.clientX - dragInfo.startX;
        const dy = event.clientY - dragInfo.startY;

        if (!dragInfo.isDragging && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
            dragInfo.isDragging = true;
            wasDraggingItems.set(true);
            windows.focusWindow(dragInfo.win.id);
            document.body.style.cursor = 'move'; // Change cursor on drag start
        }

        if (dragInfo.isDragging) {
            event.preventDefault(); // Prevent text selection etc. only when dragging
            const view = get(windowView);
            const win = dragInfo.win;

            const frameSettings = get(desktopSettings).sky?.frame;
            const th = frameSettings?.height ?? 40;
            const bottomFrameHeight = frameSettings?.width ?? 0;
            const buttonSize = taskItemSizes.get(win.id) || { width: 100, height: 28 };

            // To make the button track the mouse 1:1, we need to scale the window's vertical movement.
            // This scale factor is the inverse of the scaling used to position the button.
            const screenDesktopHeight = window.innerHeight - th - bottomFrameHeight;
            const buttonMovableSpace = th - buttonSize.height;

            const winHeight = win.maximized && typeof win.prevHeight === 'number' ? win.prevHeight : win.height;
            const screenWinHeight = (winHeight || 0) * view.zoom;
            const windowMovableSpace = screenDesktopHeight - screenWinHeight;

            const scaleY = buttonMovableSpace > 0 && windowMovableSpace > 0
                ? windowMovableSpace / buttonMovableSpace
                : 1;

            const newX = dragInfo.initialWinX + dx / view.zoom;
            const newY = dragInfo.initialWinY + (dy * scaleY) / view.zoom;

            windows.updateWindowProps(win.id, {
                x: newX,
                y: newY,
                maximized: false,
                minimized: false // Ensure window is not minimized when dragged
            });
        }
    }

    function handleDragEnd() {
        if (dragInfo && dragInfo.isDragging) {
            document.body.style.cursor = ''; // Reset cursor
            setTimeout(() => {
                wasDraggingItems.set(false);
            }, 0);
        }

        dragInfo = null;
        window.removeEventListener('mousemove', handleDragMove);
        window.removeEventListener('mouseup', handleDragEnd);
    }

    function handleTaskClick(win) {
        if (win.minimized) windows.toggleMinimize(win.id);
        else if (win.isActive) windows.toggleMinimize(win.id);
        else windows.focusWindow(win.id);
    }

    function handleCloseAllClick() {
        if ($windows.length === 0) return;
        if (confirm("Are you sure you want to close all windows?")) {
            if ($dashActive) dashActive.set(false);
            windows.closeAllWindows();
            showWindowsMenu = false;
        }
    }

    function handleWindowClick(event) {
        if (showMenu && startButton && !startButton.contains(event.target)) showMenu = false;
        if (showWindowsMenu && windowsButton && !windowsButton.contains(event.target)) showWindowsMenu = false;
    }

    function launchIosk(props = {}) { newIoskConnection(props); showMenu = false; }
    function launchCalculator(props = {}) { newCalculator(props); showMenu = false; }
    function launchSettings(props = {}) { newSettings(props); showMenu = false; }
    function launchLocalTerminal(props = {}) { newLocalTerminal(props); showMenu = false; }
    function launchLocalFileExplorer(props = {}) { newLocalFileExplorer(props); showMenu = false; }
    function launchAsk(props = {}) { newAskWindow(props); showMenu = false; }

    function newBox() {
        const name = prompt("Enter a name for the new Box:", "My Project Box");
        if (!name) return;

        // For simplicity, this implementation only handles 'local' type boxes.
        const context = prompt("Enter the local filesystem path for the Box:", "/home/user/project");
        if (!context) return;

        createBox(name, 'local', context);
    }

    function toggleSkyCloak() {
        desktopSettings.update(s => {
            s.sky.cloak.enabled = !s.sky.cloak.enabled;
            return s;
        });
    }

    let middleClickTimeout;
    function handleTaskbarMouseDown(event) {
        if (event.button !== 1 || event.target !== event.currentTarget) return;
        event.preventDefault();

        if (middleClickTimeout) {
            clearTimeout(middleClickTimeout);
            middleClickTimeout = null;
            toggleSkyCloak();
        } else {
            middleClickTimeout = setTimeout(() => {
                middleClickTimeout = null;
            }, 300);
        }
    }

    function handleTaskbarWheel(event) {
        if (event.target !== event.currentTarget) return;
        event.preventDefault();
        toggleSkyCloak();
    }

    onMount(() => {
        window.addEventListener('click', handleWindowClick);
    });
    onDestroy(() => {
        window.removeEventListener('click', handleWindowClick);
        if (middleClickTimeout) clearTimeout(middleClickTimeout);
        middleClickTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
    });
</script>

<style>
    @keyframes notice-glow {
        50% { border-color: var(--notice-color); box-shadow: 0 0 10px 2px var(--notice-color); }
    }
    .task-item.noticing {
        animation: notice-glow 1.2s ease-in-out;
    }
    .taskbar { height: var(--tb-height, 40px); display: flex; align-items: center; justify-content: space-between; padding: 0 10px; flex-shrink: 0; position: relative; }
    .taskbar-left, .taskbar-right { display: flex; align-items: center; gap: 8px; position: relative; z-index: 10; }
    .taskbar-center { position: absolute; left: 50%; transform: translateX(-50%); z-index: 10; }
    .task-item { background-color: var(--taskbar-button-bg); color: var(--taskbar-text); border: 1px solid var(--frame-border-color, var(--border-color)); border-radius: 4px; padding: 2px 5px; cursor: pointer; max-width: 250px; position: absolute; transition: left 0.3s ease-out, top 0.3s ease-out, border-color 0.2s ease-in-out; z-index: 1; display: flex; align-items: center; justify-content: center; }
    .task-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .task-item.minimized { font-style: italic; opacity: 0.7; }
    .task-item.active { border-bottom: 2px solid #27c93f; padding-bottom: 1px; z-index: 2; }
    .taskbar-left > .windows-button:first-child { background-color: #ff5f56; border-color: #e0443e; color: white; }
    .taskbar-left > .windows-button:first-child:hover { background-color: #e0443e; }
    .taskbar-left > .windows-button:nth-child(2) { background-color: #ffbd2e; border-color: #e0a320; color: white; }
    .taskbar-left > .windows-button:nth-child(2):hover { background-color: #e0a320; }
    .taskbar-left > .windows-button:nth-child(2).active {
        background-color: #27ae60; /* A different green to indicate active state */
        border-color: #229954;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.25);
    }
    .start-button { background-color: #3498db; border: 1px solid #2980b9; color: white; transition: box-shadow 0.3s ease-in-out; padding: 4px; }
    .start-button:hover { background-color: #2980b9; }
    .start-button img { height: 100%; display: block; object-fit: contain; }
    @keyframes sky-glow {
        50% { border-color: #5dade2; box-shadow: 0 0 12px 3px #5dade2; }
    }
    .start-button.connected {
        animation: sky-glow 2s infinite ease-in-out;
    }
    .quick-launch-button { background-color: #27c93f; border: 1px solid #1a9c2a; color: white; }
    .quick-launch-button:hover { background-color: #1a9c2a; }

    /* Scalable main buttons */
    .windows-button, .quick-launch-button, .start-button {
        font-weight: bold;
        cursor: pointer;
        height: calc(var(--tb-height, 40px) * 0.7);
        width: calc(var(--tb-height, 40px) * 0.7);
        box-sizing: border-box;
        font-size: calc(var(--tb-height, 40px) * 0.35);
        border-radius: calc(var(--tb-height, 40px) * 0.1);
        border: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .windows-button { background-color: var(--taskbar-button-bg); color: var(--taskbar-text); }
    .windows-button:hover { background-color: var(--taskbar-button-hover-bg); }
    .windows-button.active { background-color: var(--taskbar-button-hover-bg); }

    .start-menu, .windows-menu { position: absolute; top: calc(var(--tb-height, 40px) + 5px); background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 21500; }
    .start-menu {
        top: calc(var(--tb-height, 40px) * 0.85);
        right: 0;
        display: grid;
        grid-template-columns: repeat(4, 52px);
        grid-template-rows: repeat(2, 52px);
        gap: 8px;
        padding: 8px;
        width: auto;
    }
    .windows-menu {
        top: calc(var(--tb-height, 40px) * 0.85);
        left: 0;
        max-height: 300px;
        overflow-y: auto; display: flex; flex-direction: column; width: 200px;
    }
    .menu-item-row {
        display: flex;
        align-items: stretch;
        border-bottom: 1px solid var(--border-color);
    }
    .menu-item-row:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .menu-item-close {
        background-color: #ff5f56;
        border: none;
        color: white;
        cursor: pointer;
        padding: 0 12px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .menu-item-close:hover {
        background-color: #e0443e;
    }
    .menu-item-row .menu-item {
        border-bottom: none;
        flex-grow: 1;
    }
    .menu-item-row:hover .menu-item {
        background-color: transparent;
    }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 10px 15px; text-align: left; cursor: pointer; border-bottom: 1px solid var(--border-color); }
    .menu-item:last-child { border-bottom: none; }
    .menu-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; }
    .start-menu .menu-item {
        position: relative;
        padding: 0;
        text-align: center;
        border-bottom: none;
        border-radius: 6px;
        font-size: 26px;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .start-menu .menu-item:last-child {
        border-bottom: none;
    }
    .start-menu .menu-item:disabled {
        opacity: 0.5;
    }
    .start-menu .menu-item:disabled:hover {
        background-color: transparent;
    }
    .skybridge-overlay {
        position: absolute;
        top: calc(8px + 52px + 8px); /* Corresponds to start-menu padding + 1 row + 1 gap */
        left: 8px; /* Corresponds to start-menu padding */
        width: calc(4 * 52px + 3 * 8px); /* 4 columns + 3 gaps */
        height: 52px; /* 1 row */
        background-color: rgba(30, 30, 30, 0.33);
        backdrop-filter: blur(1px);
        color: white;
        font-weight: bold;
        font-size: 13px;
        letter-spacing: 0.5px;
        border-radius: 6px;
        z-index: 5;
        pointer-events: none; /* Let clicks pass through to disabled buttons */
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .menu-badge {
        position: absolute;
        top: 4px;
        right: 4px;
        width: 16px;
        height: 16px;
    }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .menu-item-empty { padding: 10px 15px; color: #7f8c8d; font-style: italic; }
    .close-all-row {
        cursor: pointer;
        border-top: 1px solid var(--border-color);
        border-bottom: none;
    }
    .close-all-row .menu-item {
        color: #e74c3c;
        font-weight: bold;
    }
    .close-all-row:hover {
        background-color: #c0392b;
        color: white;
    }
    /* When hovering the entire "Close All" row, highlight the 'x' button too */
    .close-all-row:hover .menu-item-close {
        background-color: #e0443e;
    }
    .start-button, .windows-list-button { position: relative; }
    .start-button::after, .windows-list-button::after { content: ''; position: absolute; bottom: 0px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 4px solid rgba(255, 255, 255, 0.7); }
    .start-button::after { right: 5px; }
    .windows-list-button::after { left: 5px; }

    /* Scalable clock */
    .clock-button { background: none; border: none; color: inherit; padding: 0; cursor: pointer; position: relative; border-radius: 4px; display: flex; align-items: center; justify-content: center; width: calc(var(--tb-height, 40px) - 6px); height: calc(var(--tb-height, 40px) - 6px); }
    .clock-button:hover { background-color: var(--taskbar-button-hover-bg); }

    .notice-badge { position: absolute; top: 0px; right: 0px; background-color: #e74c3c; color: white; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; font-weight: bold; display: flex; align-items: center; justify-content: center; line-height: 1; border: 1px solid var(--taskbar-bg); }

    /* New styles for tab representation */
    .task-item-layout { display: flex; align-items: center; gap: 4px; overflow: hidden; width: 100%; justify-content: center; }
    .active-tab-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 1; }
    .inactive-tabs-group { display: flex; gap: 3px; flex-shrink: 1; overflow: hidden; }
    .inactive-tab { display: inline-block; font-size: 0.65em; line-height: 1.1; max-width: 60px; padding: 2px 3px; background-color: rgba(0,0,0,0.2); border-radius: 3px; white-space: normal; word-break: break-word; text-align: center; opacity: 0.8; }
</style>

<svelte:window bind:innerWidth={screenWidth} />

<div class="taskbar" on:mousedown={handleTaskbarMouseDown} on:wheel={handleTaskbarWheel} style="--tb-height: {tbHeight}px">
    <div class="taskbar-left" bind:this={leftSectionEl}>
        <button class="windows-button windows-list-button" bind:this={windowsButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showWindowsMenu = !showWindowsMenu; }}>✕</button>
        <button class="windows-button" class:active={$dashActive} on:click={() => dashActive.update(v => !v)} title="Dash">&mdash;</button>
        {#if showWindowsMenu}
            <div class="windows-menu" style={menuBackgroundStyle}>
                {#each $windows.sort((a, b) => a.id - b.id) as win (win.id)}
                    <div class="menu-item-row">
                        <button class="menu-item-close" on:click={() => windows.removeWindow(win.id)} title="Close window">✕</button>
                        <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); windows.focusWindow(win.id); showWindowsMenu = false; }}>
                            {getActiveTabTitle(win)}
                        </button>
                    </div>
                {:else}
                    <span class="menu-item-empty">No open windows</span>
                {/each}
                {#if $windows.length > 0}
                    <div class="menu-item-row close-all-row" on:click={handleCloseAllClick}>
                        <button type="button" class="menu-item-close">✕</button>
                        <button type="button" class="menu-item">Close All</button>
                    </div>
                {/if}
            </div>
        {/if}
    </div>

    {#each $windows as win (win.id)}
        {@const activeTab = win.tabs.find(t => t.id === win.activeTabId) || win.tabs[0]}
        {@const activeIndex = win.tabs.indexOf(activeTab)}
        {@const beforeTabs = win.tabs.slice(0, activeIndex)}
        {@const afterTabs = win.tabs.slice(activeIndex + 1)}
        {@const state = win.isActive ? 'active' : 'inactive'}
        {@const frameSettings = $desktopSettings?.windows?.normal?.frame?.[state]}
        {@const frameStyle = frameSettings ? generateBgStyle(frameSettings) : null}
        {@const borderColor = !win.cloaked && frameSettings?.shadowEnabled ? frameSettings.shadowColor : null}
        <button
            class="task-item"
            class:minimized={win.minimized}
            class:active={win.isActive}
            class:noticing={!!win.notice}
            title={activeTab?.title}
            on:mousedown={(e) => onTaskItemMouseDown(e, win)}
            on:click={() => {
                if (get(wasDraggingItems)) return;
                if ($dashActive) dashActive.set(false); handleTaskClick(win);
            }}
            on:dblclick={() => windows.toggleMaximize(win.id)}
            use:measure={win.id}
            style="left: {taskItemLayouts[win.id] ? taskItemLayouts[win.id].left + 'px' : '-9999px'}; top: {taskItemLayouts[win.id] ? taskItemLayouts[win.id].top + 'px' : '-9999px'}; --notice-color: {win.notice?.color}; background: {frameStyle}; {borderColor ? `--frame-border-color: ${borderColor};` : ''}"
        >
            {#if win.tabs.length > 1}
                <div class="task-item-layout">
                    <div class="inactive-tabs-group">
                        {#each beforeTabs as tab (tab.id)}
                            <span class="inactive-tab" title={tab.title}>{tab.title}</span>
                        {/each}
                    </div>

                    <span class="active-tab-title">{activeTab?.title}</span>

                    <div class="inactive-tabs-group">
                        {#each afterTabs as tab (tab.id)}
                            <span class="inactive-tab" title={tab.title}>{tab.title}</span>
                        {/each}
                    </div>
                </div>
            {:else}
                {activeTab?.title}
            {/if}
        </button>
    {/each}

    <div class="taskbar-center" bind:this={centerSectionEl}>
        <button class="clock-button" on:click={(e) => { if ($dashActive) dashActive.set(false); newNotificationCenter({ sourceEvent: e }); }}>
            <Clock />
            {#if $unreadNoticeCount > 0}
                <span class="notice-badge">{$unreadNoticeCount}</span>
            {/if}
        </button>
    </div>
    <div class="taskbar-right" bind:this={rightSectionEl}>
        <button class="quick-launch-button" on:click|stopPropagation={(e) => { if ($dashActive) dashActive.set(false); launchIosk({ sourceEvent: e }); }} title="IOSK Connection">&#9632;</button>
        <button class="start-button" class:connected={$connectionStatus === 'connected'} bind:this={startButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showMenu = !showMenu; }} title="SKYBOARD Menu"><img src="/favicon.png" alt="SKYBOARDS"></button>
        {#if showMenu}
            <div class="start-menu" style={menuBackgroundStyle}>
                {#if $connectionStatus !== 'connected'}
                    <div class="skybridge-overlay">SKYBRIDGE REQUIRED</div>
                {/if}
                <!-- Top Row -->
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchSettings({ sourceEvent: e }); }} title="Settings">⚙️</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchCalculator({ sourceEvent: e }); }} title="Calculator">🧮</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); newWebBrowser({ sourceEvent: e }); showMenu = false; }} title="Web Browser">🌐</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchIosk({ sourceEvent: e }); }} title="IOSK Connection">
                    🖥️
                    <img class="menu-badge" src="/iosk.png" alt="IOSK" />
                </button>

                <!-- Bottom Row -->
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchAsk({ sourceEvent: e }); }} disabled={$connectionStatus !== 'connected'} title="Ask">?</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); newBox(); showMenu = false; }} disabled={$connectionStatus !== 'connected'} title="New Box">📦</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchLocalFileExplorer({ sourceEvent: e }); }} disabled={$connectionStatus !== 'connected'} title="Files">📁</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchLocalTerminal({ sourceEvent: e }); }} disabled={$connectionStatus !== 'connected'} title="Terminal">&gt;_</button>
            </div>
        {/if}
    </div>
</div>
