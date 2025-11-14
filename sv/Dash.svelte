<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { dashActive, dashLayouts, dashCycleIndex } from './desktopStore.js';
    import { windows } from './windows.js';
    import { get } from 'svelte/store';
    import { onMount, onDestroy } from 'svelte';

    import IoskConsole from './IoskConsole.svelte';
    import Calculator from './Calculator.svelte';
    import Settings from './Settings.svelte';
    import IoskFileExplorer from './IoskFileExplorer.svelte';
    import IoskFileViewer from './IoskFileViewer.svelte';
    import WebBrowser from './WebBrowser.svelte';
    import IoskPrivateChat from './IoskPrivateChat.svelte';

    let isLayoutDirty = true;
    let lastSavedLayoutSnapshot = '';
    let currentLayout = null;
    let manualPreviewedLayout = null;
    let cyclePreviewedLayout = null;
    $: previewedLayout = manualPreviewedLayout || cyclePreviewedLayout;
    let previewContainerWidth = 0, previewContainerHeight = 0, previewScale = 1;
    let previewDesktop = { width: 0, height: 0, top: 0, left: 0 };

    let contextMenu = { visible: false, x: 0, y: 0, layoutId: null, type: 'saved' };

    function closeContextMenu() {
        contextMenu = { visible: false, x: 0, y: 0, layoutId: null, type: 'saved' };
    }

    function handleKeydown(e) {
        if (e.metaKey || e.altKey) return;
        if (e.key === 'Escape') { e.preventDefault(); handleMaximizeDash(); }
    }

    onMount(() => {
        window.addEventListener('click', closeContextMenu);
        window.addEventListener('keydown', handleKeydown);
    });

    onDestroy(() => {
        window.removeEventListener('click', closeContextMenu);
        window.removeEventListener('keydown', handleKeydown);
    });

    function handleRightClick(event, layout) {
        event.preventDefault();
        contextMenu = { visible: true, x: event.clientX, y: event.clientY, layoutId: layout.id, type: 'saved' };
    }

    function handleDeleteLayout() {
        if (contextMenu.layoutId === null) return;
        const layoutIdToDelete = contextMenu.layoutId;
        closeContextMenu();
        setTimeout(() => { if (confirm('Are you sure you want to delete this layout?')) { dashLayouts.update(layouts => layouts.filter(l => l.id !== layoutIdToDelete)); } }, 0);
    }

    function handleRenameLayout() {
        if (contextMenu.layoutId === null) return;
        const layoutIdToRename = contextMenu.layoutId;
        const layoutToRename = get(dashLayouts).find(l => l.id === layoutIdToRename);
        if (!layoutToRename) return;
        closeContextMenu();
        setTimeout(() => {
            const newName = prompt("Enter new name for the layout:", layoutToRename.name);
            if (newName && newName.trim() !== '') { dashLayouts.update(layouts => layouts.map(l => l.id === layoutIdToRename ? { ...l, name: newName.trim() } : l)); }
        }, 0);
    }

    function handleCurrentDesktopRightClick(event) {
        event.preventDefault();
        contextMenu = { visible: true, x: event.clientX, y: event.clientY, layoutId: null, type: 'current' };
    }

    function handleSaveAs() {
        closeContextMenu();
        setTimeout(() => {
            const defaultName = `Layout ${get(dashLayouts).length + 1}`;
            const newName = prompt("Enter a name for the new layout:", defaultName);
            if (newName && newName.trim() !== '') {
                const currentWindows = get(windows);
                const layoutToSave = generateLayoutObject(currentWindows, newName.trim(), Date.now());
                dashLayouts.update(layouts => [...layouts, layoutToSave]);
                lastSavedLayoutSnapshot = generateLayoutSnapshot(currentWindows);
                isLayoutDirty = false;
            }
        }, 0);
    }

    function handleDeleteCurrent() {
        closeContextMenu();
        handleCancelDash();
    }

    function findTabById(groups, tabId) {
        for (const group of groups) {
            const tab = group.tabs.find(t => t.id === tabId);
            if (tab) return tab;
        }
        return null;
    }

    function generateLayoutObject(groupsArray, name, id) {
        const layoutGroups = groupsArray.map(group => {
            const layoutTabs = group.tabs.map(tab => {
                const associatedConsole = findTabById(groupsArray, tab.consoleId);
                return {
                    originalId: tab.id,
                    componentType: getComponentType(tab.component),
                    title: tab.title,
                    maximized: group.maximized, // This is a group property but convenient here
                    wsUrl: tab.wsUrl, username: tab.username,
                    localUser: tab.localUser, remoteUser: tab.remoteUser,
                    consoleConnection: associatedConsole ? associatedConsole.consoleConnection : null,
                    initialPath: tab.currentPath, path: tab.path,
                    mode: tab.mode, initialUrl: tab.currentUrl,
                };
            });
            return {
                x: group.x, y: group.y, width: group.width, height: group.height,
                maximized: group.maximized,
                activeTabId: group.activeTabId,
                tabs: layoutTabs
            };
        });

        return {
            id: id, name: name,
            desktop: { width: window.innerWidth, height: window.innerHeight - 40 },
            windowGroups: layoutGroups
        };
    }

    function getComponentType(component) {
        if (component === IoskConsole) return 'IoskConsole';
        if (component === Calculator) return 'Calculator';
        if (component === Settings) return 'Settings';
        if (component === IoskFileExplorer) return 'IoskFileExplorer';
        if (component === IoskFileViewer) return 'IoskFileViewer';
        if (component === WebBrowser) return 'WebBrowser';
        if (component === IoskPrivateChat) return 'IoskPrivateChat';
        return 'Unknown';
    }

    function generateLayoutSnapshot(groupsArray) {
        if (!groupsArray) return '[]';
        const sortedGroups = [...groupsArray].sort((a, b) => a.id - b.id);
        const relevantData = sortedGroups.map(g => ({
            id: g.id, x: g.x, y: g.y, width: g.width, height: g.height,
            minimized: g.minimized, maximized: g.maximized,
            tabs: g.tabs.map(t => t.id).sort(),
            activeTabId: g.activeTabId
        }));
        return JSON.stringify(relevantData);
    }

    $: if ($dashActive) {
        currentLayout = generateLayoutObject(get(windows), 'Current Desktop', 'current');
        if (!manualPreviewedLayout && !cyclePreviewedLayout) {
            manualPreviewedLayout = currentLayout;
        }
    } else {
        currentLayout = null;
        manualPreviewedLayout = null;
    }

    $: if ($windows) {
        const currentSnapshot = generateLayoutSnapshot($windows);
        if (currentSnapshot !== lastSavedLayoutSnapshot) isLayoutDirty = true;
    }

    $: if ($dashCycleIndex > -1 && $dashLayouts[$dashCycleIndex]) {
        cyclePreviewedLayout = $dashLayouts[$dashCycleIndex];
    } else {
        cyclePreviewedLayout = null;
    }

    function handleSaveDash() {
        const currentWindows = get(windows);
        const layoutToSave = generateLayoutObject(currentWindows, `Layout ${get(dashLayouts).length + 1}`, Date.now());
        dashLayouts.update(layouts => [...layouts, layoutToSave]);
        lastSavedLayoutSnapshot = generateLayoutSnapshot(currentWindows);
        isLayoutDirty = false;
    }

    function handleRestoreLayout(layout) {
        if (!layout || !layout.windowGroups) return;

        const savedDesktopWidth = layout.desktop?.width || window.innerWidth;
        const savedDesktopHeight = layout.desktop?.height || (window.innerHeight - 40);
        const currentDesktopWidth = window.innerWidth;
        const currentDesktopHeight = window.innerHeight - 40;
        const scaleX = currentDesktopWidth / savedDesktopWidth;
        const scaleY = currentDesktopHeight / savedDesktopHeight;

        for (const groupData of layout.windowGroups) {
            const scaledGroupData = { ...groupData };
            if (!scaledGroupData.maximized) {
                scaledGroupData.x = Math.round(scaledGroupData.x * scaleX);
                scaledGroupData.y = Math.round(scaledGroupData.y * scaleY);
                scaledGroupData.width = Math.round(scaledGroupData.width * scaleX);
                scaledGroupData.height = Math.round(scaledGroupData.height * scaleY);
            }
            windows.restoreWindow(scaledGroupData);
        }
        dashActive.set(false);
    }

    function handleMaximizeDash() {
        windows.restoreAllWindows();
        dashActive.set(false);
    }

    function handleCancelDash() {
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
        dashActive.set(false);
        windows.minimizeAllWindows();
    }

    $: if (previewedLayout && previewContainerWidth > 0 && previewContainerHeight > 0) {
        const savedDesktopWidth = previewedLayout.desktop?.width || 1920;
        const savedDesktopHeight = previewedLayout.desktop?.height || 1080;
        const scaleX = previewContainerWidth / savedDesktopWidth;
        const scaleY = previewContainerHeight / savedDesktopHeight;
        previewScale = Math.min(scaleX, scaleY) * 0.95;
        const scaledWidth = savedDesktopWidth * previewScale;
        const scaledHeight = savedDesktopHeight * previewScale;
        previewDesktop = {
            width: scaledWidth, height: scaledHeight,
            left: (previewContainerWidth - scaledWidth) / 2,
            top: (previewContainerHeight - scaledHeight) / 2
        };
    } else {
        previewDesktop = { width: 0, height: 0, top: 0, left: 0 };
    }
