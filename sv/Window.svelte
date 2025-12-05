<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher, tick, onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { windows, dragState, instanceRegistry, dragRequest, generateBoardConfigFromWindow } from './windows.js';
    import { desktopSettings, windowSettings, windowView, TASKBAR_HEIGHT, desktopInteraction } from './desktop.js';
    import { savePanelConfig } from './local.js';
    import IoskConsole from './IoskConsole.svelte';
    import IoskFileExplorer from './IoskFileExplorer.svelte';
    import IoskFileViewer from './IoskFileViewer.svelte';
    import WebBrowser from './WebBrowser.svelte';
    import Settings from './Settings.svelte';
    import Calculator from './Calculator.svelte';
    import IoskPrivateChat from './IoskPrivateChat.svelte';
    import LocalTerminal from './LocalTerminal.svelte';
    import LocalFileExplorer from './LocalFileExplorer.svelte';
    import Ask from './Ask.svelte';
    import IoskWatch from './IoskWatch.svelte';
    import IoskUserInspector from './IoskUserInspector.svelte';
    import NotificationCenter from './NotificationCenter.svelte';
    import WindowSettingsModal from './popup/WindowSettingsModal.svelte';
    import InstanceRegistrar from './InstanceRegistrar.svelte';

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
    export let notice;
    export let tabs;
    export let activeTabId;
    export let cloaked;

    $: activeTab = tabs.find(t => t.id === activeTabId) || tabs[0] || {};
    $: component = activeTab.component;
    $: componentName = activeTab.componentName;
    $: title = activeTab.title;
    $: isConsoleConnected = activeTab.isConsoleConnected;
    $: canRender = activeTab.canRender;

    const dispatch = createEventDispatcher();
    let settings;
    desktopSettings.subscribe(value => settings = value);

    function generateBgStyle(bgSettings) {
        if (!bgSettings) return null;
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
        return null;
    }

    $: state = isActive ? 'active' : 'inactive';
    $: frameSettings = settings?.windows?.normal?.frame?.[state];
    $: frameStyle = generateBgStyle(frameSettings);
    $: frameHeight = frameSettings?.height ?? 30;
    $: frameWidth = frameSettings?.width ?? 0;
    $: frameOpacity = frameSettings?.opacity ?? 1.0;
    $: boxShadowStyle = cloaked ? 'none' : (frameSettings?.shadowEnabled
        ? `${frameSettings.shadowInset ? 'inset ' : ''}${frameSettings.shadowX}px ${frameSettings.shadowY}px ${frameSettings.shadowBlur}px ${frameSettings.shadowSpread}px ${frameSettings.shadowColor}`
        : 'none');

    $: sceneSettings = settings?.windows?.normal?.scene?.[state];

    $: cloakSettings = settings?.windows?.normal?.cloak?.[state];
    $: cloakStyle = generateBgStyle(cloakSettings);
    $: cloakOpacity = cloaked ? (cloakSettings?.opacity ?? 0.8) : 0;

    let isDragging = false;
    let isResizing = false;
    let dragOffsetX, dragOffsetY;
    let resizeDirection = '';
    let initialResizeState = {};
    let focusFollowsMouseTimeout = null;
    let showOptionsMenu = false;
    let optionsButton;
    let tabsContainerEl;
    let titleBarEl;
    let middleClickTimeout;

    // --- Content Area Logic (Moved from Desktop.svelte) ---
    let componentInstances = {};
    function handleContentMouseDown(event) {
        if (event.button === 1 && !maximized) {
            handleMiddleClick(event);
            event.stopPropagation();
            return;
        }

        if (event.ctrlKey && event.button === 1) { // Ctrl + Middle click
            event.preventDefault();
            event.stopPropagation();
            dispatch('backrequest');
            return;
        }

        if ((event.altKey || event.metaKey) && !maximized) {
            if (event.button === 0) { // Left click for move
                dragRequest.set({ id, type: 'move', direction: null, clientX: event.clientX, clientY: event.clientY });
            } else if (event.button === 2) { // Right click for resize
                const relX = event.clientX - x;
                const relY = event.clientY - y;
                let yDir = relY < height / 3 ? 'n' : (relY > (height * 2) / 3 ? 's' : '');
                let xDir = relX < width / 3 ? 'w' : (relX > (width * 2) / 3 ? 'e' : '');
                const direction = yDir + xDir;
                if (direction) {
                    dragRequest.set({ id, type: 'resize', direction: direction, clientX: event.clientX, clientY: event.clientY });
                }
            }
        } else if (!isActive) {
            windows.focusWindow(id);
        }
    }
    function handleContentWheel(event, tab) {
        if (event.ctrlKey || event.altKey) {
            event.preventDefault();
            const zoomStep = 0.1;
            const delta = event.deltaY < 0 ? zoomStep : -zoomStep;
            windows.changeTabZoom(id, tab.id, delta);
        }
    }
    function handleFocusOut(event, tab) {
        const contentAreaEl = event.currentTarget;
        if (contentAreaEl && !contentAreaEl.contains(event.relatedTarget)) {
            windows.updateTabProps(id, tab.id, { lastFocusedElement: event.target });
        }
    }

    // React to drag/resize requests from other components (like Desktop's content area)
    $: if ($dragRequest && $dragRequest.id === id) {
        const request = $dragRequest;
        dragRequest.set(null); // Consume the request

        // Create a mock event to pass to the existing drag/resize handlers
        const mockEvent = {
            clientX: request.clientX,
            clientY: request.clientY,
            target: titleBarEl, // Use titleBar as a plausible target
            preventDefault: () => {},
            button: request.type === 'move' ? 0 : 2,
        };

        if (request.type === 'move') {
            onDragStart(mockEvent);
        } else if (request.type === 'resize') {
            onResizeStart(mockEvent, request.direction);
        }
    }

    let showGenericSettingsModal = false;

    function openSettings() {
        showOptionsMenu = false;
        const instance = instanceRegistry.get(activeTabId);
        const componentsWithCustomSettings = ['IoskConsole', 'IoskFileExplorer', 'WebBrowser', 'Settings'];
        if (componentsWithCustomSettings.includes(componentName) && instance && typeof instance.showSettingsDialog === 'function') {
            instance.showSettingsDialog();
        } else {
            showGenericSettingsModal = true;
        }
    }

    function handleWindowClick(event) {
        if (showOptionsMenu && optionsButton && !optionsButton.contains(event.target) && !event.target.closest('.options-menu')) {
            showOptionsMenu = false;
        }
    }

    onMount(() => {
        window.addEventListener('click', handleWindowClick);
    });

    onDestroy(() => {
        window.removeEventListener('click', handleWindowClick);
        if (focusFollowsMouseTimeout) clearTimeout(focusFollowsMouseTimeout);
        if (middleClickTimeout) clearTimeout(middleClickTimeout);
    });

    function handleConnect() {
        const instance = instanceRegistry.get(activeTabId);
        if (instance && typeof instance.connect === 'function') instance.connect();
        showOptionsMenu = false;
    }

    function handleDisconnect() {
        const instance = instanceRegistry.get(activeTabId);
        if (instance && typeof instance.disconnect === 'function') instance.disconnect();
        showOptionsMenu = false;
    }

    // --- Tab Dragging Logic ---
    let isTabDragging = false;
    let draggedTabInfo = null;
    let dropIndicator = { visible: false, left: 0 };
    let tabDragHasMoved = false;

    function onTabMouseDown(e, tab) {
        if (e.button !== 0 || maximized) return; // Only left click, no dragging when maximized
        e.stopPropagation();

        isTabDragging = true;
        tabDragHasMoved = false;
        draggedTabInfo = {
            groupId: id,
            tabId: tab.id,
        };

        window.addEventListener('mousemove', onTabMouseMove);
        window.addEventListener('mouseup', onTabMouseUp, { once: true });
    }

    function onTabMouseMove(e) {
        if (!isTabDragging) return;

        tabDragHasMoved = true;

        const { top, bottom, left: containerLeft } = tabsContainerEl.getBoundingClientRect();
        const isOutsideY = e.clientY < top - 20 || e.clientY > bottom + 20;

        if (isOutsideY && tabs.length > 1) {
            draggedTabInfo.isDetaching = true;
            dropIndicator.visible = false;
            document.body.style.cursor = 'copy';
        } else {
            draggedTabInfo.isDetaching = false;
            document.body.style.cursor = 'default';

            dropIndicator.visible = false;
            let targetTabId = null;

            // Iterate over sibling tabs to find drop position
            for (const child of tabsContainerEl.children) {
                if (!child.classList.contains('tab') || child.dataset.tabId == draggedTabInfo.tabId) continue;

                const rect = child.getBoundingClientRect();
                const midpoint = rect.left + rect.width / 2;

                if (e.clientX < midpoint) {
                    targetTabId = child.dataset.tabId;
                    dropIndicator.left = rect.left - containerLeft;
                    dropIndicator.visible = true;
                    break;
                }
            }

            // If no target found, it means it's at the end
            if (!dropIndicator.visible) {
                const lastChild = tabsContainerEl.querySelector('.tab:last-of-type');
                if (lastChild) {
                    const rect = lastChild.getBoundingClientRect();
                    dropIndicator.left = rect.right - containerLeft;
                    dropIndicator.visible = true;
                }
                targetTabId = null; // Signal to append at the end
            }

            draggedTabInfo.targetTabId = targetTabId;
        }
    }

    function onTabMouseUp(e) {
        window.removeEventListener('mousemove', onTabMouseMove);
        document.body.style.cursor = 'auto';

        if (isTabDragging) {
            if (draggedTabInfo.isDetaching) {
                windows.detachTabToNewWindow(draggedTabInfo.groupId, draggedTabInfo.tabId, e.clientX - 100, e.clientY - 15);
            } else if (tabDragHasMoved) {
                windows.reorderTab(draggedTabInfo.groupId, draggedTabInfo.tabId, draggedTabInfo.targetTabId);
            }
        }
        isTabDragging = false;
        draggedTabInfo = null;
        dropIndicator.visible = false;
        tabDragHasMoved = false;
    }

    async function restoreFocus() {
        if (activeTab.lastFocusedElement && document.body.contains(activeTab.lastFocusedElement)) {
            await tick();
            activeTab.lastFocusedElement.focus({ preventScroll: true });
        }
    }

    $: if (isActive) Promise.resolve().then(restoreFocus);

    function onDragStart(event) {
        isDragging = true;
        dragState.set({ draggingGroupId: id, dropTargetGroupId: null, dropTargetBoxPanel: null });

        const { panX, panY, zoom } = get(windowView);
        const worldMouseX = (event.clientX - panX) / zoom;
        const worldMouseY = ((event.clientY - TASKBAR_HEIGHT) - panY) / zoom;

        dragOffsetX = worldMouseX - x;
        dragOffsetY = worldMouseY - y;
        
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd, { once: true });
        windows.focusWindow(id);
        document.body.style.cursor = 'move';
    }

    function onDrag(event) {
        if (!isDragging) return;
        
        const { panX, panY, zoom } = get(windowView);
        const worldMouseX = (event.clientX - panX) / zoom;
        const worldMouseY = ((event.clientY - TASKBAR_HEIGHT) - panY) / zoom;

        const newX = worldMouseX - dragOffsetX;
        const newY = worldMouseY - dragOffsetY;

        windows.updateWindowProps(id, { x: newX, y: newY });

        // Drop target detection logic
        titleBarEl.style.pointerEvents = 'none';
        const elementUnder = document.elementFromPoint(event.clientX, event.clientY);
        titleBarEl.style.pointerEvents = 'auto';

        const targetTitleBar = elementUnder?.closest('.title-bar');
        const targetId = targetTitleBar ? parseInt(targetTitleBar.dataset.groupId, 10) : null;
        
        if (targetId && targetId !== id) {
            dragState.update(s => ({ ...s, dropTargetGroupId: targetId, dropTargetBoxPanel: null }));
        } else {
             // Let Box.svelte handle setting dropTargetBoxPanel via its mouseenter events
            dragState.update(s => ({ ...s, dropTargetGroupId: null }));
        }
    }

    function onDragEnd() {
        isDragging = false;
        document.body.style.cursor = 'auto';
        window.removeEventListener('mousemove', onDrag);
        const currentDragState = get(dragState);
        if (currentDragState) {
            if (currentDragState.dropTargetGroupId) {
                windows.groupWindows(currentDragState.draggingGroupId, currentDragState.dropTargetGroupId);
            } else if (currentDragState.dropTargetBoxPanel) {
                const { boxId, location } = currentDragState.dropTargetBoxPanel;
                const allWindows = get(windows);
                const sourceGroup = allWindows.find(g => g.id === currentDragState.draggingGroupId);
                if (sourceGroup) {
                    const board_config = generateBoardConfigFromWindow(sourceGroup, allWindows);
                    const board_type = sourceGroup.tabs.length > 1 ? 'tabs' : 'window';
                    savePanelConfig(boxId, location, board_type, board_config);
                    // Move the window to the box by removing it from the desktop
                    windows.removeWindow(currentDragState.draggingGroupId);
                }
            }
        }
        dragState.set(null);
        restoreFocus();
    }

    function onResizeStart(event, directionOverride = '') {
        if (maximized) return;
        let direction = directionOverride || (event.target.classList.contains('resize-handle') ? 'se' : '');
        if (!direction) return;

        isResizing = true;
        resizeDirection = direction;
        initialResizeState = { x, y, width, height, mouseX: event.clientX, mouseY: event.clientY };
        window.addEventListener('mousemove', onResize);
        window.addEventListener('mouseup', onResizeEnd, { once: true });
        windows.focusWindow(id);
    }

    function onResize(event) {
        if (!isResizing) return;
        const { x: ix, y: iy, width: iw, height: ih, mouseX: startX, mouseY: startY } = initialResizeState;

        const { zoom } = get(windowView);
        const dx = (event.clientX - startX) / zoom;
        const dy = (event.clientY - startY) / zoom;
        const minWidth = 250, minHeight = 150;

        let newX = ix;
        let newY = iy;
        let newWidth = iw;
        let newHeight = ih;

        // Handle horizontal resizing
        if (resizeDirection.includes('e')) {
            newWidth = iw + dx;
        } else if (resizeDirection.includes('w')) {
            newWidth = iw - dx;
            newX = ix + dx;
        }

        // Handle vertical resizing
        if (resizeDirection.includes('s')) {
            newHeight = ih + dy;
        } else if (resizeDirection.includes('n')) {
            newHeight = ih - dy;
            newY = iy + dy;
        }

        // Enforce minimum size and adjust position accordingly
        if (newWidth < minWidth) {
            if (resizeDirection.includes('w')) {
                newX -= minWidth - newWidth;
            }
            newWidth = minWidth;
        }

        if (newHeight < minHeight) {
            if (resizeDirection.includes('n')) {
                newY -= minHeight - newHeight;
            }
            newHeight = minHeight;
        }

        windows.updateWindowProps(id, { x: newX, y: newY, width: newWidth, height: newHeight });
    }

    function onResizeEnd() {
        isResizing = false;
        window.removeEventListener('mousemove', onResize);
        restoreFocus();
    }

    function handleMiddleClick(event) {
        if (event.button !== 1) return;
        event.preventDefault();

        // Double-click detection
        if (middleClickTimeout) {
            clearTimeout(middleClickTimeout);
            middleClickTimeout = null;
            windows.toggleCloak(id);
            return;
        }
        
        // Set a timeout to clear the double-click state. If another click
        // arrives before this, it's a double-click.
        middleClickTimeout = setTimeout(() => {
            middleClickTimeout = null;
        }, 250);

        // Drag detection: if the mouse moves, cancel the double-click timer and start dragging.
        const onMove = () => {
            clearTimeout(middleClickTimeout);
            middleClickTimeout = null;
            if (event.target.closest('.content-area-container')) {
                dragRequest.set({ id, type: 'move', direction: null, clientX: event.clientX, clientY: event.clientY });
            } else {
                onDragStart(event);
            }
        };

        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
        };

        window.addEventListener('mousemove', onMove, { once: true });
        window.addEventListener('mouseup', onUp, { once: true });
    }

    function handleFrameMouseDown(event) {
        if (event.button === 1 && !maximized) {
            if (event.ctrlKey) {
                event.preventDefault();
                event.stopPropagation();
                dispatch('backrequest');
                return;
            }
            handleMiddleClick(event);
            event.stopPropagation();
            return;
        }
        
        clearTimeout(focusFollowsMouseTimeout);

        if ((event.altKey || event.metaKey) && !maximized) {
            event.preventDefault();
            if (event.button === 0) onDragStart(event);
            else if (event.button === 2) onResizeStart(event, 'se');
        } else if (event.button === 0 && cloaked && !maximized) { // Left-click to move when cloaked
            event.preventDefault();
            onDragStart(event);
        } else {
            windows.focusWindow(id);
        }
    }

    function handleTitleBarMouseDown(event) {
        // Prevent action if clicking on controls, tabs, etc.
        if (event.target.closest('button') || event.target.closest('.window-control') || event.target.closest('.tab')) {
            if (!isActive) windows.focusWindow(id);
            return;
        }
        
        if (event.button === 1 && !maximized) {
            if (event.ctrlKey) {
                event.preventDefault();
                event.stopPropagation();
                dispatch('backrequest');
                return;
            }
            handleMiddleClick(event);
            event.stopPropagation();
            return;
        }

        if (maximized) {
             if (!isActive) windows.focusWindow(id);
            return;
        }

        clearTimeout(focusFollowsMouseTimeout);

        // Alt/Meta key combinations for move/resize
        if (event.altKey || event.metaKey) {
            event.preventDefault();
            if (event.button === 0) { // Left click: Move
                onDragStart(event);
            } else if (event.button === 2) { // Right click: Resize
                onResizeStart(event, 'se');
            }
        } else if (event.button === 0) {
            // Standard left click: Move
            onDragStart(event);
        }
    }

    function handleMouseEnter() {
        if (settings?.focusFollowsMouse && !isActive) {
            focusFollowsMouseTimeout = setTimeout(() => windows.setActiveWindow(id), settings.focusDelay);
        }
    }

    function handleMouseLeave() { clearTimeout(focusFollowsMouseTimeout); }
