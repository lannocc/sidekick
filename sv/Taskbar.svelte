<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { windows, newIoskConnection } from './windows.js';

    function handleTaskClick(win) {
        if (win.minimized) {
            windows.toggleMinimize(win.id);
        } else {
            windows.focusWindow(win.id);
        }
    }
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
    }
    .launcher, .task-item {
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
    .launcher:hover, .task-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .task-item.minimized {
        font-style: italic;
        opacity: 0.7;
    }
</style>

<div class="taskbar">
    <button class="launcher" on:click={newIoskConnection}>
        + New IOSK
    </button>

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

