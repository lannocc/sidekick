<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { windows, newSettings, dragRequest } from './windows.js';
    import Window from './Window.svelte';
    import { desktopSettings, dashActive, boxes, desktopView } from './desktop.js';
    import { updateDesktopSettings } from './local.js';
    import Box from './Box.svelte';
    import Dash from './Dash.svelte';
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import InstanceRegistrar from './InstanceRegistrar.svelte';
    import { connectionStatus } from './local.js';
    import { fade } from 'svelte/transition';

    let backgroundStyle = '';
    let componentInstances = {};

    // --- Context Menu State ---
    let contextMenu = {
        visible: false,
        x: 0,
        y: 0,
        sourceEvent: null,
    };
    
    // --- Focus Follows Mouse Logic ---
    let focusTimeoutDesktop = {};

    function handleContentMouseEnter(group) {
        const settings = get(desktopSettings);
        if (settings?.focusFollowsMouse && !group.isActive) {
            focusTimeoutDesktop[group.id] = setTimeout(() => {
                windows.setActiveWindow(group.id);
            }, settings.focusDelay);
        }
    }

    function handleContentMouseLeave(group) {
        if (focusTimeoutDesktop[group.id]) {
            clearTimeout(focusTimeoutDesktop[group.id]);
            delete focusTimeoutDesktop[group.id];
        }
    }

    function handleContentMouseDown(event, group) {
        if ((event.altKey || event.metaKey) && !group.maximized) {
            event.preventDefault();
            
            if (event.button === 0) { // Left click for move
                dragRequest.set({
                    id: group.id,
                    type: 'move',
                    direction: null,
                    clientX: event.clientX,
                    clientY: event.clientY,
                });
            } else if (event.button === 2) { // Right click for resize
                const relX = event.clientX - group.x;
                const relY = event.clientY - group.y;

                let yDir = '';
                if (relY < group.height / 3) yDir = 'n';
                else if (relY > (group.height * 2) / 3) yDir = 's';
                
                let xDir = '';
                if (relX < group.width / 3) xDir = 'w';
                else if (relX > (group.width * 2) / 3) xDir = 'e';

                const direction = yDir + xDir;
                
                if (direction) { // Only trigger resize if not in the center
                    dragRequest.set({
                        id: group.id,
                        type: 'resize',
                        direction: direction,
                        clientX: event.clientX,
                        clientY: event.clientY,
                    });
                }
            }

        } else if (!group.isActive) {
            windows.focusWindow(group.id);
        }
    }

    function handleContentWheel(event, tab) {
        if (event.ctrlKey || event.altKey) {
            event.preventDefault();
            const zoomStep = 0.1;
            const delta = event.deltaY < 0 ? zoomStep : -zoomStep;
            windows.changeTabZoom(tab.group.id, tab.id, delta);
        }
    }


    function handleRightClick(event) {
        // Prevent context menu if panning
        if (isPanning) return;
        if (get(dashActive)) return; // Don't show if dash is active

        contextMenu = {
            visible: true,
            x: event.clientX,
            y: event.clientY,
            sourceEvent: event,
        };
    }

    function closeContextMenu() {
        contextMenu.visible = false;
    }

    function openSettingsMenu() {
        closeContextMenu();
        newSettings({ sourceEvent: contextMenu.sourceEvent });
    }

    function handleFocusOut(event, tab) {
        const contentAreaEl = event.currentTarget;
        if (contentAreaEl && !contentAreaEl.contains(event.relatedTarget)) {
            windows.updateTabProps(tab.group.id, tab.id, { lastFocusedElement: event.target });
        }
    }
    
    // --- View Controls State & Logic ---
    let controlsVisible = false;
    let controlsTimeout;

    function showControls() {
        controlsVisible = true;
        if (controlsTimeout) clearTimeout(controlsTimeout);
        controlsTimeout = setTimeout(() => {
            controlsVisible = false;
        }, 3000); // Linger for 3 seconds
    }

    const panStep = 50;
    const zoomStepButton = 0.2;
    const minZoom = 0.2;
    const maxZoom = 3.0;

    function pan(dx, dy) {
        showControls();
        desktopView.update(view => ({
            ...view,
            panX: view.panX + dx,
            panY: view.panY + dy,
        }));
        updateDesktopSettings(get(desktopView));
    }

    function zoom(direction) { // 1 for in, -1 for out
        showControls();
        desktopView.update(view => {
            const newZoom = Math.max(minZoom, Math.min(maxZoom, view.zoom + direction * zoomStepButton));
            if (newZoom === view.zoom) return view;

            // Zoom towards center of the screen
            const centerX = window.innerWidth / 2;
            const centerY = window.innerHeight / 2;

            const mouseWorldX = (centerX - view.panX) / view.zoom;
            const mouseWorldY = (centerY - view.panY) / view.zoom;
            
            const newPanX = centerX - mouseWorldX * newZoom;
            const newPanY = centerY - mouseWorldY * newZoom;

            return { zoom: newZoom, panX: newPanX, panY: newPanY };
        });
        updateDesktopSettings(get(desktopView));
    }

    function resetPan() {
        showControls();
        desktopView.update(v => ({ ...v, panX: 0, panY: 0 }));
        updateDesktopSettings(get(desktopView));
    }

    function resetZoom() {
        showControls();
        desktopView.update(view => {
            if (view.zoom === 1.0) return view;
            const newZoom = 1.0;
            
            const centerX = window.innerWidth / 2;
            const centerY = window.innerHeight / 2;

            const mouseWorldX = (centerX - view.panX) / view.zoom;
            const mouseWorldY = (centerY - view.panY) / view.zoom;
            
            const newPanX = centerX - mouseWorldX * newZoom;
            const newPanY = centerY - mouseWorldY * newZoom;

            return { zoom: newZoom, panX: newPanX, panY: newPanY };
        });
        updateDesktopSettings(get(desktopView));
    }


    // --- Pan and Zoom state ---
    let isPanning = false;
    let wasPanning = false;
    let lastMousePos = { x: 0, y: 0 };
    let saveViewTimeout;

    function handleDesktopMouseDown(event) {
        // Only pan if clicking on the desktop background itself and with the middle mouse button
        if (event.target !== event.currentTarget || event.button !== 1) return;
        
        isPanning = true;
        wasPanning = false;
        lastMousePos = { x: event.clientX, y: event.clientY };
        
        window.addEventListener('mousemove', handleDesktopMouseMove);
        window.addEventListener('mouseup', handleDesktopMouseUp, { once: true });
    }

    function handleDesktopMouseMove(event) {
        if (!isPanning) return;
        wasPanning = true; // If we move, it's a pan
        showControls();
        
        const dx = event.clientX - lastMousePos.x;
        const dy = event.clientY - lastMousePos.y;
        
        desktopView.update(view => ({
            ...view,
            panX: view.panX + dx,
            panY: view.panY + dy
        }));

        lastMousePos = { x: event.clientX, y: event.clientY };
    }

    function handleDesktopMouseUp() {
        if (isPanning && wasPanning) {
            // Persist final position if we actually panned
            updateDesktopSettings(get(desktopView));
        }
        isPanning = false;
        window.removeEventListener('mousemove', handleDesktopMouseMove);
    }
    
    function handleDesktopWheel(event) {
        // Only zoom if scrolling on the desktop background itself
        if (event.target !== event.currentTarget) return;
        
        event.preventDefault();
        showControls();

        const zoomFactor = 0.001;
        const minZoom = 0.2;
        const maxZoom = 3.0;

        const currentView = get(desktopView);
        const newZoom = Math.max(minZoom, Math.min(maxZoom, currentView.zoom - event.deltaY * zoomFactor));
        
        if (newZoom === currentView.zoom) return;

        const mouseX = event.clientX;
        const mouseY = event.clientY;

        // Position of the mouse in world coordinates before zoom
        const mouseWorldX = (mouseX - currentView.panX) / currentView.zoom;
        const mouseWorldY = (mouseY - currentView.panY) / currentView.zoom;

        // New pan to keep the world coordinate under the mouse
        const newPanX = mouseX - mouseWorldX * newZoom;
        const newPanY = mouseY - mouseWorldY * newZoom;
        
        desktopView.set({
            zoom: newZoom,
            panX: newPanX,
            panY: newPanY
        });

        // Debounce saving
        if (saveViewTimeout) clearTimeout(saveViewTimeout);
        saveViewTimeout = setTimeout(() => {
            updateDesktopSettings(get(desktopView));
        }, 300);
    }


    onMount(() => {
        // The WebSocket connection is now established in SideKick.svelte
        window.addEventListener('click', closeContextMenu);
    });
    onDestroy(() => {
        window.removeEventListener('click', closeContextMenu);
        Object.values(focusTimeoutDesktop).forEach(clearTimeout);
        if (saveViewTimeout) clearTimeout(saveViewTimeout);
        if (controlsTimeout) clearTimeout(controlsTimeout);
        window.removeEventListener('mousemove', handleDesktopMouseMove);
        window.removeEventListener('mouseup', handleDesktopMouseUp);
    });

    desktopSettings.subscribe(settings => {
        if (settings.bgType === 'gradient') {
            backgroundStyle = `linear-gradient(45deg, ${settings.bgGradientStart} 0%, ${settings.bgGradientEnd} 100%)`;
        } else if (settings.bgType === 'color') {
            backgroundStyle = settings.bgColor;
        } else if (settings.bgType === 'image' && settings.bgImage) {
            let size = 'cover';
            let repeat = 'no-repeat';
            let position = 'center center';

            switch (settings.bgImageDisplayMode) {
                case 'contain': // fit
                    size = 'contain';
                    break;
                case 'stretch':
                    size = '100% 100%';
                    break;
                case 'tile':
                    size = 'auto';
                    repeat = 'repeat';
                    position = '0 0'; // Tiling starts from top-left
                    break;
                case 'cover':
                default:
                    // 'cover' is the default case
                    break;
            }
            backgroundStyle = `url('${settings.bgImage}') ${position} / ${size} ${repeat}`;
        } else {
            // Fallback to default gradient
            backgroundStyle = `linear-gradient(45deg, #2c3e50 0%, #46627f 100%)`;
        }
    });