</script>

<style>
    @keyframes notice-glow {
        50% { border-color: var(--notice-color); box-shadow: 0 0 20px 5px var(--notice-color), var(--original-shadow, 0 5px 15px rgba(0,0,0,0.3)); }
    }
    .window-frame.noticing {
        animation: notice-glow 1.2s ease-in-out;
        --original-shadow: var(--box-shadow);
    }
    .window-frame {
        position: absolute;
        border: 1px solid var(--border-color);
        background-color: transparent;
        border-radius: 6px;
        display: flex;
        flex-direction: column;
        min-width: 250px;
        min-height: 150px;
        pointer-events: auto;
        box-sizing: border-box;
        /* --- ANIMATIONS --- */
        transition: border-color 0.3s ease-in-out, border-radius 0.3s ease-in-out, box-shadow 0.4s ease-in-out;
    }
    .window-frame.has-custom-frame {
        border: none;
    }
    .window-frame.cloaked {
        border-color: transparent !important;
        background-color: transparent;
    }
    .window-frame.cloaked > *:not(.cloak):not(.resize-handle) {
        visibility: hidden;
    }
    .window-frame:not(.active) { border-color: #7f8c8d; }
    .window-frame.minimized { display: none; }
    .window-frame.maximized { border-radius: 0; }
    .window-frame.maximized .resize-handle { display: none; }
    .title-bar {
        flex-shrink: 0;
        color: var(--title-bar-text);
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 8px;
        cursor: move;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        user-select: none;
        position: relative;
        pointer-events: auto;
        /* --- ANIMATIONS --- */
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out, height 0.3s ease-in-out;
    }
    .window-frame:not(.active) .title-bar { /* background-color: #7f8c8d; */ }
    .title-bar.drop-target::after { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(52, 152, 219, 0.4); border: 2px dashed #3498db; z-index: 1; pointer-events: none; border-radius: 5px; }
    .title-center { flex-grow: 1; text-align: center; overflow: hidden; height: 100%; display: flex; align-items: flex-end; justify-content: center; }
    .title-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 30px; }
    .tabs-container { position: relative; display: flex; }
    .tab { display: flex; align-items: center; background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; padding: 0 5px; margin-right: 2px; height: 26px; margin-top: auto; max-width: 150px; transition: opacity 0.2s, background-color 0.3s; }
    .tab.active {
        background-color: var(--window-bg);
        z-index: 1; /* Bring active tab forward */
    }
    .tab.dragging {
        opacity: 0.4;
    }
    .drop-indicator {
        position: absolute;
        top: 4px;
        bottom: 0px;
        width: 2px;
        background-color: #3498db;
        pointer-events: none;
    }
    .tab:not(.active) {
        opacity: 0.7;
    }
    .tab:not(.active):hover {
        opacity: 1;
    }
    .tab-close-button { background: none; border: none; color: var(--taskbar-text); cursor: pointer; padding: 0 5px; font-size: 1.2em; line-height: 1; opacity: 0.7; }
    .tab-close-button:hover { color: #e74c3c; opacity: 1; }
    .tab-title { flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; padding: 0 5px; }
    .tab.active .tab-title {
        font-weight: bold;
    }
    .window-controls { display: flex; gap: 5px; z-index: 2; }
    .window-control { --button-size: calc(var(--frame-height, 30px) * 0.45); width: var(--button-size); height: var(--button-size); display: flex; align-items: center; justify-content: center; font-size: var(--button-size); color: rgba(0,0,0,0.6); font-weight: bold; border-radius: 50%; cursor: pointer; border: 1px solid rgba(0,0,0,0.2); line-height: 1; }
    .close { background-color: #ff5f56; }
    .minimize { background-color: #ffbd2e; }
    .maximize { background-color: #27c93f; }
    .options-menu-button { background-color: #3498db; color: white; line-height: 0.8; }
    .middle-row {
        flex-grow: 1;
        display: flex;
        flex-direction: row;
        overflow: hidden; /* Prevent content from breaking out */
    }
    .content-area-wrapper {
        flex-grow: 1;
        position: relative;
        overflow: hidden;
    }
    .content-area-container {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        overflow: auto;
        padding: 5px;
        pointer-events: auto;
        box-sizing: border-box;
        /* --- ANIMATIONS --- */
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out;
    }
    .side-frame, .bottom-frame {
        flex-shrink: 0;
        pointer-events: auto;
        /* --- ANIMATIONS --- */
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out, width 0.3s ease-in-out, height 0.3s ease-in-out;
    }
    .cloak {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 5; /* Above content, below options menu */
        pointer-events: none;
        border-radius: 5px;
        /* --- ANIMATIONS --- */
        transition: opacity 0.3s ease-in-out, background 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .resize-handle {
        position: absolute;
        pointer-events: auto;
        z-index: 6;
    }
    .resize-handle.n { top: -4px; left: 8px; right: 8px; height: 8px; cursor: n-resize; }
    .resize-handle.s { bottom: -4px; left: 8px; right: 8px; height: 8px; cursor: s-resize; }
    .resize-handle.w { top: 8px; bottom: 8px; left: -4px; width: 8px; cursor: w-resize; }
    .resize-handle.e { top: 8px; bottom: 8px; right: -4px; width: 8px; cursor: e-resize; }
    .resize-handle.nw { top: -4px; left: -4px; width: 12px; height: 12px; cursor: nw-resize; }
    .resize-handle.ne { top: -4px; right: -4px; width: 12px; height: 12px; cursor: ne-resize; }
    .resize-handle.sw { bottom: -4px; left: -4px; width: 12px; height: 12px; cursor: sw-resize; }
    .resize-handle.se { bottom: -4px; right: -4px; width: 12px; height: 12px; cursor: se-resize; }
    .options-menu { position: absolute; top: 35px; right: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 1000; display: flex; flex-direction: column; min-width: 150px; padding: 4px 0; user-select: none; pointer-events: auto; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; }
    .menu-item.close-option { color: #e74c3c; }
    .menu-item.close-option:hover:not(:disabled) { background-color: #c0392b; color: white; }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; pointer-events: auto; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
    .radio-group label { display: inline-flex; align-items: center; gap: 5px; margin-right: 15px; }
    .select-input { background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 5px; border-radius: 3px; }
</style>

<div class="window-frame" class:minimized class:maximized class:active={isActive} class:noticing={!!notice} class:cloaked style:left="{x}px" style:top="{y}px" style:width="{width}px" style:height="{height}px" style:z-index="{zIndex}" style:box-shadow={boxShadowStyle} style:--box-shadow={boxShadowStyle} style:--notice-color={notice?.color} on:mousedown={handleFrameMouseDown} on:contextmenu|preventDefault|stopPropagation>
    <div class="title-bar" bind:this={titleBarEl} class:drop-target={$dragState?.dropTargetGroupId === id && $dragState?.draggingGroupId !== id} on:mousedown={handleTitleBarMouseDown} on:dblclick={() => windows.toggleMaximize(id)} on:mouseenter={handleMouseEnter} on:mouseleave={handleMouseLeave} data-group-id={id} style="height: {frameHeight}px; background: {frameStyle}; opacity: {frameOpacity}; --frame-height: {frameHeight}px;">
        <div class="window-controls" on:dblclick|stopPropagation on:mouseup|stopPropagation>
            <div class="window-control close" title="Close" on:click={() => windows.removeWindow(id)} on:mousedown|stopPropagation>&times;</div>
            <div class="window-control minimize" title="Minimize" on:click={() => windows.toggleMinimize(id)} on:mousedown|stopPropagation>_</div>
        </div>

        <div class="title-center">
            {#if tabs.length > 1}
                <div class="tabs-container" bind:this={tabsContainerEl} on:dblclick|stopPropagation>
                    {#each tabs as tab (tab.id)}
                        <div
                            class="tab"
                            class:active={tab.id === activeTabId}
                            class:dragging={isTabDragging && draggedTabInfo.tabId === tab.id}
                            data-tab-id={tab.id}
                            on:mousedown={e => onTabMouseDown(e, tab)}
                        >
                            <button class="tab-close-button" title="Close Tab" on:click|stopPropagation={() => windows.removeTab(id, tab.id)}>&times;</button>
                            <span class="tab-title" title={tab.title} on:click|stopPropagation={() => windows.setActiveTab(id, tab.id)}>{tab.title}</span>
                        </div>
                    {/each}
                    {#if dropIndicator.visible}
                        <div class="drop-indicator" style:left="{dropIndicator.left}px"></div>
                    {/if}
                </div>
            {:else}
                <span class="title-text">{title}</span>
            {/if}
        </div>

        <div class="window-controls" on:dblclick|stopPropagation on:mouseup|stopPropagation>
            <div class="window-control maximize" title={maximized ? 'Restore' : 'Maximize'} on:click={() => windows.toggleMaximize(id)} on:mousedown|stopPropagation>
                {@html maximized ? '&#128470;' : '&#9632;'}
            </div>
            <div class="window-control options-menu-button" title="Options" bind:this={optionsButton} on:click|stopPropagation={() => showOptionsMenu = !showOptionsMenu}>≡</div>
        </div>
    </div>
    <div class="middle-row">
        <div class="side-frame left" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};" on:mousedown={handleFrameMouseDown}></div>
        <div class="content-area-wrapper">
             {#each tabs as tab (tab.id)}
                <div
                    class="content-area-container"
                    style:display={tab.id === activeTabId && !minimized ? 'block' : 'none'}
                    style:pointer-events={$desktopInteraction || $dragState || cloaked ? 'none' : null}
                    style:background={generateBgStyle(sceneSettings)}
                    style:opacity={sceneSettings?.opacity ?? 1.0}
                    on:mouseenter={handleMouseEnter}
                    on:mouseleave={handleMouseLeave}
                    on:mousedown={handleContentMouseDown}
                    on:wheel={e => handleContentWheel(e, tab)}
                    on:focusout={e => handleFocusOut(e, tab)}
                    on:contextmenu|preventDefault|stopPropagation
                >
                    <div style="height: 100%;" style:zoom={tab.zoom || 1.0}>
                        <svelte:component
                            bind:this={componentInstances[tab.id]}
                            this={tab.component}
                            {...tab}
                            groupId={id}
                            id={tab.id}
                            isActive={isActive && tab.id === activeTabId}
                            {x} {y} {width} {height}
                            {maximized}
                        />
                        {#if componentInstances[tab.id]}
                            <InstanceRegistrar tabId={tab.id} instance={componentInstances[tab.id]} />
                        {/if}
                    </div>
                </div>
            {/each}
        </div>
        <div class="side-frame right" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};" on:mousedown={handleFrameMouseDown}></div>
    </div>
    <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};" on:mousedown={handleFrameMouseDown}></div>
    {#if showOptionsMenu}
        <div class="options-menu">
            <button class="menu-item" on:click={() => { windows.toggleMaximize(id); showOptionsMenu = false; }}>{maximized ? 'Restore' : 'Maximize'}</button>
            <button class="menu-item" on:click={openSettings}>Settings...</button>
            {#if component === IoskConsole}
                <button class="menu-item" on:click={handleConnect} disabled={isConsoleConnected}>Connect</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => { const i = instanceRegistry.get(activeTabId); if (i?.toggleAttachMenu) i.toggleAttachMenu(); showOptionsMenu = false; }} disabled={!isConsoleConnected}>Attach</button>
                <button class="menu-item" on:click={() => { newIoskFileExplorer(activeTab.id, title); showOptionsMenu = false; }} disabled={!isConsoleConnected}>Files...</button>
                <button class="menu-item" on:click={() => { const i = instanceRegistry.get(activeTabId); if (i?.toggleRoomsMenu) i.toggleRoomsMenu(); showOptionsMenu = false; }} disabled={!isConsoleConnected}>Rooms</button>
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={handleDisconnect} disabled={!isConsoleConnected}>Disconnect</button>
            {/if}
            {#if component === IoskFileViewer}
                <div class="menu-separator"></div>
                <button class="menu-item" on:click={() => { const i = instanceRegistry.get(activeTabId); if (i?.setMode) i.setMode('rendered'); showOptionsMenu = false; }} disabled={!canRender}>Rendered</button>
                <button class="menu-item" on:click={() => { const i = instanceRegistry.get(activeTabId); if (i?.setMode) i.setMode('raw'); showOptionsMenu = false; }}>Raw</button>
            {/if}
            <div class="menu-separator"></div>
            <button class="menu-item" on:click={() => { dispatch('backrequest'); showOptionsMenu = false; }}>Back Window</button>
            <div class="menu-separator"></div>
            <button class="menu-item" on:click={() => { windows.changeTabZoom(id, activeTabId, 0.1); showOptionsMenu = false; }}>Zoom In</button>
            <button class="menu-item" on:click={() => { windows.changeTabZoom(id, activeTabId, -0.1); showOptionsMenu = false; }}>Zoom Out</button>
            <button class="menu-item" on:click={() => { windows.resetTabZoom(id, activeTabId); showOptionsMenu = false; }}>Reset Zoom</button>
            <div class="menu-separator"></div>
            <button class="menu-item" on:click={() => { windows.toggleMinimize(id); showOptionsMenu = false; }}>Minimize</button>
            <button class="menu-item close-option" on:click={() => { showOptionsMenu = false; windows.removeWindow(id); }}>Close</button>
        </div>
    {/if}
    <div class="cloak" style:background={cloakStyle} style:opacity={cloakOpacity} style:pointer-events={cloaked ? 'auto' : 'none'} on:dblclick|stopPropagation={() => windows.toggleCloak(id)} on:mousedown={handleFrameMouseDown}></div>
    
    <div class="resize-handle n" on:mousedown|stopPropagation={e => onResizeStart(e, 'n')}></div>
    <div class="resize-handle s" on:mousedown|stopPropagation={e => onResizeStart(e, 's')}></div>
    <div class="resize-handle w" on:mousedown|stopPropagation={e => onResizeStart(e, 'w')}></div>
    <div class="resize-handle e" on:mousedown|stopPropagation={e => onResizeStart(e, 'e')}></div>
    <div class="resize-handle nw" on:mousedown|stopPropagation={e => onResizeStart(e, 'nw')}></div>
    <div class="resize-handle ne" on:mousedown|stopPropagation={e => onResizeStart(e, 'ne')}></div>
    <div class="resize-handle sw" on:mousedown|stopPropagation={e => onResizeStart(e, 'sw')}></div>
    <div class="resize-handle se" on:mousedown|stopPropagation={e => onResizeStart(e, 'se')}></div>

    <WindowSettingsModal
        bind:show={showGenericSettingsModal}
        title="Window Settings: {title}"
        {componentName}
        {x} {y} {width} {height}
        showNoticeSettings={true}
    />
</div>