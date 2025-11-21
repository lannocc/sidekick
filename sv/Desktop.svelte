<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { windows, newSettings, dragRequest } from './windows.js';
    import Window from './Window.svelte';
    import { desktopSettings, dashActive } from './desktop.js';
    import Dash from './Dash.svelte';
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import InstanceRegistrar from './InstanceRegistrar.svelte';

    let backgroundStyle = '';
    let componentInstances = {};

    // --- Context Menu State ---
    let contextMenu = {
        visible: false,
        x: 0,
        y: 0,
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
        if (get(dashActive)) return; // Don't show if dash is active

        contextMenu = {
            visible: true,
            x: event.clientX,
            y: event.clientY,
        };
    }

    function closeContextMenu() {
        contextMenu.visible = false;
    }

    function openSettingsMenu() {
        closeContextMenu();
        newSettings();
    }

    function handleFocusOut(event, tab) {
        const contentAreaEl = event.currentTarget;
        if (contentAreaEl && !contentAreaEl.contains(event.relatedTarget)) {
            windows.updateTabProps(tab.group.id, tab.id, { lastFocusedElement: event.target });
        }
    }

    onMount(() => {
        window.addEventListener('click', closeContextMenu);
    });
    onDestroy(() => {
        window.removeEventListener('click', closeContextMenu);
        Object.values(focusTimeoutDesktop).forEach(clearTimeout);
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
    .desktop.dash-active .windows-layer,
    .desktop.dash-active .tab-contents-layer {
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

    .tab-contents-layer {
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
</style>

<div class="desktop" class:dash-active={$dashActive} style:background={backgroundStyle} on:contextmenu|preventDefault={handleRightClick}>
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
                style:left="{group.maximized ? 0 : group.x}px"
                style:top="{group.maximized ? 0 : group.y}px"
                style:width="{group.maximized ? '100%' : group.width + 'px'}"
                style:height="{group.maximized ? '100%' : group.height + 'px'}"
                style:z-index="{group.zIndex - 1}"
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

    {#if contextMenu.visible}
        <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
            <button on:click={openSettingsMenu}>Settings...</button>
        </div>
    {/if}

    {#if $dashActive}
        <Dash />
    {/if}
</div>
