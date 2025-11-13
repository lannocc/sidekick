<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher, tick, onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { windows, dragState, newIoskFileExplorer } from './windows.js';
    import { desktopSettings, windowSettings } from './desktopStore.js';
    import IoskConsole from './IoskConsole.svelte';
    import IoskFileExplorer from './IoskFileExplorer.svelte';
    import IoskFileViewer from './IoskFileViewer.svelte';
    import WebBrowser from './WebBrowser.svelte';
    import Settings from './Settings.svelte';

    // Group properties
    export let id;
    export let x;
    export let y;
    export let width;
    export let height;
    export let zIndex;
    export let minimized;
    export let maximized;
    export let isActive;
    export let isFlashing;
    export let tabs;
    export let activeTabId;

    $: activeTab = tabs.find(t => t.id === activeTabId) || tabs[0] || {};
    $: component = activeTab.component;
    $: componentName = activeTab.componentName;
    $: title = activeTab.title;
    $: isConsoleConnected = activeTab.isConsoleConnected;
    $: canRender = activeTab.canRender;

    $: componentProps = { ...activeTab, id: activeTab.id, isActive, x, y, width, height };

    const dispatch = createEventDispatcher();
    let settings;
    desktopSettings.subscribe(value => settings = value);

    let isDragging = false;
    let isResizing = false;
    let dragOffsetX, dragOffsetY;
    let resizeDirection = '';
    let initialResizeState = {};
    let focusTimeout = null;
    let showOptionsMenu = false;
    let optionsButton;
    let componentInstance;
    let contentAreaEl;
    let titleBarEl;

    let showGenericSettingsModal = false;
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };

    function openSettings() {
        showOptionsMenu = false;
        const componentsWithCustomSettings = ['IoskConsole', 'IoskFileExplorer', 'WebBrowser', 'Settings'];
        if (componentsWithCustomSettings.includes(componentName) && componentInstance && typeof componentInstance.showSettingsDialog === 'function') {
            componentInstance.showSettingsDialog();
        } else {
            const allSettings = get(windowSettings);
            const currentSettings = allSettings[componentName] || { positioning: 'auto' };
            windowSettingsForModal = {
                positioning: currentSettings.positioning || 'auto',
                x: currentSettings.x ?? x, y: currentSettings.y ?? y,
                width: currentSettings.width ?? width, height: currentSettings.height ?? height,
            };
            showGenericSettingsModal = true;
        }
    }

    function saveGenericWindowSettings() {
        windowSettings.update(allSettings => ({ ...allSettings, [componentName]: windowSettingsForModal }));
        showGenericSettingsModal = false;
    }

    function handleWindowClick(event) {
        if (showOptionsMenu && optionsButton && !optionsButton.contains(event.target) && !event.target.closest('.options-menu')) {
            showOptionsMenu = false;
        }
    }

    onMount(() => {
        window.addEventListener('click', handleWindowClick);
        titleBarEl.addEventListener('mouseenter', handleTitleMouseEnter);
        titleBarEl.addEventListener('mouseleave', handleTitleMouseLeave);
    });

    onDestroy(() => {
        window.removeEventListener('click', handleWindowClick);
        if (titleBarEl) {
            titleBarEl.removeEventListener('mouseenter', handleTitleMouseEnter);
            titleBarEl.removeEventListener('mouseleave', handleTitleMouseLeave);
        }
    });

    function handleConnect() {
        if (componentInstance && typeof componentInstance.connect === 'function') componentInstance.connect();
        showOptionsMenu = false;
    }

    function handleDisconnect() {
        if (componentInstance && typeof componentInstance.disconnect === 'function') componentInstance.disconnect();
        showOptionsMenu = false;
    }

    async function restoreFocus() {
        if (activeTab.lastFocusedElement && document.body.contains(activeTab.lastFocusedElement)) {
            await tick();
            activeTab.lastFocusedElement.focus({ preventScroll: true });
        }
    }

    function handleFocusOut(event) {
        if (contentAreaEl && !contentAreaEl.contains(event.relatedTarget) && contentAreaEl.contains(event.target)) {
            windows.updateTabProps(id, activeTabId, { lastFocusedElement: event.target });
        }
    }

    $: if (isActive) Promise.resolve().then(restoreFocus);

    function onDragStart(event) {
        if (event.target.closest('button') || event.target.closest('.window-control') || maximized) return;
        isDragging = true;
        dragState.set({ draggingGroupId: id, dropTargetGroupId: null });
        dragOffsetX = event.clientX - x;
        dragOffsetY = event.clientY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd, { once: true });
        if (event.altKey || event.metaKey) windows.setActiveWindow(id);
        else windows.focusWindow(id);
        document.body.style.cursor = 'move';
    }

    function onDrag(event) {
        if (!isDragging) return;
        x = event.clientX - dragOffsetX;
        y = event.clientY - dragOffsetY;
        windows.updateWindowProps(id, { x, y });
    }

    function onDragEnd() {
        isDragging = false;
        document.body.style.cursor = 'auto';
        window.removeEventListener('mousemove', onDrag);
        const currentDragState = get(dragState);
        if (currentDragState && currentDragState.dropTargetGroupId) {
            windows.groupWindows(currentDragState.draggingGroupId, currentDragState.dropTargetGroupId);
        }
        dragState.set(null);
        restoreFocus();
    }

    function handleTitleMouseEnter() {
        const currentDragState = get(dragState);
        if (currentDragState && currentDragState.draggingGroupId !== id) {
            dragState.update(s => ({ ...s, dropTargetGroupId: id }));
        }
    }
    
    function handleTitleMouseLeave() {
        const currentDragState = get(dragState);
        if (currentDragState && currentDragState.dropTargetGroupId === id) {
            dragState.update(s => ({ ...s, dropTargetGroupId: null }));
        }
    }

    function onResizeStart(event) {
        if (maximized) return;
        let direction = event.target.classList.contains('resize-handle') ? 'se' : '';
        if (!direction) return;

        isResizing = true;
        resizeDirection = direction;
        initialResizeState = { x, y, width, height, mouseX: event.clientX, mouseY: event.clientY };
        window.addEventListener('mousemove', onResize);
        window.addEventListener('mouseup', onResizeEnd, { once: true });
        if (event.altKey || event.metaKey) windows.setActiveWindow(id);
        else windows.focusWindow(id);
    }

    function onResize(event) {
        if (!isResizing) return;
        const { x: ix, y: iy, width: iw, height: ih, mouseX: startX, mouseY: startY } = initialResizeState;
        const dx = event.clientX - startX;
        const dy = event.clientY - startY;
        const minWidth = 250, minHeight = 150;

        let newWidth = iw, newHeight = ih;
        if (resizeDirection.includes('e')) newWidth = Math.max(minWidth, iw + dx);
        if (resizeDirection.includes('s')) newHeight = Math.max(minHeight, ih + dy);
        
        windows.updateWindowProps(id, { width: newWidth, height: newHeight });
    }

    function onResizeEnd() {
        isResizing = false;
        window.removeEventListener('mousemove', onResize);
        restoreFocus();
    }
    
    function handleFrameMouseDown(event) {
        clearTimeout(focusTimeout);
        if ((event.altKey || event.metaKey) && !maximized) {
            event.preventDefault();
            if (event.button === 0) onDragStart(event);
        } else {
            windows.focusWindow(id);
        }
    }

    function handleMouseEnter() {
        if (settings?.focusFollowsMouse && !isActive) {
            focusTimeout = setTimeout(() => windows.setActiveWindow(id), settings.focusDelay);
        }
    }

    function handleMouseLeave() { clearTimeout(focusTimeout); }
