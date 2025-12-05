<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows, newIoskConnection, newCalculator, newSettings, newWebBrowser, newLocalTerminal, newLocalFileExplorer, newAskWindow, newNotificationCenter } from './windows.js';
    import { dashActive, unreadNoticeCount, windowView, desktopSettings, wasDraggingItems } from './desktop.js';
    import { createBox, connectionStatus } from './local.js';
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
        // Convert window "world" coordinates to "screen" coordinates using windowView
        const screenWinX = win.x * $windowView.zoom + $windowView.panX;
        const screenWinWidth = win.width * $windowView.zoom;

        const windowCenter = screenWinX + screenWinWidth / 2;
        const progress = Math.max(0, Math.min(1, windowCenter / screenWidth));

        const leftAlignedPos = screenWinX;
        const rightAlignedPos = screenWinX + screenWinWidth - buttonWidth;

        let idealLeft = leftAlignedPos * (1 - progress) + rightAlignedPos * progress;
        idealLeft = Math.max(0, Math.min(idealLeft, screenWidth - buttonWidth));
        return idealLeft;
    }

    function getIdealButtonTop(win, buttonHeight) {
        const frameSettings = get(desktopSettings).sky?.frame;
        const th = frameSettings?.height ?? 40;
        const bottomFrameHeight = frameSettings?.width ?? 0;
        const screenWinY = win.y * $windowView.zoom + $windowView.panY;
        const screenDesktopHeight = window.innerHeight - th - bottomFrameHeight;
        
        const progress = Math.max(0, Math.min(1, screenWinY / screenDesktopHeight));
        const availableSpace = th - buttonHeight;
        const idealTop = progress * availableSpace;
        
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
                    const collision = placedRects.find(r => intersects(currentRect, r));
                    
                    if (!collision) break; // Found a spot

                    if (currentRect.left < collision.right) {
                        left = collision.right; // Note: GAP is baked into fixed rects
                        top = item.idealTop; // Reset vertical position when pushed horizontally
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
                    window.addEventListener('mouseup', handleDragEnd);
                    
                    handleDragMove(moveEvent);
                }
            };

            const onUp = () => {
                window.removeEventListener('mousemove', onMove);
                window.removeEventListener('mouseup', onUp);
            };
            
            window.addEventListener('mousemove', onMove);
            window.addEventListener('mouseup', onUp);
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
            const newX = dragInfo.initialWinX + dx / view.zoom;
            const newY = dragInfo.initialWinY + dy / view.zoom;

            windows.update(wins => wins.map(w => {
                if (w.id === dragInfo.win.id) {
                    return {
                        ...w,
                        x: newX,
                        y: newY,
                        maximized: false
                    };
                }
                return w;
            }));
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
            if (s.sky.cloak.opacity > 0) {
                s.sky.cloak.lastOpacity = s.sky.cloak.opacity;
                s.sky.cloak.opacity = 0;
            } else {
                s.sky.cloak.opacity = s.sky.cloak.lastOpacity || 0.8;
            }
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
    .task-item { background-color: var(--taskbar-button-bg); color: var(--taskbar-text); border: 1px solid var(--border-color); border-radius: 4px; padding: 2px 5px; cursor: pointer; max-width: 250px; position: absolute; transition: left 0.3s ease-out, top 0.3s ease-out, border-color 0.2s ease-in-out; z-index: 1; display: flex; align-items: center; justify-content: center; }
    .task-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .task-item.minimized { font-style: italic; opacity: 0.7; }
    .task-item.active { border-bottom: 2px solid #27c93f; padding-bottom: 1px; z-index: 2; }
    .taskbar-left > .windows-button:first-child { background-color: #ff5f56; border-color: #e0443e; color: white; }
    .taskbar-left > .windows-button:first-child:hover { background-color: #e0443e; }
    .taskbar-left > .windows-button:nth-child(2) { background-color: #ffbd2e; border-color: #e0a320; color: white; }
    .taskbar-left > .windows-button:nth-child(2):hover { background-color: #e0a320; }
    .start-button { background-color: #3498db; border: 1px solid #2980b9; color: white; transition: box-shadow 0.3s ease-in-out; }
    .start-button:hover { background-color: #2980b9; }
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
        padding: 0 calc(var(--tb-height, 40px) * 0.25);
        font-size: calc(var(--tb-height, 40px) * 0.35);
        border-radius: calc(var(--tb-height, 40px) * 0.1);
        border: 1px solid var(--border-color);
    }
    .windows-button { background-color: var(--taskbar-button-bg); color: var(--taskbar-text); }
    .windows-button:hover { background-color: var(--taskbar-button-hover-bg); }
    .windows-button.active { background-color: var(--taskbar-button-hover-bg); }

    .start-menu, .windows-menu { position: absolute; top: calc(var(--tb-height, 40px) + 5px); background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 10000; display: flex; flex-direction: column; width: 200px; }
    .start-menu { right: 10px; }
    .windows-menu { left: 10px; max-height: 300px; overflow-y: auto; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 10px 15px; text-align: left; cursor: pointer; border-bottom: 1px solid var(--border-color); }
    .menu-item:last-child { border-bottom: none; }
    .menu-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .menu-item-empty { padding: 10px 15px; color: #7f8c8d; font-style: italic; }
    .menu-item.close-all { color: #e74c3c; border-top: 1px solid var(--border-color); border-bottom: none; }
    .menu-item.close-all:hover { background-color: #c0392b; color: white; }
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

<div class="taskbar" on:mousedown={handleTaskbarMouseDown} style="--tb-height: {tbHeight}px">
    <div class="taskbar-left" bind:this={leftSectionEl}>
        <button class="windows-button" class:active={$dashActive} on:click={() => dashActive.update(v => !v)} title="Dash">&mdash;</button>
        <button class="windows-button windows-list-button" bind:this={windowsButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showWindowsMenu = !showWindowsMenu; }}>W~</button>
        {#if showWindowsMenu}
            <div class="windows-menu" style={menuBackgroundStyle}>
                {#each $windows.sort((a, b) => a.id - b.id) as win (win.id)}
                    <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); windows.focusWindow(win.id); showWindowsMenu = false; }}>
                        {getActiveTabTitle(win)}
                    </button>
                {:else}
                    <span class="menu-item-empty">No open windows</span>
                {/each}
                {#if $windows.length > 0}<button class="menu-item close-all" on:click={handleCloseAllClick}>Close All</button>{/if}
            </div>
        {/if}
    </div>

    {#each $windows as win (win.id)}
        {@const activeTab = win.tabs.find(t => t.id === win.activeTabId) || win.tabs[0]}
        {@const activeIndex = win.tabs.indexOf(activeTab)}
        {@const beforeTabs = win.tabs.slice(0, activeIndex)}
        {@const afterTabs = win.tabs.slice(activeIndex + 1)}
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
            style="left: {taskItemLayouts[win.id] ? taskItemLayouts[win.id].left + 'px' : '-9999px'}; top: {taskItemLayouts[win.id] ? taskItemLayouts[win.id].top + 'px' : '-9999px'}; --notice-color: {win.notice?.color};"
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
        <button class="quick-launch-button" on:click|stopPropagation={(e) => { if ($dashActive) dashActive.set(false); launchIosk({ sourceEvent: e }); }} title="IOSK Connection">$+</button>
        <button class="start-button" class:connected={$connectionStatus === 'connected'} bind:this={startButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showMenu = !showMenu; }}>SKY</button>
        {#if showMenu}
            <div class="start-menu" style={menuBackgroundStyle}>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchSettings({ sourceEvent: e }); }}>Settings</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchIosk({ sourceEvent: e }); }}>IOSK Connection</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); newWebBrowser({ sourceEvent: e }); showMenu = false; }}>Web Browser</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); newBox(); showMenu = false; }} disabled={$connectionStatus !== 'connected'}>New Box...</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchAsk({ sourceEvent: e }); }} disabled={$connectionStatus !== 'connected'}>Ask</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchLocalTerminal({ sourceEvent: e }); }} disabled={$connectionStatus !== 'connected'}>Terminal</button>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchLocalFileExplorer({ sourceEvent: e }); }} disabled={$connectionStatus !== 'connected'}>Files</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={(e) => { if ($dashActive) dashActive.set(false); launchCalculator({ sourceEvent: e }); }}>Calculator</button>
            </div>
        {/if}
    </div>
</div>