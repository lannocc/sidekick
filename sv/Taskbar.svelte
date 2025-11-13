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
                if (entry.borderBoxSize && entry.borderBoxSize.length > 0) {
                    newWidth = entry.borderBoxSize[0].inlineSize;
                } else {
                    newWidth = entry.target.getBoundingClientRect().width;
                }
                if (taskItemWidths.get(id) !== newWidth) {
                    taskItemWidths.set(id, newWidth);
                    taskItemWidths = taskItemWidths;
                }
            }
        });
        ro.observe(node);

        return {
            destroy() {
                ro.disconnect();
                if (taskItemWidths.has(id)) {
                    taskItemWidths.delete(id);
                    taskItemWidths = taskItemWidths;
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
        if (win.maximized) {
            return screenWidth / 2 - buttonWidth / 2;
        }
        const windowCenter = win.x + win.width / 2;
        const progress = Math.max(0, Math.min(1, windowCenter / screenWidth));
        const leftAlignedPos = win.x;
        const rightAlignedPos = win.x + win.width - buttonWidth;
        let idealLeft = leftAlignedPos * (1 - progress) + rightAlignedPos * progress;
        idealLeft = Math.max(0, Math.min(idealLeft, screenWidth - buttonWidth));
        return idealLeft;
    }

    $: if (screenWidth && leftSectionEl && centerSectionEl && rightSectionEl && $windows.length > 0) {
        const allWidthsKnown = $windows.every(win => taskItemWidths.has(win.id));
        if (allWidthsKnown) {
            const leftRect = leftSectionEl.getBoundingClientRect();
            const centerRect = centerSectionEl.getBoundingClientRect();
            const rightRect = rightSectionEl.getBoundingClientRect();

            const items = $windows
                .map(win => ({ id: win.id, idealLeft: getIdealButtonLeft(win, taskItemWidths.get(win.id) || 100), width: taskItemWidths.get(win.id) || 100 }))
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

            let overflow = lastItemRightEdge - (rightRect.left - GAP);
            if (overflow > 0) {
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
    } else if ($windows.length === 0) {
        taskItemLayouts = {};
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

    function launchIosk() { newIoskConnection(); showMenu = false; }
    function launchCalculator() { newCalculator(); showMenu = false; }
    function launchSettings() { newSettings(); showMenu = false; }

    onMount(() => window.addEventListener('click', handleWindowClick));
    onDestroy(() => window.removeEventListener('click', handleWindowClick));
</script>

<style>
    .taskbar { height: 40px; background-color: var(--taskbar-bg); border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 10px; flex-shrink: 0; position: relative; z-index: 20000; }
    .taskbar-left, .taskbar-right { display: flex; align-items: center; gap: 8px; position: relative; z-index: 10; }
    .taskbar-center { position: absolute; left: 50%; transform: translateX(-50%); z-index: 10; }
    .task-item { background-color: var(--taskbar-button-bg); color: var(--taskbar-text); border: 1px solid var(--border-color); border-radius: 4px; padding: 2px 5px; cursor: pointer; max-width: 250px; position: absolute; top: 50%; transform: translateY(-50%); transition: left 0.3s ease-out; z-index: 1; display: flex; align-items: center; justify-content: center; }
    .task-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .task-item.minimized { font-style: italic; opacity: 0.7; }
    .task-item.active { border-bottom: 2px solid #27c93f; padding-bottom: 1px; z-index: 2; }
    .taskbar-left > .windows-button:first-child { background-color: #ff5f56; border-color: #e0443e; color: white; }
    .taskbar-left > .windows-button:first-child:hover { background-color: #e0443e; }
    .taskbar-left > .windows-button:nth-child(2) { background-color: #ffbd2e; border-color: #e0a320; color: white; }
    .taskbar-left > .windows-button:nth-child(2):hover { background-color: #e0a320; }
    .start-button { background-color: #3498db; border: 1px solid #2980b9; color: white; font-weight: bold; border-radius: 4px; padding: 5px 10px; cursor: pointer; }
    .start-button:hover { background-color: #2980b9; }
    .quick-launch-button { background-color: #27c93f; border: 1px solid #1a9c2a; color: white; font-weight: bold; border-radius: 4px; padding: 5px 10px; cursor: pointer; }
    .quick-launch-button:hover { background-color: #1a9c2a; }
    .windows-button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--taskbar-text); font-weight: bold; border-radius: 4px; padding: 5px 10px; cursor: pointer; }
    .windows-button:hover { background-color: var(--taskbar-button-hover-bg); }
    .windows-button.active { background-color: var(--taskbar-button-hover-bg); }
    .start-menu, .windows-menu { position: absolute; top: 45px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 10000; display: flex; flex-direction: column; width: 200px; }
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

    /* New styles for tab representation */
    .task-item-layout { display: flex; align-items: center; gap: 4px; overflow: hidden; width: 100%; justify-content: center; }
    .active-tab-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 1; }
    .inactive-tabs-group { display: flex; gap: 3px; flex-shrink: 1; overflow: hidden; }
    .inactive-tab { display: inline-block; font-size: 0.65em; line-height: 1.1; max-width: 60px; padding: 2px 3px; background-color: rgba(0,0,0,0.2); border-radius: 3px; white-space: normal; word-break: break-word; text-align: center; opacity: 0.8; }
</style>

<svelte:window bind:innerWidth={screenWidth} />

<div class="taskbar">
    <div class="taskbar-left" bind:this={leftSectionEl}>
        <button class="windows-button" class:active={$dashActive} on:click={() => dashActive.update(v => !v)} title="Dash">&mdash;</button>
        <button class="windows-button windows-list-button" bind:this={windowsButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showWindowsMenu = !showWindowsMenu; }}>W~</button>
        {#if showWindowsMenu}
            <div class="windows-menu">
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
            title={activeTab?.title}
            on:click={() => { if ($dashActive) dashActive.set(false); handleTaskClick(win); }}
            use:measure={win.id}
            style="left: {taskItemLayouts[win.id] ? taskItemLayouts[win.id].left + 'px' : '-9999px'};"
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

    <div class="taskbar-center" bind:this={centerSectionEl}><Clock /></div>
    <div class="taskbar-right" bind:this={rightSectionEl}>
        <button class="quick-launch-button" on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); launchIosk(); }} title="IOSK Connection">$+</button>
        <button class="start-button" bind:this={startButton} on:click|stopPropagation={() => { if ($dashActive) dashActive.set(false); showMenu = !showMenu; }}>SK</button>
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