</script>

<style>
    @keyframes flash-animation {
        50% { border-color: #f39c12; box-shadow: 0 0 20px 5px rgba(243, 156, 18, 0.7); }
    }
    .window-frame.active.flashing, .window-frame:not(.active).flashing {
        animation: flash-animation 0.5s ease-in-out;
    }
    .window-frame { position: absolute; border: 1px solid var(--border-color); background-color: var(--window-bg); border-radius: 6px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); display: flex; flex-direction: column; min-width: 250px; min-height: 150px; transition: border-color 0.2s ease-in-out; }
    .window-frame:not(.active) { border-color: #7f8c8d; }
    .window-frame.minimized { display: none; }
    .window-frame.maximized { border-radius: 0; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; }
    .window-frame.maximized .resize-handle { display: none; }
    .title-bar { height: 30px; background-color: var(--title-bar-bg); color: var(--title-bar-text); display: flex; justify-content: space-between; align-items: center; padding: 0 8px; cursor: move; border-top-left-radius: 5px; border-top-right-radius: 5px; user-select: none; transition: background-color 0.2s ease-in-out; position: relative; }
    .window-frame:not(.active) .title-bar { background-color: #7f8c8d; }
    .title-bar.drop-target::after { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(52, 152, 219, 0.4); border: 2px dashed #3498db; z-index: 1; pointer-events: none; border-radius: 5px; }
    .title-center { flex-grow: 1; text-align: center; overflow: hidden; height: 100%; display: flex; align-items: flex-end; justify-content: center; }
    .title-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 30px; }
    .tabs-container { display: flex; height: 100%; }

    .tab { display: flex; align-items: center; background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; padding: 0 5px; margin-right: 2px; height: 26px; margin-top: auto; max-width: 150px; }
    .tab.active { background-color: var(--window-bg); }
    .tab-close-button { background: none; border: none; color: var(--taskbar-text); cursor: pointer; padding: 0 5px; font-size: 1.2em; line-height: 1; opacity: 0.7; }
    .tab-close-button:hover { color: #e74c3c; opacity: 1; }
    .tab-title { flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; padding: 0 5px; }
    .window-controls { display: flex; gap: 5px; z-index: 2; }
    .window-control { width: 14px; height: 14px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: rgba(0,0,0,0.6); font-weight: bold; border-radius: 50%; cursor: pointer; border: 1px solid rgba(0,0,0,0.2); line-height: 18px; }
    .close { background-color: #ff5f56; }
    .minimize { background-color: #ffbd2e; }
    .maximize { background-color: #27c93f; }
    .options-menu-button { background-color: #3498db; color: white; line-height: 0.8; }
    .content-area { flex-grow: 1; overflow: auto; padding: 5px; }
    .resize-handle { position: absolute; bottom: 0; right: 0; width: 12px; height: 12px; cursor: se-resize; }
    .options-menu { position: absolute; top: 35px; right: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 1000; display: flex; flex-direction: column; min-width: 150px; padding: 4px 0; user-select: none; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; }
    .menu-item.close-option { color: #e74c3c; }
    .menu-item.close-option:hover:not(:disabled) { background-color: #c0392b; color: white; }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding-left: 20px; }
    .form-grid label { display: flex; align-items: center; gap: 5px; }
    .form-grid input { width: 80px; background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 5px; border-radius: 3px; }
    .radio-group label { display: inline-flex; align-items: center; gap: 5px; margin-right: 15px; }
</style>

<div class="window-frame" class:minimized class:maximized class:active={isActive} class:flashing={isFlashing} style:left="{x}px" style:top="{y}px" style:width="{maximized ? null : width + 'px'}" style:height="{maximized ? null : height + 'px'}" style:z-index="{zIndex}" on:mousedown={handleFrameMouseDown} on:mouseenter={handleMouseEnter} on:mouseleave={handleMouseLeave} style:pointer-events={isDragging ? 'none' : 'auto'}>
    <div class="title-bar" bind:this={titleBarEl} class:drop-target={$dragState?.dropTargetGroupId === id && $dragState?.draggingGroupId !== id} on:mousedown={onDragStart} on:dblclick={() => windows.toggleMaximize(id)}>
        <div class="window-controls">
            <div class="window-control close" title="Close" on:click={() => windows.removeWindow(id)} on:mousedown|stopPropagation>&times;</div>
            <div class="window-control minimize" title="Minimize" on:click={() => windows.toggleMinimize(id)} on:mousedown|stopPropagation>_</div>
        </div>
        
        <div class="title-center">
            {#if tabs.length > 1}
                <div class="tabs-container">
                    {#each tabs as tab (tab.id)}
                        <div class="tab" class:active={tab.id === activeTabId}>
                            <button class="tab-close-button" title="Close Tab" on:click|stopPropagation={() => windows.removeTab(id, tab.id)}>&times;</button>
                            <span class="tab-title" title={tab.title} on:click|stopPropagation={() => windows.setActiveTab(id, tab.id)}>{tab.title}</span>
                        </div>
                    {/each}
                </div>
            {:else}
                <span class="title-text">{title}</span>
            {/if}
        </div>
        
        <div class="window-controls">
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
            {#if component === IoskConsole}
                <button class="menu-item" on:click={handleConnect} disabled={isConsoleConnected}>Connect</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => { if (componentInstance?.toggleAttachMenu) componentInstance.toggleAttachMenu(); showOptionsMenu = false; }} disabled={!isConsoleConnected}>Attach</button>
                <button class="menu-item" on:click={() => { newIoskFileExplorer(activeTab.id, title); showOptionsMenu = false; }} disabled={!isConsoleConnected}>Files...</button>
                <button class="menu-item" on:click={() => { if (componentInstance?.toggleRoomsMenu) componentInstance.toggleRoomsMenu(); showOptionsMenu = false; }} disabled={!isConsoleConnected}>Rooms</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={handleDisconnect} disabled={!isConsoleConnected}>Disconnect</button>
            {/if}
            {#if component === IoskFileViewer}
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => { if (componentInstance?.setMode) componentInstance.setMode('rendered'); showOptionsMenu = false; }} disabled={!canRender}>Rendered</button>
                <button class="menu-item" on:click={() => { if (componentInstance?.setMode) componentInstance.setMode('raw'); showOptionsMenu = false; }}>Raw</button>
            {/if}
            <div class="menu-separator"></div>
            <button class="menu-item" on:click={() => { windows.toggleMinimize(id); showOptionsMenu = false; }}>Minimize</button>
            <button class="menu-item close-option" on:click={() => { showOptionsMenu = false; windows.removeWindow(id); }}>Close</button>
        </div>
    {/if}
    <div class="content-area" bind:this={contentAreaEl} on:focusout={handleFocusOut}>
        <svelte:component bind:this={componentInstance} this={component} {...componentProps} />
    </div>
    <div class="resize-handle" on:mousedown|stopPropagation={onResizeStart}></div>

    {#if showGenericSettingsModal}
        <div class="modal-overlay" on:click|self={() => showGenericSettingsModal = false}>
            <div class="modal-content" on:click|stopPropagation>
                <h3>Window Settings: {title}</h3>
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
