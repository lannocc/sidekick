<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { windows, newIoskConnection, newCalculator } from './windows.js';

    let showMenu = false;
    let startButton;

    function handleTaskClick(win) {
        // If the window is minimized, this will restore and focus it.
        // If the window is open, this will minimize it as requested.
        windows.toggleMinimize(win.id);
    }

    function handleWindowClick(event) {
        if (showMenu && !startButton.contains(event.target)) {
            showMenu = false;
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
        border-top: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        padding: 0 10px;
        gap: 8px;
        flex-shrink: 0;
        position: relative; /* For menu positioning */
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
    .start-button {
        background-color: #27c93f; /* Standout color */
        border: 1px solid #1a9c2a;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 5px 10px;
        cursor: pointer;
    }
    .start-menu {
        position: absolute;
        bottom: 45px; /* Position above the taskbar */
        left: 10px;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 -3px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        width: 200px;
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
</style>

<div class="taskbar">
    <button class="start-button" bind:this={startButton} on:click|stopPropagation={() => showMenu = !showMenu}>
        SK
    </button>

    {#if showMenu}
        <div class="start-menu">
            <button class="menu-item" on:click={launchIosk}>New IOSK Connection</button>
            <button class="menu-item" on:click={launchCalculator}>Calculator</button>
        </div>
    {/if}

    {#each $windows as win (win.id)}
        <button
            class="task-item"
            class:minimized={win.minimized}
            title={win.title}
            on:click={() => handleTaskClick(win)}
        >
            {win.title}
        </button>
    {/each}
</div>

