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
        position: relative; /* For menu positioning */
    }
    .taskbar-left, .taskbar-right {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .taskbar-center {
        /* The clock goes here, centered automatically */
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

<div class="taskbar">
    <div class="taskbar-left">
        <button class="windows-button" bind:this={windowsButton} on:click|stopPropagation={() => showWindowsMenu = !showWindowsMenu}>
            Windows
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

        {#each $windows as win (win.id)}
            <button
                class="task-item"
                class:minimized={win.minimized}
                class:active={win.isActive}
                title={win.title}
                on:click={() => handleTaskClick(win)}
            >
                {win.title}
            </button>
        {/each}
    </div>

    <div class="taskbar-center">
        <Clock />
    </div>

    <div class="taskbar-right">
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

