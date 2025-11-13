<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher, tick, onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { windows, newIoskFileExplorer } from './windows.js';
    import { desktopSettings, windowSettings, tabDropTarget } from './desktopStore.js';
    import IoskConsole from './IoskConsole.svelte';
    import IoskFileViewer from './IoskFileViewer.svelte';

    // --- Group Props ---
    export let id; // Group ID
    export let x, y, width, height, zIndex, minimized, maximized, isActive, tabs, activeTabId;
    
    // --- Derived State ---
    $: activeTab = tabs.find(t => t.id === activeTabId);
    $: isDropTarget = $tabDropTarget === id;

    const dispatch = createEventDispatcher();
    let settings;
    desktopSettings.subscribe(value => settings = value);

    let isDragging = false, isResizing = false;
    let dragOffsetX, dragOffsetY;
    let resizeDirection = '', initialResizeState = {};
    let focusTimeout = null;
    let showOptionsMenu = false;
    let optionsButton;
    let componentInstance;
    let contentAreaEl;
    let showGenericSettingsModal = false;
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };

    function openSettings() {
        showOptionsMenu = false;
        const componentsWithCustomSettings = ['IoskConsole', 'IoskFileExplorer', 'WebBrowser', 'Settings'];
        if (componentsWithCustomSettings.includes(activeTab.componentName) && componentInstance?.showSettingsDialog) {
            componentInstance.showSettingsDialog();
        } else {
            const currentSettings = get(windowSettings)[activeTab.componentName] || { positioning: 'auto' };
            windowSettingsForModal = {
                positioning: currentSettings.positioning || 'auto',
                x: currentSettings.x ?? x, y: currentSettings.y ?? y,
                width: currentSettings.width ?? width, height: currentSettings.height ?? height,
            };
            showGenericSettingsModal = true;
        }
    }

    function saveGenericWindowSettings() {
        windowSettings.update(all => ({ ...all, [activeTab.componentName]: windowSettingsForModal }));
        showGenericSettingsModal = false;
    }

    function handleWindowClick(event) {
        if (showOptionsMenu && optionsButton && !optionsButton.contains(event.target) && !event.target.closest('.options-menu')) {
            showOptionsMenu = false;
        }
    }

    onMount(() => window.addEventListener('click', handleWindowClick));
    onDestroy(() => window.removeEventListener('click', handleWindowClick));

    function handleConnect() { componentInstance?.connect?.(); showOptionsMenu = false; }
    function handleDisconnect() { componentInstance?.disconnect?.(); showOptionsMenu = false; }

    async function restoreFocus() {
        if (activeTab?.lastFocusedElement && document.body.contains(activeTab.lastFocusedElement)) {
            await tick();
            activeTab.lastFocusedElement.focus({ preventScroll: true });
        }
    }

    function handleFocusOut(event) {
        if (contentAreaEl && !contentAreaEl.contains(event.relatedTarget) && contentAreaEl.contains(event.target)) {
            windows.updateTabProps(activeTab.id, { lastFocusedElement: event.target });
        }
    }

    $: if (isActive) Promise.resolve().then(restoreFocus);

    function onDragStart(event) {
        if (event.target.closest('.window-control, .tab-button') || maximized) return;
        isDragging = true;
        dragOffsetX = event.clientX - x;
        dragOffsetY = event.clientY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd);
        windows.focusGroup(id);
    }

    function onDrag(event) {
        if (!isDragging) return;
        const newX = event.clientX - dragOffsetX;
        const newY = event.clientY - dragOffsetY;
        windows.updateGroupProps(id, { x: newX, y: newY });
        
        if (tabs.length === 1) {
            const elUnderCursor = document.elementFromPoint(event.clientX, event.clientY);
            const targetTitleBar = elUnderCursor?.closest('.title-bar[data-group-id]');
            const targetGroupId = targetTitleBar ? parseInt(targetTitleBar.dataset.groupId) : null;
            if (targetGroupId && targetGroupId !== id) {
                tabDropTarget.set(targetGroupId);
            } else {
                tabDropTarget.set(null);
            }
        }
    }

    function onDragEnd() {
        isDragging = false;
        window.removeEventListener('mousemove', onDrag);
        window.removeEventListener('mouseup', onDragEnd);
        
        const targetId = get(tabDropTarget);
        if (targetId) {
            windows.mergeTabs(tabs[0].id, targetId);
        }
        tabDropTarget.set(null);
        restoreFocus();
    }
    
    function onResizeStart(event) {
        if (maximized) return;
        let direction = event.target.classList.contains('resize-handle') ? 'se' : '';
        if (!direction) return;
        isResizing = true;
        resizeDirection = direction;
        initialResizeState = { x, y, width, height, mouseX: event.clientX, mouseY: event.clientY };
        window.addEventListener('mousemove', onResize);
        window.addEventListener('mouseup', onResizeEnd);
        windows.focusGroup(id);
    }

    function onResize(event) {
        if (!isResizing) return;
        const { x: ix, y: iy, width: iw, height: ih, mouseX: startX, mouseY: startY } = initialResizeState;
        const dx = event.clientX - startX;
        const dy = event.clientY - startY;
        const minWidth = 350, minHeight = 150;
        let newWidth = Math.max(minWidth, iw + dx);
        let newHeight = Math.max(minHeight, ih + dy);
        windows.updateGroupProps(id, { width: newWidth, height: newHeight });
    }

    function onResizeEnd() {
        isResizing = false;
        window.removeEventListener('mousemove', onResize);
        window.removeEventListener('mouseup', onResizeEnd);
        restoreFocus();
    }
    
    function handleFrameMouseDown(event) {
        clearTimeout(focusTimeout);
        windows.focusGroup(id);
    }

    function handleMouseEnter() {
        if (settings?.focusFollowsMouse && !isActive) {
            focusTimeout = setTimeout(() => windows.focusGroup(id), settings.focusDelay);
        }
    }
    function handleMouseLeave() { clearTimeout(focusTimeout); }
