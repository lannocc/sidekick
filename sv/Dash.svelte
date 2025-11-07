<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { dashActive, dashLayouts } from './desktopStore.js';
    import { windows, restoreWindow } from './windows.js';
    import { get } from 'svelte/store';

    // Import component types to map them to strings for saving layouts
    import IoskConsole from './IoskConsole.svelte';
    import Calculator from './Calculator.svelte';
    import Settings from './Settings.svelte';
    import IoskFileExplorer from './IoskFileExplorer.svelte';

    let isLayoutDirty = true;
    let lastSavedLayoutSnapshot = '';

    function getComponentType(component) {
        if (component === IoskConsole) return 'IoskConsole';
        if (component === Calculator) return 'Calculator';
        if (component === Settings) return 'Settings';
        if (component === IoskFileExplorer) return 'IoskFileExplorer';
        return 'Unknown';
    }

    // Helper to create a comparable snapshot of the window layout
    function generateLayoutSnapshot(windowsArray) {
        if (!windowsArray) return '[]';
        // Sort by ID to ensure consistent string output for comparison
        const sortedWindows = [...windowsArray].sort((a, b) => a.id - b.id);
        const relevantData = sortedWindows.map(win => ({
            id: win.id, // ID is important for comparison
            x: win.x,
            y: win.y,
            width: win.width,
            height: win.height,
            minimized: win.minimized,
            maximized: win.maximized
        }));
        return JSON.stringify(relevantData);
    }

    // Watch for window changes to re-enable the save button
    $: {
        if ($windows) {
            const currentSnapshot = generateLayoutSnapshot($windows);
            if (currentSnapshot !== lastSavedLayoutSnapshot) {
                isLayoutDirty = true;
            }
        }
    }

    function handleSaveDash() {
        const currentWindows = get(windows);
        // We only care about position, size, and component info for restoring.
        const layoutToSave = currentWindows.map(win => ({
            componentType: getComponentType(win.component),
            title: win.title,
            x: win.x,
            y: win.y,
            width: win.width,
            height: win.height,
            maximized: win.maximized,
            consoleId: win.consoleId, // Specific prop for File Explorer
        }));

        dashLayouts.update(layouts => [...layouts, { id: Date.now(), name: `Layout ${layouts.length + 1}`, windows: layoutToSave }]);

        // After saving, mark the current layout as saved and disable the button
        lastSavedLayoutSnapshot = generateLayoutSnapshot(currentWindows);
        isLayoutDirty = false;
    }

    function handleRestoreLayout(layout) {
        if (!layout || !layout.windows) return;
        for (const winData of layout.windows) {
            restoreWindow(winData);
        }
        // Exit dash mode to see the result
        dashActive.set(false);
    }

    function handleMaximizeDash() {
        // Exits dash mode, returning to previous window arrangement
        dashActive.set(false);
    }

    function handleCancelDash() {
        // Exits dash mode and closes all windows
        dashActive.set(false);
        windows.closeAllWindows();
    }
    
    function handleMinimizeDash() {
        // Exits dash mode and minimizes all windows ("Show Desktop")
        dashActive.set(false);
        windows.minimizeAllWindows();
    }
</script>

<style>
    .dash-dialog {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        
        display: flex;
        flex-direction: column;
        color: var(--title-bar-text);
        z-index: 1000;
        user-select: none;
        box-sizing: border-box;
        padding: 40px;
    }

    .dash-header {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        flex-shrink: 0;
    }
    
    .dash-title {
        font-size: 1.5em;
        font-weight: 300;
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
    }

    .header-controls {
        display: flex;
        gap: 10px;
        align-items: center;
    }
    
    .control-button {
        background: none;
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        border-radius: 4px;
        width: 30px;
        height: 30px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2em;
        font-family: monospace;
        transition: background-color 0.2s;
    }
    
    .control-button:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .control-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .control-button.save {
        color: #27c93f; /* green checkmark */
        font-size: 1.4em;
    }
    .control-button.cancel {
        color: #ff5f56; /* red X */
        font-size: 1.5em;
    }

    .dash-body {
        flex-grow: 1;
        display: flex;
        gap: 40px;
        margin-top: 40px; /* space for header */
    }

    .dash-preview {
        flex: 3;
        background-color: rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(255, 255, 255, 0.3);
    }

    .dash-layouts {
        flex: 1;
        background-color: rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 15px;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
        gap: 15px;
        overflow-y: auto;
    }

    .layout-tile {
        aspect-ratio: 16 / 10;
        background-color: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        padding: 5px;
        text-align: center;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .layout-tile:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        border-color: var(--taskbar-button-hover-bg);
    }

</style>

<div class="dash-dialog">
    <div class="dash-header">
        <div class="header-controls left">
            <button class="control-button cancel" on:click={handleCancelDash} title="Cancel and Close All Windows">&times;</button>
            <button class="control-button" on:click={handleMinimizeDash} title="Show Desktop">_</button>
        </div>
        <h1 class="dash-title">Dash</h1>
        <div class="header-controls right">
            <button class="control-button" on:click={handleMaximizeDash} title="Full Dash">&#9632;</button>
            <button class="control-button save" on:click={handleSaveDash} title="Save Current Layout" disabled={!isLayoutDirty}>&#x2713;</button>
        </div>
    </div>

    <div class="dash-body">
        <div class="dash-preview">
            <p>Layout Preview</p>
        </div>
        <div class="dash-layouts">
            {#each $dashLayouts as layout (layout.id)}
                <div 
                    class="layout-tile" 
                    title={layout.name}
                    on:click={() => handleRestoreLayout(layout)}
                    role="button" 
                    tabindex="0"
                    on:keydown={e => e.key === 'Enter' && handleRestoreLayout(layout)}
                >
                    {layout.name}
                </div>
            {/each}
        </div>
    </div>
</div>