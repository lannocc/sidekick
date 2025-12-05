<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import Desktop from './Desktop.svelte';
    import Taskbar from './Taskbar.svelte';
    import { windows } from './windows.js';
    import { dashActive, dashLayouts, dashCycleIndex, desktopSettings } from './desktop.js';
    import { get } from 'svelte/store';
    import { initializeLocalConnection } from './local.js';

    function generateBgStyle(bgSettings) {
        if (!bgSettings) return '';
        if (bgSettings.bgType === 'gradient') {
            return `linear-gradient(45deg, ${bgSettings.bgGradientStart} 0%, ${bgSettings.bgGradientEnd} 100%)`;
        } else if (bgSettings.bgType === 'color') {
            return bgSettings.bgColor;
        } else if (bgSettings.bgType === 'image' && bgSettings.bgImage) {
            let size = 'cover';
            let repeat = 'no-repeat';
            let position = 'center center';
            switch (bgSettings.bgImageDisplayMode) {
                case 'contain': size = 'contain'; break;
                case 'stretch': size = '100% 100%'; break;
                case 'tile': size = 'auto'; repeat = 'repeat'; position = '0 0'; break;
                case 'cover': default: break;
            }
            return `url('${bgSettings.bgImage}') ${position} / ${size} ${repeat}`;
        }
        return '';
    }

    $: cloakSettings = $desktopSettings.sky?.cloak;
    $: cloakStyle = cloakSettings ? generateBgStyle(cloakSettings) : '';
    $: cloakOpacity = cloakSettings?.opacity ?? 0;

    // Frame settings
    $: frameSettings = $desktopSettings.sky?.frame;
    $: frameStyle = frameSettings ? generateBgStyle(frameSettings) : '';
    $: frameOpacity = frameSettings?.opacity ?? 1;
    $: frameHeight = frameSettings?.height ?? 40;
    $: frameWidth = frameSettings?.width ?? 0;

    function handleKeyDown(e) {
        // Tab switching with Alt/Ctrl + Number
        const numericKey = parseInt(e.key, 10);
        if ((e.altKey || e.ctrlKey) && !e.metaKey && !isNaN(numericKey) && numericKey >= 1 && numericKey <= 9) {
            e.preventDefault();

            const allWindows = get(windows);
            const activeWindow = allWindows.find(w => w.isActive && !w.minimized);

            if (activeWindow && activeWindow.tabs.length > 1) {
                const tabIndex = numericKey - 1; // '1' corresponds to index 0

                // Check if the tab index is valid
                if (tabIndex < activeWindow.tabs.length) {
                    const tabToActivate = activeWindow.tabs[tabIndex];
                    windows.setActiveTab(activeWindow.id, tabToActivate.id);
                }
            }
        }

        // Close active tab/window with Alt/Ctrl + w
        if ((e.altKey || e.ctrlKey) && !e.metaKey && e.key.toLowerCase() === 'w') {
            e.preventDefault();
            const activeWindow = get(windows).find(w => w.isActive && !w.minimized);
            if (activeWindow) {
                windows.removeTab(activeWindow.id, activeWindow.activeTabId);
            }
        }

        // Check for Meta/Alt + ` or Meta/Alt + ~ (Shift + `)
        if ((e.metaKey || e.altKey) && (e.key === '`' || e.key === '~')) {
            e.preventDefault();

            // e.shiftKey is true for '~', false for '`'
            const forward = !e.shiftKey;
            windows.cycleWindow(forward);
        }

        // Dash layout cycling
        if ((e.metaKey || e.altKey) && e.key === 'Escape') {
            e.preventDefault();

            const layouts = get(dashLayouts);
            const isDashActive = get(dashActive);
            const forward = !e.shiftKey;

            if (layouts.length === 0) {
                dashActive.update(v => !v);
                dashCycleIndex.set(-1);
                return;
            }

            if (!isDashActive) {
                // Dash is closed, open it and set index to first/last
                dashActive.set(true);
                dashCycleIndex.set(forward ? 0 : layouts.length - 1);
            } else {
                // Dash is open, cycle to the next/prev layout
                dashCycleIndex.update(idx => {
                    let newIndex;
                    if (idx === -1) {
                        // Not currently cycling, start from beginning/end
                        newIndex = forward ? 0 : layouts.length - 1;
                    } else {
                        newIndex = idx + (forward ? 1 : -1);
                    }

                    if (forward && newIndex >= layouts.length) {
                        dashActive.set(false);
                        return -1; // Cycled past the end
                    } else if (!forward && newIndex < 0) {
                        dashActive.set(false);
                        return -1; // Cycled past the beginning
                    } else {
                        return newIndex;
                    }
                });
            }
        }
    }

    onMount(() => {
        initializeLocalConnection();
        window.addEventListener('keydown', handleKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', handleKeyDown);
    });
</script>

<style>
    .sk-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        width: 100vw;
    }
    .top-frame {
        position: relative;
        z-index: 20000;
        flex-shrink: 0;
    }
    .desktop-wrapper {
        flex-grow: 1;
        display: flex;
        overflow: hidden;
    }
    .desktop-area {
        flex-grow: 1;
        position: relative;
    }
    .side-frame, .bottom-frame {
        flex-shrink: 0;
    }
    .sky-cloak {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 30000;
        pointer-events: none;
        transition: opacity 0.3s ease-in-out;
    }
</style>

<div class="sky-cloak" style="opacity: {cloakOpacity}; background: {cloakStyle};"></div>

<div class="sk-container" on:contextmenu|preventDefault>
    <div class="top-frame" style="height: {frameHeight}px; background: {frameStyle}; opacity: {frameOpacity};">
        <Taskbar />
    </div>
    <div class="desktop-wrapper">
        <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
        <div class="desktop-area">
            <Desktop />
        </div>
        <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
    </div>
    <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
</div>