</script>

<style>
    .dash-dialog { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; color: var(--title-bar-text); z-index: 1000; user-select: none; box-sizing: border-box; padding: 40px; }
    .dash-header { position: absolute; top: 0; left: 0; right: 0; height: 40px; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; flex-shrink: 0; }
    .dash-title { font-size: 1.5em; font-weight: 300; position: absolute; left: 50%; transform: translateX(-50%); }
    .header-controls { display: flex; gap: 10px; align-items: center; }
    .control-button { background: none; border: 1px solid var(--border-color); color: var(--title-bar-text); border-radius: 4px; width: 30px; height: 30px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1.2em; font-family: monospace; transition: background-color 0.2s; }
    .control-button:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .control-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .control-button.save { color: #27c93f; font-size: 1.4em; }
    .control-button.cancel { color: #ff5f56; font-size: 1.5em; }
    .dash-body { flex-grow: 1; display: flex; gap: 40px; margin-top: 40px; min-height: 0; }
    .dash-preview { flex: 3; background-color: rgba(0,0,0,0.1); border: 1px solid var(--border-color); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: rgba(255, 255, 255, 0.3); position: relative; overflow: hidden; padding: 10px; box-sizing: border-box; }
    .preview-screen { position: absolute; background-color: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 4px; transition: all 0.2s ease-in-out; }
    .preview-window { position: absolute; background-color: rgba(52, 152, 219, 0.5); border: 1px solid rgba(41, 128, 185, 0.8); border-radius: 2px; box-sizing: border-box; overflow: hidden; display: flex; flex-direction: column; }
    .preview-title-bar { display: flex; flex-shrink: 0; background-color: rgba(0,0,0,0.2); overflow: hidden; align-items: center; height: 14px; }
    .preview-tab { padding: 0 3px; font-size: 9px; line-height: 14px; color: rgba(255, 255, 255, 0.8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70px; border-right: 1px solid rgba(41, 128, 185, 0.4); text-shadow: 0 0 2px rgba(0,0,0,0.6); }
    .preview-tab.active { font-weight: bold; color: white; background-color: rgba(255,255,255,0.1); }
    .dash-layouts { flex: 1; background-color: rgba(0,0,0,0.1); border: 1px solid var(--border-color); border-radius: 8px; padding: 15px; display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 15px; overflow-y: auto; min-height: 0; }
    .layout-tile { aspect-ratio: 16 / 10; background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-direction: column; padding: 5px; text-align: center; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }
    .layout-tile:hover { transform: translateY(-3px); box-shadow: 0 4px 10px rgba(0,0,0,0.3); border-color: var(--taskbar-button-hover-bg); }
    .layout-tile.current { border-color: #27c93f; box-shadow: 0 0 8px rgba(39, 201, 63, 0.4); }
    .layout-tile.highlighted { border-color: #3498db; box-shadow: 0 0 8px rgba(52, 152, 219, 0.5); }
    .context-menu { position: fixed; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 1001; display: flex; flex-direction: column; padding: 4px 0; min-width: 120px; }
    .context-menu button { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .context-menu button:hover { background-color: var(--taskbar-button-hover-bg); }
    .context-menu button.delete { color: #e74c3c; }
    .context-menu button.delete:hover { background-color: #c0392b; color: white; }
    @media (max-width: 900px) { .dash-body { flex-direction: column; gap: 20px; } }
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
                <div class="preview-screen" style:width="{previewDesktop.width}px" style:height="{previewDesktop.height}px" style:top="{previewDesktop.top}px" style:left="{previewDesktop.left}px">
                    {#each (previewedLayout.windowGroups || []) as group}
                        {@const isMaximized = group.maximized}
                        <div class="preview-window" title={group.tabs.map(t => t.title).join(' | ')} style:left="{isMaximized ? 0 : (group.x * previewScale)}px" style:top="{isMaximized ? 0 : (group.y * previewScale)}px" style:width="{isMaximized ? '100%' : Math.max(20, group.width * previewScale)}px" style:height="{isMaximized ? '100%' : Math.max(16, group.height * previewScale)}px">
                            <div class="preview-title-bar">
                                {#each group.tabs as tab (tab.originalId)}
                                    <div class="preview-tab" class:active={tab.originalId === group.activeTabId} title={tab.title}>
                                        {tab.title}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/each}
                </div>
            {:else}
                <p>Hover over a layout to see a preview</p>
            {/if}
        </div>
        <div class="dash-layouts">
            {#if currentLayout}
                <div class="layout-tile current" title={currentLayout.name} on:click={handleMaximizeDash} on:mouseenter={() => manualPreviewedLayout = currentLayout} on:mouseleave={() => manualPreviewedLayout = null} role="button" tabindex="0" on:contextmenu|preventDefault={handleCurrentDesktopRightClick} on:keydown={e => e.key === 'Enter' && handleMaximizeDash()}>
                    {currentLayout.name}
                </div>
            {/if}
            {#each $dashLayouts as layout (layout.id)}
                <div class="layout-tile" class:highlighted={cyclePreviewedLayout && cyclePreviewedLayout.id === layout.id} title={layout.name} on:click={() => handleRestoreLayout(layout)} on:mouseenter={() => manualPreviewedLayout = layout} on:mouseleave={() => manualPreviewedLayout = null} on:contextmenu|preventDefault={e => handleRightClick(e, layout)} role="button" tabindex="0" on:keydown={e => e.key === 'Enter' && handleRestoreLayout(layout)}>
                    {layout.name}
                </div>
            {/each}
        </div>
    </div>
</div>

{#if contextMenu.visible}
    <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
        {#if contextMenu.type === 'current'}
            <button on:click={handleSaveAs} disabled={$windows.length === 0}>Save As...</button>
            <button class="delete" on:click={handleDeleteCurrent}>Delete</button>
        {:else}
            <button on:click={handleRenameLayout}>Rename</button>
            <button class="delete" on:click={handleDeleteLayout}>Delete</button>
        {/if}
    </div>
{/if}