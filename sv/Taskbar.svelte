<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows, newIoskConnection, newCalculator, newSettings, newWebBrowser } from './windows.js';
    import { dashActive } from './desktopStore.js';
    import Clock from './Clock.svelte';

    let showMenu = false; // For Start menu
    let startButton;

    let showWindowsMenu = false; // For Windows list menu
    let windowsButton;

    let screenWidth;

    // Elements for layout calculation
    let leftSectionEl, centerSectionEl, rightSectionEl;

    // Map to store measured widths of task items
    let taskItemWidths = new Map();

    // Object to store final calculated layouts
    let taskItemLayouts = {};

    const GAP = 5; // px gap between items

    // Svelte action to measure an element's width using ResizeObserver
    function measure(node, id) {
        const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
                let newWidth;
                // Use borderBoxSize for a more accurate width (includes padding and border).
                // It's an array, so we take the first entry.
                if (entry.borderBoxSize && entry.borderBoxSize.length > 0) {
                    newWidth = entry.borderBoxSize[0].inlineSize;
                } else {
                    // Fallback for older browsers that don't support borderBoxSize.
                    // getBoundingClientRect() includes padding and border.
                    newWidth = entry.target.getBoundingClientRect().width;
                }

                // Update map only if the width has actually changed to avoid infinite loops
                if (taskItemWidths.get(id) !== newWidth) {
                    taskItemWidths.set(id, newWidth);
                    taskItemWidths = taskItemWidths; // Trigger reactivity
                }
            }
        });
        ro.observe(node);

        return {
            destroy() {
                ro.disconnect();
                if (taskItemWidths.has(id)) {
                    taskItemWidths.delete(id);
                    taskItemWidths = taskItemWidths; // Trigger reactivity
                }
            }
        };
    }

    $: allTabs = $windows.flatMap(group =>
        group.tabs.map(tab => ({
            ...tab,
            groupId: group.id,
            groupX: group.x,
            groupY: group.y,
            groupWidth: group.width,
            groupHeight: group.height,
            isGroupActive: group.isActive,
            isGroupMinimized: group.minimized,
            isGroupMaximized: group.maximized
        }))
    );

    function getIdealButtonLeft(tab, buttonWidth) {
        if (tab.isGroupMaximized) {
            return screenWidth / 2 - buttonWidth / 2;
        }
        const windowCenter = tab.groupX + tab.groupWidth / 2;
        const progress = Math.max(0, Math.min(1, windowCenter / screenWidth));
        const leftAlignedPos = tab.groupX;
        const rightAlignedPos = tab.groupX + tab.groupWidth - buttonWidth;
        let idealLeft = leftAlignedPos * (1 - progress) + rightAlignedPos * progress;
        idealLeft = Math.max(0, Math.min(idealLeft, screenWidth - buttonWidth));
        return idealLeft;
    }

    $: if (screenWidth && leftSectionEl && centerSectionEl && rightSectionEl && allTabs.length > 0) {
        const allWidthsKnown = allTabs.every(tab => taskItemWidths.has(tab.id));
        if (allWidthsKnown) {
            const leftRect = leftSectionEl.getBoundingClientRect();
            const centerRect = centerSectionEl.getBoundingClientRect();
            const rightRect = rightSectionEl.getBoundingClientRect();
            const items = allTabs
                .map(tab => {
                    const buttonWidth = taskItemWidths.get(tab.id) || 100;
                    return { id: tab.id, idealLeft: getIdealButtonLeft(tab, buttonWidth), width: buttonWidth };
                })
                .sort((a, b) => a.idealLeft - b.idealLeft);
            const newLayouts = {};
            let lastItemRightEdge = leftRect.right + GAP;
            for (const item of items) {
                let left = Math.max(item.idealLeft, lastItemRightEdge);
                if ((left + item.width + GAP) > centerRect.left && left < (centerRect.right + GAP)) {
                    left = Math.max(lastItemRightEdge, centerRect.right + GAP);
                }
                newLayouts[item.id] = { left };
                lastItemRightEdge = left + item.width + GAP;
            }
            if (lastItemRightEdge - (rightRect.left - GAP) > 0) {
                let requiredRightEdge = rightRect.left - GAP;
                for (let i = items.length - 1; i >= 0; i--) {
                    const item = items[i];
                    const finalLeft = Math.min(newLayouts[item.id].left, requiredRightEdge - item.width);
                    newLayouts[item.id].left = finalLeft;
                    requiredRightEdge = finalLeft - GAP;
                }
            }
            taskItemLayouts = newLayouts;
        }
    } else if (allTabs.length === 0) {
        taskItemLayouts = {};
    }

    function handleTaskClick(tab) {
        if (tab.isGroupMinimized) {
            windows.toggleMinimize(tab.groupId);
        } else if (tab.isGroupActive) {
            windows.toggleMinimize(tab.groupId);
        } else {
            windows.focusGroup(tab.groupId);
        }
        windows.setActiveTab(tab.groupId, tab.id);
    }

    function handleCloseAllClick() {
        if (allTabs.length === 0) return;
        if (confirm("Are you sure you want to close all windows?")) {
            if ($dashActive) dashActive.set(false);
            windows.closeAllWindows();
            showWindowsMenu = false;
        }
    }

    function handleWindowClick(event) {
        if (showMenu && startButton && !startButton.contains(event.target)) {
            showMenu = false;
        }
        if (showWindowsMenu && windowsButton && !windowsButton.contains(event.target)) {
            showWindowsMenu = false;
        }
    }

    function launchIosk() {
        newIoskConnection();
        showMenu = false;
    }

    function launchCalculator() {
        newCalculator();
        showMenu = false;
    }

    function launchSettings() {
        newSettings();
        showMenu = false;
    }

    onMount(() => {
        window.addEventListener('click', handleWindowClick);
    });
    onDestroy(() => {
        window.removeEventListener('click', handleWindowClick);
    });