</script>

<style>
    .desktop {
        flex-grow: 1;
        position: relative;
        width: 100%;
        overflow: hidden;
        /* Default background color */
        background-color: var(--background-color);
        /* Dynamic background is applied via style attribute */
        background-position: center;
        transition: background 0.5s ease-in-out;
    }
    .desktop.dash-active .desktop-content {
        /* Hide windows without unmounting components, preserving their state */
        visibility: hidden;
    }
    .desktop::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: rgba(0,0,0,0.4);
        backdrop-filter: blur(5px);
        opacity: 0;
        transition: opacity 0.3s ease, backdrop-filter 0.3s ease;
        z-index: 50; /* Above background, below windows/dashboard */
        pointer-events: none;
    }
    .desktop.dash-active::before {
        opacity: 1;
    }
    .context-menu {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10001; /* Above Dash */
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
    
    .desktop-content {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        transform-origin: 0 0;
        pointer-events: none;
    }

    .boxes-layer {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none; /* Parent container is not interactive */
    }
    .boxes-layer > :global(*) {
        pointer-events: auto; /* Children (boxes) are interactive */
    }

    .windows-layer, .tab-contents-layer {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none;
    }

    .tab-content-wrapper {
        position: absolute;
        pointer-events: none;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid transparent; /* To align with window-frame border */
        border-radius: 6px;
        box-sizing: border-box;
    }
    .tab-content-wrapper.maximized {
        border-radius: 0;
    }
    .content-area-container {
        margin-top: 30px; /* title bar height */
        flex-grow: 1;
        overflow: auto;
        padding: 5px;
        pointer-events: auto;
        background-color: var(--window-bg);
    }

    /* --- View Controls --- */
    .view-controls {
        position: absolute;
        top: 20px;
        right: 20px;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        backdrop-filter: blur(5px);
        gap: 10px;
        border-radius: 8px;
        padding: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    .pan-controls {
        display: grid;
        grid-template-areas:
            ". up ."
            "left reset right"
            ". down .";
        gap: 4px;
    }
    .pan-up { grid-area: up; }
    .pan-left { grid-area: left; }
    .pan-reset { grid-area: reset; }
    .pan-right { grid-area: right; }
    .pan-down { grid-area: down; }

    .zoom-controls {
        display: flex;
        gap: 4px;
        justify-content: center;
    }

    .view-controls button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background-color: rgba(40, 40, 40, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        cursor: pointer;
        border-radius: 4px;
        font-size: 16px;
        font-weight: bold;
        line-height: 1;
        padding: 0;
        transition: background-color 0.2s;
    }
    .view-controls button:hover {
        background-color: rgba(255, 255, 255, 0.2);
    }
    .view-controls button:active {
        background-color: rgba(255, 255, 255, 0.3);
    }

    .zoom-controls .zoom-reset {
        width: auto;
        padding: 0 8px;
        font-size: 14px;
    }
</style>

<div class="desktop" class:dash-active={$dashActive} style:background={backgroundStyle} on:contextmenu|preventDefault={handleRightClick} on:mousedown={handleDesktopMouseDown} on:wheel={handleDesktopWheel}>

    <div class="desktop-content" style:transform="translate({$desktopView.panX}px, {$desktopView.panY}px) scale({$desktopView.zoom})">
        {#if $connectionStatus === 'connected'}
            <div class="boxes-layer">
                {#each $boxes as box (box.id)}
                    <Box {box} />
                {/each}
            </div>
        {/if}

        <div class="windows-layer">
            {#each $windows as win (win.id)}
                <Window {...win} />
            {/each}
        </div>

        <div class="tab-contents-layer">
            {#each $windows.flatMap(w => w.tabs.map(t => ({...t, group: w}))) as tab (tab.id)}
                {@const group = tab.group}
                <div
                    class="tab-content-wrapper"
                    class:maximized={group.maximized}
                    style:display={(tab.id === group.activeTabId && !group.minimized) ? 'flex' : 'none'}
                    style:left="{group.maximized ? `calc(-${$desktopView.panX}px / ${$desktopView.zoom})` : `${group.x}px`}"
                    style:top="{group.maximized ? `calc(-${$desktopView.panY}px / ${$desktopView.zoom})` : `${group.y}px`}"
                    style:width="{group.maximized ? `calc(100% / ${$desktopView.zoom})` : `${group.width}px`}"
                    style:height="{group.maximized ? `calc(100% / ${$desktopView.zoom})` : `${group.height}px`}"
                    style:z-index="{tab.isSettingsModalOpen ? group.zIndex + 1 : group.zIndex - 1}"
                    on:focusout={e => handleFocusOut(e, tab)}
                    on:contextmenu|preventDefault|stopPropagation
                >
                    <div
                        class="content-area-container"
                        on:mouseenter={() => handleContentMouseEnter(group)}
                        on:mouseleave={() => handleContentMouseLeave(group)}
                        on:mousedown={e => handleContentMouseDown(e, group)}
                        on:wheel={e => handleContentWheel(e, tab)}
                    >
                        <div style="height: 100%;" style:zoom={tab.zoom || 1.0}>
                            <svelte:component
                                bind:this={componentInstances[tab.id]}
                                this={tab.component}
                                {...tab}
                                groupId={group.id}
                                id={tab.id}
                                isActive={group.isActive && tab.id === group.activeTabId}
                                x={group.x} y={group.y} width={group.width} height={group.height}
                                maximized={group.maximized}
                            />
                            {#if componentInstances[tab.id]}
                                <InstanceRegistrar tabId={tab.id} instance={componentInstances[tab.id]} />
                            {/if}
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    </div>

    {#if controlsVisible}
        <div class="view-controls" transition:fade={{ duration: 142 }}>
            <div class="zoom-controls">
                <button on:click={() => zoom(-1)} title="Zoom Out">-</button>
                <button class="zoom-reset" on:click={resetZoom} title="Reset Zoom">1:1</button>
                <button on:click={() => zoom(1)} title="Zoom In">+</button>
            </div>
            <div class="pan-controls">
                <button class="pan-up" on:click={() => pan(0, panStep)} title="Pan Up">▲</button>
                <button class="pan-left" on:click={() => pan(panStep, 0)} title="Pan Left">◀</button>
                <button class="pan-reset" on:click={resetPan} title="Reset Pan">●</button>
                <button class="pan-right" on:click={() => pan(-panStep, 0)} title="Pan Right">▶</button>
                <button class="pan-down" on:click={() => pan(0, -panStep)} title="Pan Down">▼</button>
            </div>
        </div>
    {/if}

    {#if contextMenu.visible && !wasPanning}
        <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
            <button on:click={openSettingsMenu}>Settings...</button>
        </div>
    {/if}

    {#if $dashActive}
        <Dash />
    {/if}
</div>
