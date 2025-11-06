<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows, newIoskConnection, newCalculator, newSettings } from './windows.js';
    import Clock from './Clock.svelte';

    let showMenu = false; // For Start menu
    let startButton;

    let showWindowsMenu = false; // For Windows list menu
    let windowsButton;

    let showDashboard = false; // For dashboard toggle

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
                // Update map only if the width has actually changed
                if (taskItemWidths.get(id) !== entry.contentRect.width) {
                    taskItemWidths.set(id, entry.contentRect.width);
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

    // Reactive calculation for task item layouts
    $: if (screenWidth && leftSectionEl && centerSectionEl && rightSectionEl && $windows.length > 0) {
        // Wait until we have widths for all items before calculating the layout
        const allWidthsKnown = $windows.every(win => taskItemWidths.has(win.id));

        if (allWidthsKnown) {
            const leftRect = leftSectionEl.getBoundingClientRect();
            const centerRect = centerSectionEl.getBoundingClientRect();
            const rightRect = rightSectionEl.getBoundingClientRect();

            // Prepare items with their ideal positions and widths, then sort by ideal position
            const items = $windows
                .map(win => ({
                    id: win.id,
                    idealX: getWindowCenterX(win),
                    width: taskItemWidths.get(win.id) || 100, // Fallback width
                }))
                .sort((a, b) => a.idealX - b.idealX);

            const newLayouts = {};
            let lastItemRightEdge = leftRect.right + GAP;

            // --- Pass 1: Place items from left to right, avoiding collisions ---
            for (const item of items) {
                const itemWidth = item.width;
                let idealLeft = item.idealX - itemWidth / 2;

                // Position is either its ideal spot or right after the previous item
                let left = Math.max(idealLeft, lastItemRightEdge);

                // Check for collision with the center clock area
                if ((left + itemWidth + GAP) > centerRect.left && left < (centerRect.right + GAP)) {
                    // It collides. Push it to be after the clock, ensuring it's also after the previous item.
                    left = Math.max(lastItemRightEdge, centerRect.right + GAP);
                }

                newLayouts[item.id] = { left };
                lastItemRightEdge = left + itemWidth + GAP;
            }

            // --- Pass 2: Adjust if the whole group overflows past the right section ---
            let overflow = lastItemRightEdge - (rightRect.left - GAP);
            if (overflow > 0) {
                const firstItem = items[0];
                const firstItemLeft = newLayouts[firstItem.id].left;

                // We can only shift left by the amount of space available on the left
                const availableShift = firstItemLeft - (leftRect.right + GAP);
                const shiftAmount = Math.min(overflow, availableShift);

                if (shiftAmount > 0) {
                    for (const item of items) {
                        newLayouts[item.id].left -= shiftAmount;
                    }
                }
            }

            taskItemLayouts = newLayouts;
        }
    } else if ($windows.length === 0) {
        taskItemLayouts = {}; // Clear layouts if no windows are open
    }

    // Helper to calculate a window's horizontal center
    function getWindowCenterX(win) {
        // A maximized window's center is the screen's center
        return win.maximized ? screenWidth / 2 : win.x + win.width / 2;
    }

    function handleTaskClick(win) {
        // If the window is minimized, this will restore and focus it.
        // If the window is open, this will minimize it as requested.
        windows.toggleMinimize(win.id);
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
    .start-button {
        background-color: #27c93f; /* Standout color */
        border: 1px solid #1a9c2a;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
        /* Pushes button to the far right */
    }
    .quick-launch-button {
        background-color: #3498db; /* A distinct, functional blue */
        border: 1px solid #2980b9;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
    }
    .quick-launch-button:hover {
        background-color: #2980b9;
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
</style>

<svelte:window bind:innerWidth={screenWidth} />

<div class="taskbar">
    <div class="taskbar-left" bind:this={leftSectionEl}>
        <button class="windows-button" bind:this={windowsButton} on:click|stopPropagation={() => showWindowsMenu = !showWindowsMenu}>
            W~
        </button>
        <button class="windows-button" class:active={showDashboard} on:click={() => showDashboard = !showDashboard} title="Toggle Dashboard">
            &mdash;
        </button>
        {#if showWindowsMenu}
            <div class="windows-menu">
                {#each $windows.sort((a, b) => a.id - b.id) as win (win.id)}
                    <button class="menu-item" on:click={() => { windows.focusWindow(win.id); showWindowsMenu = false; }}>
                        {win.title}
                    </button>
                {:else}
                    <span class="menu-item-empty">No open windows</span>
                {/each}
                {#if $windows.length > 0}
                    <button class="menu-item close-all" on:click={() => { windows.closeAllWindows(); showWindowsMenu = false; }}>
                        Close All
                    </button>
                {/if}
            </div>
        {/if}
    </div>

    {#each $windows as win (win.id)}
        <button
            class="task-item"
            class:minimized={win.minimized}
            class:active={win.isActive}
            title={win.title}
            on:click={() => handleTaskClick(win)}
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
        <button class="quick-launch-button" on:click|stopPropagation={launchIosk} title="New IOSK Connection">
            $+
        </button>
        <button class="start-button" bind:this={startButton} on:click|stopPropagation={() => showMenu = !showMenu}>
            SK
        </button>

        {#if showMenu}
            <div class="start-menu">
                <button class="menu-item" on:click={launchIosk}>New IOSK Connection</button>
                <button class="menu-item" on:click={launchCalculator}>Calculator</button>
                <button class="menu-item" on:click={launchSettings}>Settings</button>
            </div>
        {/if}
    </div>
</div>