</script>

<style>
    .taskbar {
        height: 40px;
        background-color: var(--taskbar-bg);
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: space-between; /* This will space out left, center, and right sections */
        padding: 0 10px;
        flex-shrink: 0;
        position: relative; /* For menu positioning and absolute children */
        z-index: 20000; /* Ensure taskbar and its menus are above all windows */
    }
    .taskbar-left, .taskbar-right {
        display: flex;
        align-items: center;
        gap: 8px;
        position: relative; /* Establish stacking context */
        z-index: 10;      /* Keep static items on top */
    }
    .taskbar-center {
        /* The clock is absolutely centered to prevent it from shifting
           when the number of buttons on the left or right changes. */
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10; /* Keep clock on top */
    }
    .task-item {
        background-color: var(--taskbar-button-bg);
        color: var(--taskbar-text);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 150px;
        /* Positioning styles for tracking the window */
        position: absolute;
        top: 50%;
        /* The `left` property is now the start of the button.
           We only need to translate vertically. */
        transform: translateY(-50%);
        transition: left 0.3s ease-out;
        z-index: 1;
    }
    .task-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .task-item.minimized {
        font-style: italic;
        opacity: 0.7;
    }
    .task-item.active {
        /* Use the accent color from the start button for a consistent look */
        border-bottom: 2px solid #27c93f;
        /* Adjust padding to keep the button height consistent */
        padding-bottom: 4px;
        z-index: 2; /* Active button on top of other buttons */
    }

    /* Color updates for fixed buttons */
    .taskbar-left > .windows-button:first-child {
        background-color: #ff5f56; /* Match window close button */
        border-color: #e0443e;
        color: white;
    }
    .taskbar-left > .windows-button:first-child:hover {
        background-color: #e0443e;
    }
    .taskbar-left > .windows-button:nth-child(2) {
        background-color: #ffbd2e; /* Match window minimize button */
        border-color: #e0a320;
        color: white;
    }
     .taskbar-left > .windows-button:nth-child(2):hover {
        background-color: #e0a320;
    }

    .start-button {
        background-color: #3498db; /* Swapped from green to blue */
        border: 1px solid #2980b9;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
    }
    .start-button:hover {
        background-color: #2980b9;
    }
    .quick-launch-button {
        background-color: #27c93f; /* Swapped from blue to green */
        border: 1px solid #1a9c2a;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
    }
    .quick-launch-button:hover {
        background-color: #1a9c2a;
    }
    .windows-button {
        background-color: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--taskbar-text);
        font-weight: bold;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
    }
    .windows-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .windows-button.active {
        background-color: var(--taskbar-button-hover-bg);
    }
    .start-menu {
        position: absolute;
        top: 45px; /* Position below the taskbar */
        right: 10px;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        width: 200px;
    }
    .windows-menu {
        position: absolute;
        top: 45px; /* Position below the taskbar */
        left: 10px;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        width: 200px;
        max-height: 300px;
        overflow-y: auto;
    }
    .menu-item {
        background: none;
        border: none;
        color: var(--taskbar-text);
        padding: 10px 15px;
        text-align: left;
        cursor: pointer;
        border-bottom: 1px solid var(--border-color);
    }
    .menu-item:last-child {
        border-bottom: none;
    }
    .menu-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .menu-item:disabled {
        color: #7f8c8d;
        cursor: not-allowed;
    }
    .menu-separator {
        height: 1px;
        background-color: var(--border-color);
        margin: 4px 0;
    }
    .menu-item-empty {
        padding: 10px 15px;
        color: #7f8c8d; /* Muted color */
        font-style: italic;
    }
    .menu-item.close-all {
        color: #e74c3c;
        border-top: 1px solid var(--border-color);
        border-bottom: none;
    }
    .menu-item.close-all:hover {
        background-color: #c0392b;
        color: white;
    }

    /* Styles for menu indicators on buttons */
    .start-button,
    .windows-list-button {
        position: relative; /* Required for pseudo-element positioning */
    }
    .start-button::after,
    .windows-list-button::after {
        content: '';
        position: absolute;
        bottom: 0px;
        width: 0;
        height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid rgba(255, 255, 255, 0.7); /* Downward pointing triangle */
    }
    .start-button::after {
        right: 5px;
    }
    .windows-list-button::after {
        left: 5px;
    }
