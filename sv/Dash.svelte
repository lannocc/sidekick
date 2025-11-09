<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { dashActive, dashLayouts, dashCycleIndex } from './desktopStore.js';
    import { windows, restoreWindow } from './windows.js';
    import { get } from 'svelte/store';
    import { onMount, onDestroy } from 'svelte';

    // Import component types to map them to strings for saving layouts
    import IoskConsole from './IoskConsole.svelte';
    import Calculator from './Calculator.svelte';
    import Settings from './Settings.svelte';
    import IoskFileExplorer from './IoskFileExplorer.svelte';
    import IoskFileViewer from './IoskFileViewer.svelte';

    let isLayoutDirty = true;
    let lastSavedLayoutSnapshot = '';

    // --- State for Preview ---
    let manualPreviewedLayout = null; // Controlled by mouse hover
    let cyclePreviewedLayout = null;  // Controlled by keyboard cycle store
    $: previewedLayout = manualPreviewedLayout || cyclePreviewedLayout;

    let previewContainerWidth = 0;
    let previewContainerHeight = 0;
    let previewScale = 1;
    let previewDesktop = { width: 0, height: 0, top: 0, left: 0 };


    // --- Context Menu State ---
    let contextMenu = {
        visible: false,
        x: 0,
        y: 0,
        layoutId: null
    };

    function closeContextMenu() {
        contextMenu = { visible: false, x: 0, y: 0, layoutId: null };
    }

    function handleKeydown(e) {
        // Let SideKick.svelte handle cycling through layouts with modifier keys.
        if (e.metaKey || e.altKey) return;

        if (e.key === 'Escape') {
            e.preventDefault();
            handleMaximizeDash();
        }
    }

    onMount(() => {
        // Close context menu on any click outside of it
        window.addEventListener('click', closeContextMenu);
        window.addEventListener('keydown', handleKeydown);
    });

    onDestroy(() => {
        window.removeEventListener('click', closeContextMenu);
        window.removeEventListener('keydown', handleKeydown);
    });

    function handleRightClick(event, layout) {
        event.preventDefault();
        contextMenu = {
            visible: true,
            x: event.clientX,
            y: event.clientY,
            layoutId: layout.id
        };
    }

    function handleDeleteLayout() {
        if (contextMenu.layoutId === null) return;
        const layoutIdToDelete = contextMenu.layoutId;
        closeContextMenu();

        // Use setTimeout to allow the UI to update (hide menu) before the blocking confirm() dialog appears.
        setTimeout(() => {
            if (confirm('Are you sure you want to delete this layout?')) {
                dashLayouts.update(layouts => layouts.filter(l => l.id !== layoutIdToDelete));
            }
        }, 0);
    }

    function handleRenameLayout() {
        if (contextMenu.layoutId === null) return;
        const layoutIdToRename = contextMenu.layoutId;
        const layoutToRename = get(dashLayouts).find(l => l.id === layoutIdToRename);
        if (!layoutToRename) return;

        closeContextMenu();

        // Use setTimeout to allow the UI to update (hide menu) before the blocking prompt() dialog appears.
        setTimeout(() => {
            const newName = prompt("Enter new name for the layout:", layoutToRename.name);

            if (newName && newName.trim() !== '') {
                dashLayouts.update(layouts =>
                    layouts.map(l =>
                        l.id === layoutIdToRename ? { ...l, name: newName.trim() } : l
                    )
                );
            }
        }, 0);
    }
    // --- End Context Menu Logic ---


    function getComponentType(component) {
        if (component === IoskConsole) return 'IoskConsole';
        if (component === Calculator) return 'Calculator';
        if (component === Settings) return 'Settings';
        if (component === IoskFileExplorer) return 'IoskFileExplorer';
        if (component === IoskFileViewer) return 'IoskFileViewer';
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

    // React to keyboard cycling
    $: if ($dashCycleIndex > -1 && $dashLayouts[$dashCycleIndex]) {
        cyclePreviewedLayout = $dashLayouts[$dashCycleIndex];
    } else {
        cyclePreviewedLayout = null;
    }

    function handleSaveDash() {
        const currentWindows = get(windows);
        // Map current windows to a serializable format
        const layoutWindows = currentWindows.map(win => {
            const associatedConsole = currentWindows.find(c => c.id === win.consoleId);

            return {
                componentType: getComponentType(win.component),
                title: win.title,
                x: win.x,
                y: win.y,
                width: win.width,
                height: win.height,
                maximized: win.maximized,

                // For IoskFileExplorer & IoskFileViewer, save the connection identity
                // so we can re-associate on restore.
                consoleConnection: associatedConsole ? associatedConsole.consoleConnection : null,

                // Component-specific state to restore
                initialPath: win.currentPath, // For IoskFileExplorer. It's saved as `initialPath` for easy restoration.
                path: win.path,               // For IoskFileViewer
                mode: win.mode                // For IoskFileViewer
            };
        });

        // Create the full layout object, now including desktop dimensions for accurate preview scaling
        const layoutToSave = {
            id: Date.now(),
            name: `Layout ${get(dashLayouts).length + 1}`,
            desktop: {
                width: window.innerWidth,
                // The available desktop area height is the viewport height minus the 40px taskbar
                height: window.innerHeight - 40
            },
            windows: layoutWindows
        };

        dashLayouts.update(layouts => [...layouts, layoutToSave]);

        // After saving, mark the current layout as saved and disable the button
        lastSavedLayoutSnapshot = generateLayoutSnapshot(currentWindows);
        isLayoutDirty = false;
    }

    function handleRestoreLayout(layout) {
        if (!layout || !layout.windows) return;

        // Get the dimensions of the desktop when the layout was saved.
        // Fallback to current dimensions if not saved (for older layouts).
        const savedDesktopWidth = layout.desktop?.width || window.innerWidth;
        const savedDesktopHeight = layout.desktop?.height || (window.innerHeight - 40);

        // Get current desktop dimensions.
        const currentDesktopWidth = window.innerWidth;
        const currentDesktopHeight = window.innerHeight - 40;

        // Calculate scaling factors. No need to preserve aspect ratio.
        const scaleX = currentDesktopWidth / savedDesktopWidth;
        const scaleY = currentDesktopHeight / savedDesktopHeight;

        for (const winData of layout.windows) {
            // Create a copy of the window data to avoid modifying the original layout object.
            const scaledWinData = { ...winData };

            // Scale position and size, but only for non-maximized windows.
            if (!scaledWinData.maximized) {
                scaledWinData.x = Math.round(scaledWinData.x * scaleX);
                scaledWinData.y = Math.round(scaledWinData.y * scaleY);
                scaledWinData.width = Math.round(scaledWinData.width * scaleX);
                scaledWinData.height = Math.round(scaledWinData.height * scaleY);
            }

            restoreWindow(scaledWinData);
        }

        // Exit dash mode to see the result
        dashActive.set(false);
    }

    function handleMaximizeDash() {
        // Exits dash mode, returning to previous window arrangement
        dashActive.set(false);
    }

    function handleCancelDash() {
        // Exits dash mode and closes all windows, with confirmation
        if (get(windows).length > 0) {
            setTimeout(() => {
                if (confirm("Are you sure you want to close all windows?")) {
                    dashActive.set(false);
                    windows.closeAllWindows();
                }
            }, 0);
        } else {
            dashActive.set(false);
        }
    }
    
    function handleMinimizeDash() {
        // Exits dash mode and minimizes all windows ("Show Desktop")
        dashActive.set(false);
        windows.minimizeAllWindows();
    }

    // --- Reactive Calculations for Layout Preview ---
    $: if (previewedLayout && previewContainerWidth > 0 && previewContainerHeight > 0) {
        // Fallback for old layouts without saved desktop dimensions, assuming a 16:9 ratio.
        const savedDesktopWidth = previewedLayout.desktop?.width || 1920;
        const savedDesktopHeight = previewedLayout.desktop?.height || 1080;

        const scaleX = previewContainerWidth / savedDesktopWidth;
        const scaleY = previewContainerHeight / savedDesktopHeight;
        // Use 95% of the smallest scale factor to ensure there's a nice padding.
        previewScale = Math.min(scaleX, scaleY) * 0.95;

        const scaledWidth = savedDesktopWidth * previewScale;
        const scaledHeight = savedDesktopHeight * previewScale;

        previewDesktop = {
            width: scaledWidth,
            height: scaledHeight,
            // Center the preview screen within its container.
            left: (previewContainerWidth - scaledWidth) / 2,
            top: (previewContainerHeight - scaledHeight) / 2
        };
    } else {
        // Reset when not previewing.
        previewDesktop = { width: 0, height: 0, top: 0, left: 0 };
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
        position: relative; /* For absolute positioning of preview screen */
        overflow: hidden; /* Hide anything that might spill out */
        padding: 10px;
        box-sizing: border-box;
    }

    .preview-screen {
        position: absolute;
        background-color: rgba(0,0,0,0.2);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        transition: all 0.2s ease-in-out;
    }

    .preview-window {
        position: absolute;
        background-color: rgba(52, 152, 219, 0.5); /* Semi-transparent blue */
        border: 1px solid rgba(41, 128, 185, 0.8);
        border-radius: 2px;
        box-sizing: border-box;
        color: rgba(255, 255, 255, 0.9);
        font-size: 10px;
        padding: 1px 3px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-shadow: 0 0 2px rgba(0,0,0,0.6);
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
    
    .context-menu {
        position: fixed; /* Use fixed to position relative to viewport */
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 1001; /* Above the dash dialog */
        display: flex;
        flex-direction: column;
        padding: 4px 0;
        min-width: 120px;
    }

    .context-menu button {
        background: none;
        border: none;
        color: var(--taskbar-text);
        padding: 8px 12px;
        text-align: left;
        cursor: pointer;
        font-size: 14px;
    }

    .context-menu button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    
    .context-menu button.delete {
        color: #e74c3c;
    }

    .context-menu button.delete:hover {
        background-color: #c0392b;
        color: white;
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
            <button class="control-button save" on:click={handleSaveDash} title="Save Current Layout" disabled={!isLayoutDirty || $windows.length === 0}>&#x2713;</button>
        </div>
    </div>

    <div class="dash-body">
        <div class="dash-preview" bind:clientWidth={previewContainerWidth} bind:clientHeight={previewContainerHeight}>
             {#if previewedLayout && previewDesktop.width > 0}
                <div
                    class="preview-screen"
                    style:width="{previewDesktop.width}px"
                    style:height="{previewDesktop.height}px"
                    style:top="{previewDesktop.top}px"
                    style:left="{previewDesktop.left}px"
                >
                    {#each previewedLayout.windows as win (`${win.title}-${win.x}-${win.y}`)}
                        {@const isMaximized = win.maximized}
                        <div
                            class="preview-window"
                            title={win.title}
                            style:left="{isMaximized ? 0 : (win.x * previewScale)}px"
                            style:top="{isMaximized ? 0 : (win.y * previewScale)}px"
                            style:width="{isMaximized ? '100%' : Math.max(2, win.width * previewScale)}px"
                            style:height="{isMaximized ? '100%' : Math.max(2, win.height * previewScale)}px"
                        >{win.title}</div>
                    {/each}
                </div>
            {:else}
                <p>Hover over a layout to see a preview</p>
            {/if}
        </div>
        <div class="dash-layouts">
            {#each $dashLayouts as layout (layout.id)}
                <div 
                    class="layout-tile" 
                    title={layout.name}
                    on:click={() => handleRestoreLayout(layout)}
                    on:mouseenter={() => manualPreviewedLayout = layout}
                    on:mouseleave={() => manualPreviewedLayout = null}
                    on:contextmenu|preventDefault={e => handleRightClick(e, layout)}
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

{#if contextMenu.visible}
    <div 
        class="context-menu" 
        style="top: {contextMenu.y}px; left: {contextMenu.x}px;"
        on:click|stopPropagation
    >
        <button on:click={handleRenameLayout}>Rename</button>
        <button class="delete" on:click={handleDeleteLayout}>Delete</button>
    </div>
{/if}