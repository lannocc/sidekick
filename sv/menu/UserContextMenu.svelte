<!-- sv/UserContextMenu.svelte -->
<script>
    import { createEventDispatcher } from 'svelte';

    export let x = 0;
    export let y = 0;
    export let user = null;
    export let colorNameToCss = {};

    const dispatch = createEventDispatcher();
    let showColorPicker = false;

    function dispatchAndClose(eventName, detail) {
        dispatch(eventName, detail);
    }
</script>

<style>
    .user-context-menu {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 200; /* Above console content */
        display: flex;
        flex-direction: column;
        padding: 4px;
        min-width: 120px;
    }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; border-bottom: 1px solid var(--border-color); }
    .menu-item:last-child { border-bottom: none; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-separator { height: 3px; background-color: var(--border-color); margin: 0; }
    .close-item { color: #e74c3c; }
    .close-item:hover { background-color: #c0392b; color: white; }
    .color-picker-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 4px;
        padding: 4px;
    }
    .color-swatch {
        width: 24px;
        height: 24px;
        border: 1px solid var(--border-color);
        border-radius: 3px;
        cursor: pointer;
        background: none; /* remove default button background */
    }
    .color-swatch:hover {
        border-color: var(--taskbar-button-hover-bg);
        transform: scale(1.1);
    }
</style>

<div
    class="user-context-menu"
    style="top: {y}px; left: {x}px;"
    on:click|stopPropagation
>
    {#if showColorPicker}
        <div class="color-picker-grid">
            {#each Object.entries(colorNameToCss) as [name, cssVar] (name)}
                <button
                    class="color-swatch"
                    style="background-color: {cssVar}"
                    title={name.replace(/_/g, ' ')}
                    on:click={() => dispatchAndClose('setColor', name)}
                ></button>
            {/each}
        </div>
        <div class="menu-separator"></div>
        <button class="menu-item" on:click={() => showColorPicker = false}>
            &larr; Back
        </button>
    {:else}
        <button class="menu-item" on:click={() => dispatchAndClose('inspectContext', user)}>
          Context
        </button>
        <div class="menu-separator"></div>
        <button class="menu-item" on:click={() => dispatchAndClose('privateChat', user)}>
            Private Chat
        </button>
        <button class="menu-item" on:click={() => dispatchAndClose('viewLog')}>
            View Log
        </button>
        <button class="menu-item" on:click={() => showColorPicker = true}>
          Color
        </button>
        <div class="menu-separator"></div>
        <button class="menu-item close-item" on:click={() => dispatchAndClose('detach')}>
            Detach
        </button>
    {/if}
</div>