</style>

<svelte:window bind:innerWidth={screenWidth} />

<div class="taskbar">
    <div class="taskbar-left" bind:this={leftSectionEl}>
        <button class="windows-button" class:active={$dashActive} on:click={() => dashActive.update(v => !v)} title="Dash">
            &mdash;
        </button>
        <button class="windows-button windows-list-button" bind:this={windowsButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showWindowsMenu = !showWindowsMenu; }}>
            W~
        </button>
        {#if showWindowsMenu}
            <div class="windows-menu">
                {#each allTabs.sort((a, b) => a.id - b.id) as tab (tab.id)}
                    <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); windows.setActiveTab(tab.groupId, tab.id); showWindowsMenu = false; }}>
                        {tab.title}
                    </button>
                {:else}
                    <span class="menu-item-empty">No open windows</span>
                {/each}
                {#if allTabs.length > 0}
                    <button class="menu-item close-all" on:click={handleCloseAllClick}>
                        Close All
                    </button>
                {/if}
            </div>
        {/if}
    </div>

    {#each allTabs as tab (tab.id)}
        <button
            class="task-item"
            class:minimized={tab.isGroupMinimized}
            class:active={tab.isGroupActive}
            title={tab.title}
            on:click={() => { if ($dashActive) dashActive.set(false); handleTaskClick(tab); }}
            use:measure={tab.id}
            style="left: {taskItemLayouts[tab.id] ? taskItemLayouts[tab.id].left + 'px' : '-9999px'};"
        >
            {tab.title}
        </button>
    {/each}

    {#each $windows as win (win.id)}
        <button
            class="task-item"
            class:minimized={win.minimized}
            class:active={win.isActive}
            title={win.title}
            on:click={() => { if ($dashActive) dashActive.set(false); handleTaskClick(win); }}
            use:measure={win.id}
            style="left: {taskItemLayouts[win.id] ? taskItemLayouts[win.id].left + 'px' : '-9999px'};"
        >
            {win.title}
        </button>
    {/each}

    <div class="taskbar-center" bind:this={centerSectionEl}>
        <Clock />
    </div>

    <div class="taskbar-right" bind:this={rightSectionEl}>
        <button class="quick-launch-button" on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); launchIosk(); }} title="IOSK Connection">
            $+
        </button>
        <button class="start-button" bind:this={startButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showMenu = !showMenu; }}>
            SK
        </button>

        {#if showMenu}
            <div class="start-menu">
                <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); launchSettings(); }}>Settings</button>
                <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); launchIosk(); }}>IOSK Connection</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); newWebBrowser(); showMenu = false; }}>Web Browser</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => { if ($dashActive) dashActive.set(false); launchCalculator(); }}>Calculator</button>
            </div>
        {/if}
    </div>
</div>