</script>

<style>
    .window-frame { position: absolute; border: 1px solid var(--border-color); background-color: var(--window-bg); border-radius: 6px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); display: flex; flex-direction: column; min-width: 350px; min-height: 150px; transition: border-color 0.2s; }
    .window-frame:not(.active) { border-color: #7f8c8d; }
    .window-frame.minimized { display: none; }
    .window-frame.maximized { border-radius: 0; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; }
    .window-frame.maximized .resize-handle { display: none; }
    @keyframes flash-animation { 50% { border-color: #f39c12; box-shadow: 0 0 20px 5px rgba(243, 156, 18, 0.7); } }
    .window-frame.flashing { animation: flash-animation 0.5s ease-in-out; }
    
    .title-bar { height: 30px; background-color: var(--title-bar-bg); color: var(--title-bar-text); display: flex; justify-content: space-between; align-items: stretch; border-top-left-radius: 5px; border-top-right-radius: 5px; user-select: none; transition: background-color 0.2s; flex-shrink: 0; }
    .window-frame:not(.active) .title-bar { background-color: #7f8c8d; }
    .title-bar.drop-target { background-color: #27ae60; }

    .tabs-container { display: flex; flex-grow: 1; align-items: stretch; overflow: hidden; }
    .tab-button { background: transparent; border: none; color: var(--title-bar-text); padding: 0 10px; cursor: pointer; display: flex; align-items: center; gap: 8px; max-width: 180px; border-right: 1px solid var(--border-color); }
    .tab-button:not(.active) { background-color: rgba(0,0,0,0.2); }
    .tab-button.active { font-weight: bold; }
    .tab-button:hover:not(.active) { background-color: rgba(0,0,0,0.3); }
    .tab-title { flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; }
    .tab-close { font-size: 16px; width: 16px; height: 16px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    .tab-close:hover { background-color: #ff5f56; color: white; }
    .title-drag-area { flex-grow: 1; cursor: move; }

    .window-controls { display: flex; gap: 5px; align-items: center; padding: 0 8px; }
    .window-control { width: 14px; height: 14px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: rgba(0,0,0,0.6); font-weight: bold; border-radius: 50%; cursor: pointer; border: 1px solid rgba(0,0,0,0.2); line-height: 18px; }
    .close { background-color: #ff5f56; }
    .minimize { background-color: #ffbd2e; }
    .maximize { background-color: #27c93f; }
    .options-menu-button { background-color: #3498db; color: white; line-height: 0.8; }

    .content-area { flex-grow: 1; overflow: auto; padding: 5px; }
    .resize-handle { position: absolute; bottom: 0; right: 0; width: 12px; height: 12px; cursor: se-resize; }
    
    .options-menu { position: absolute; top: 35px; right: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 1000; display: flex; flex-direction: column; min-width: 150px; padding: 4px 0; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .menu-item.close-option { color: #e74c3c; }
    .menu-item.close-option:hover { background-color: #c0392b; color: white; }
    
    /* Generic Modal Styles */
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; }
</style>

<div class="window-frame" class:minimized class:maximized class:active class:flashing={activeTab?.isFlashing}
    style:left="{x}px" style:top="{y}px" style:width="{maximized ? null : width + 'px'}" style:height="{maximized ? null : height + 'px'}"
    style:z-index="{zIndex}" on:mousedown={handleFrameMouseDown} on:mouseenter={handleMouseEnter} on:mouseleave={handleMouseLeave}>
    <div class="title-bar" on:dblclick={() => windows.toggleMaximize(id)} data-group-id={id} class:drop-target={isDropTarget}>
        <div class="tabs-container">
            {#each tabs as tab (tab.id)}
                <button class="tab-button" class:active={tab.id === activeTabId} on:click={() => windows.setActiveTab(id, tab.id)} title={tab.title}>
                    <span class="tab-title">{tab.title}</span>
                    <span class="tab-close" on:click|stopPropagation={() => windows.removeTab(tab.id)}>&times;</span>
                </button>
            {/each}
        </div>
        <div class="title-drag-area" on:mousedown|stopPropagation={onDragStart}></div>
        <div class="window-controls">
            <div class="window-control minimize" title="Minimize" on:click={() => windows.toggleMinimize(id)} on:mousedown|stopPropagation>_</div>
            <div class="window-control maximize" title={maximized ? 'Restore' : 'Maximize'} on:click={() => windows.toggleMaximize(id)} on:mousedown|stopPropagation>
                {@html maximized ? '&#128470;' : '&#9632;'}
            </div>
            <div class="window-control options-menu-button" title="Options" bind:this={optionsButton} on:click|stopPropagation={() => showOptionsMenu = !showOptionsMenu}>≡</div>
        </div>
    </div>
    {#if showOptionsMenu}
        <div class="options-menu">
            <button class="menu-item" on:click={() => { windows.toggleMaximize(id); showOptionsMenu = false; }}>{maximized ? 'Restore' : 'Maximize'}</button>
            <button class="menu-item" on:click={openSettings}>Settings...</button>
            {#if activeTab.component === IoskConsole}
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={handleConnect} disabled={activeTab.isConsoleConnected}>Connect</button>
                <button class="menu-item" on:click={() => { newIoskFileExplorer(activeTab.id, activeTab.title); showOptionsMenu = false; }} disabled={!activeTab.isConsoleConnected}>Files...</button>
                <button class="menu-item" on:click={handleDisconnect} disabled={!activeTab.isConsoleConnected}>Disconnect</button>
            {/if}
            {#if activeTab.component === IoskFileViewer}
                 <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => componentInstance?.setMode('rendered')} disabled={!activeTab.canRender}>Rendered</button>
                <button class="menu-item" on:click={() => componentInstance?.setMode('raw')}>Raw</button>
            {/if}
            <div class="menu-separator"></div>
            <button class="menu-item" on:click={() => { windows.toggleMinimize(id); showOptionsMenu = false; }}>Minimize</button>
            <button class="menu-item close-option" on:click={() => { windows.removeTab(activeTabId); showOptionsMenu = false; }}>Close Tab</button>
        </div>
    {/if}
    <div class="content-area" bind:this={contentAreaEl} on:focusout={handleFocusOut}>
        {#if activeTab}
            <svelte:component bind:this={componentInstance} this={activeTab.component} {...activeTab} isActive={isActive && activeTab.id === activeTabId} />
        {/if}
    </div>
    <div class="resize-handle" on:mousedown|stopPropagation={onResizeStart}></div>

    {#if showGenericSettingsModal}
        <div class="modal-overlay" on:click|self={() => showGenericSettingsModal = false}>
            <div class="modal-content" on:click|stopPropagation>
                <h3>Window Settings: {activeTab.title}</h3>
                <fieldset>
                    <legend>Default Position & Size</legend>
                    <div class="radio-group">
                        <label><input type="radio" bind:group={windowSettingsForModal.positioning} value="auto"> Auto</label>
                        <label><input type="radio" bind:group={windowSettingsForModal.positioning} value="manual"> Manual</label>
                    </div>
                    {#if windowSettingsForModal.positioning === 'manual'}
                        <div class="form-grid">
                            <label>X: <input type="number" bind:value={windowSettingsForModal.x}></label>
                            <label>Y: <input type="number" bind:value={windowSettingsForModal.y}></label>
                            <label>Width: <input type="number" bind:value={windowSettingsForModal.width}></label>
                            <label>Height: <input type="number" bind:value={windowSettingsForModal.height}></label>
                        </div>
                    {/if}
                </fieldset>
                <div class="buttons">
                    <button on:click={() => showGenericSettingsModal = false}>Cancel</button>
                    <button class="save-button" on:click={saveGenericWindowSettings}>Save Defaults</button>
                </div>
            </div>
        </div>
    {/if}
</div>