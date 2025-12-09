<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { createEventDispatcher, tick, onMount, onDestroy, getContext } from 'svelte';
    import { get } from 'svelte/store';
    import { windows, dragState, instanceRegistry, dragRequest, generateBoardConfigFromWindow } from './windows.js';
    import { desktopSettings, windowSettings, windowView, desktopView, TASKBAR_HEIGHT, desktopInteraction, selectedItems } from './desktop.js';
    import { savePanelConfig } from './local.js';
    import IoskConsole from './board/IoskConsole.svelte';
    import IoskFileExplorer from './board/IoskFileExplorer.svelte';
    import IoskFileViewer from './board/IoskFileViewer.svelte';
    import WebBrowser from './board/WebBrowser.svelte';
    import Settings from './board/Settings.svelte';
    import Calculator from './board/Calculator.svelte';
    import IoskPrivateChat from './board/IoskPrivateChat.svelte';
    import LocalTerminal from './board/LocalTerminal.svelte';
    import LocalFileExplorer from './board/LocalFileExplorer.svelte';
    import Ask from './board/Ask.svelte';
    import IoskWatch from './board/IoskWatch.svelte';
    import IoskUserInspector from './board/IoskUserInspector.svelte';
    import NotificationCenter from './board/NotificationCenter.svelte';
    import WindowSettingsModal from './popup/WindowSettingsModal.svelte';
    import InstanceRegistrar from './InstanceRegistrar.svelte';

    // --- Core Properties ---
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

    // --- New Properties for Unified Component ---
    export let isBacked = false;
    export let scale = 1.0;
    export let originalBackedId = null; // ID from the backed_windows table

    // --- Derived State ---
    $: activeTab = tabs.find(t => t.id === activeTabId) || tabs[0] || {};
    $: component = activeTab.component;
    $: componentName = activeTab.componentName;
    $: title = activeTab.title;
    $: isConsoleConnected = activeTab.isConsoleConnected;
    $: canRender = activeTab.canRender;

    const dispatch = createEventDispatcher();
    let settings;
    desktopSettings.subscribe(value => settings = value);

    // --- Style Generation ---
    function generateBgStyle(bgSettings) {
        if (!bgSettings) return null;
        if (bgSettings.bgType === 'gradient') return `linear-gradient(45deg, ${bgSettings.bgGradientStart} 0%, ${bgSettings.bgGradientEnd} 100%)`;
        if (bgSettings.bgType === 'color') return bgSettings.bgColor;
        if (bgSettings.bgType === 'image' && bgSettings.bgImage) {
            let size = 'cover', repeat = 'no-repeat', position = 'center center';
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
    $: windowType = isBacked ? 'back' : 'normal';
    
    // --- Window Styles (Unified) ---
    $: frameSettings = settings?.windows?.[windowType]?.frame?.[state];
    $: frameStyle = generateBgStyle(frameSettings);
    $: frameHeight = frameSettings?.height ?? 30;
    $: frameWidth = frameSettings?.width ?? 0;
    $: frameOpacity = frameSettings?.opacity ?? 1.0;
    $: boxShadowStyle = cloaked ? 'none' : (frameSettings?.shadowEnabled
        ? `${frameSettings.shadowInset ? 'inset ' : ''}${frameSettings.shadowX}px ${frameSettings.shadowY}px ${frameSettings.shadowBlur}px ${frameSettings.shadowSpread}px ${frameSettings.shadowColor}`
        : 'none');
    $: sceneSettings = settings?.windows?.[windowType]?.scene?.[state];
    $: cloakSettings = settings?.windows?.[windowType]?.cloak?.[state];
    $: cloakStyle = generateBgStyle(cloakSettings);
    $: cloakOpacity = cloaked ? (cloakSettings?.opacity ?? 0.8) : 0;

    // --- NEW: Scrollbar Color Derivation ---
    $: scrollbarThumbColor = (frameSettings?.bgType === 'color' ? frameSettings.bgColor : frameSettings?.bgGradientStart) || '#46627f';
    $: scrollbarTrackColor = (sceneSettings?.bgType === 'color' ? sceneSettings.bgColor : sceneSettings?.bgGradientStart) || '#2c3e50';

    // --- Backed Window Specifics ---
    $: isSelected = $selectedItems.has(`backed_window-${id}`);
    
    // --- Transform Logic ---
    $: currentView = isBacked ? $desktopView : $windowView;
    $: transform = `translate(${currentView.panX}px, ${currentView.panY}px) scale(${currentView.zoom}) translate(${x}px, ${y}px)`;

    // --- Interaction State ---
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
    let windowWrapperEl;
    let middleClickTimeout;
    let componentInstances = {};

    // --- Event Handlers ---
    function handleContentMouseDown(event) {
        if (isBacked) return; // Let Desktop.svelte handle backed item interaction
        if (event.button === 1) {
            if (event.ctrlKey) { event.preventDefault(); event.stopPropagation(); dispatch('backrequest'); return; }
            handleMiddleClick(event);
            event.stopPropagation();
            return;
        }
        if ((event.altKey || event.metaKey) && !maximized) {
            if (event.button === 0) { dragRequest.set({ id, type: 'move', direction: null, clientX: event.clientX, clientY: event.clientY, focus: false }); }
            else if (event.button === 2) {
                const relX = event.clientX - x, relY = event.clientY - y;
                let yDir = relY < height / 3 ? 'n' : (relY > (height * 2) / 3 ? 's' : ''), xDir = relX < width / 3 ? 'w' : (relX > (width * 2) / 3 ? 'e' : '');
                if (yDir + xDir) { dragRequest.set({ id, type: 'resize', direction: yDir + xDir, clientX: event.clientX, clientY: event.clientY, focus: false }); }
            }
        } else if (!isActive) { windows.focusWindow(id); }
    }
    
    // ... (Most other functions like onDragStart, onResize, etc., can remain as they are,
    // since they correctly handle the 'front' window case, which is what they're for.)
    // All the logic for handleConnect, handleDisconnect, tab dragging, etc. is fine.
    
    // --- Simplified functions that already exist ---
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
    $: if ($dragRequest && $dragRequest.id === id) {
        const request = $dragRequest;
        dragRequest.set(null);
        const mockEvent = { clientX: request.clientX, clientY: request.clientY, target: titleBarEl, preventDefault: () => {}, button: request.type === 'move' ? 0 : 2 };
        if (request.type === 'move') { onDragStart(mockEvent, { focus: request.focus ?? true }); } 
        else if (request.type === 'resize') { onResizeStart(mockEvent, request.direction, { focus: request.focus ?? true }); }
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
    function handleWindowClick(event) { if (showOptionsMenu && optionsButton && !optionsButton.contains(event.target) && !event.target.closest('.options-menu')) { showOptionsMenu = false; } }
    onMount(() => { window.addEventListener('click', handleWindowClick); });
    onDestroy(() => { window.removeEventListener('click', handleWindowClick); if (focusFollowsMouseTimeout) clearTimeout(focusFollowsMouseTimeout); if (middleClickTimeout) clearTimeout(middleClickTimeout); });
    function handleConnect() { const instance = instanceRegistry.get(activeTabId); if (instance && typeof instance.connect === 'function') instance.connect(); showOptionsMenu = false; }
    function handleDisconnect() { const instance = instanceRegistry.get(activeTabId); if (instance && typeof instance.disconnect === 'function') instance.disconnect(); showOptionsMenu = false; }
    let isTabDragging = false, draggedTabInfo = null, dropIndicator = { visible: false, left: 0 }, tabDragHasMoved = false;
    function onTabMouseDown(e, tab) { if (e.button !== 0 || maximized || isBacked) return; e.stopPropagation(); isTabDragging = true; tabDragHasMoved = false; draggedTabInfo = { groupId: id, tabId: tab.id }; window.addEventListener('mousemove', onTabMouseMove); window.addEventListener('mouseup', onTabMouseUp, { once: true }); }
    function onTabMouseMove(e) { if (!isTabDragging) return; tabDragHasMoved = true; const { top, bottom, left: containerLeft } = tabsContainerEl.getBoundingClientRect(); const isOutsideY = e.clientY < top - 20 || e.clientY > bottom + 20; if (isOutsideY && tabs.length > 1) { draggedTabInfo.isDetaching = true; dropIndicator.visible = false; document.body.style.cursor = 'copy'; } else { draggedTabInfo.isDetaching = false; document.body.style.cursor = 'default'; dropIndicator.visible = false; let targetTabId = null; for (const child of tabsContainerEl.children) { if (!child.classList.contains('tab') || child.dataset.tabId == draggedTabInfo.tabId) continue; const rect = child.getBoundingClientRect(); const midpoint = rect.left + rect.width / 2; if (e.clientX < midpoint) { targetTabId = child.dataset.tabId; dropIndicator.left = rect.left - containerLeft; dropIndicator.visible = true; break; } } if (!dropIndicator.visible) { const lastChild = tabsContainerEl.querySelector('.tab:last-of-type'); if (lastChild) { const rect = lastChild.getBoundingClientRect(); dropIndicator.left = rect.right - containerLeft; dropIndicator.visible = true; } targetTabId = null; } draggedTabInfo.targetTabId = targetTabId; } }
    function onTabMouseUp(e) { window.removeEventListener('mousemove', onTabMouseMove); document.body.style.cursor = 'auto'; if (isTabDragging) { if (draggedTabInfo.isDetaching) { windows.detachTabToNewWindow(draggedTabInfo.groupId, draggedTabInfo.tabId, e.clientX - 100, e.clientY - 15); } else if (tabDragHasMoved) { windows.reorderTab(draggedTabInfo.groupId, draggedTabInfo.tabId, draggedTabInfo.targetTabId); } } isTabDragging = false; draggedTabInfo = null; dropIndicator.visible = false; tabDragHasMoved = false; }
    async function restoreFocus() { if (activeTab.lastFocusedElement && document.body.contains(activeTab.lastFocusedElement)) { await tick(); activeTab.lastFocusedElement.focus({ preventScroll: true }); } }
    $: if (isActive && !isBacked) Promise.resolve().then(restoreFocus);
    function onDragStart(event, { focus = true } = {}) {
        isDragging = true;
        dragState.set({ draggingGroupId: id, dropTargetGroupId: null, dropTargetBoxPanel: null });
        const { panX, panY, zoom } = get(windowView);
        const worldMouseX = (event.clientX - panX) / zoom;
        const worldMouseY = ((event.clientY - TASKBAR_HEIGHT) - panY) / zoom;
        dragOffsetX = worldMouseX - x;
        dragOffsetY = worldMouseY - y;
        window.addEventListener('mousemove', onDrag);
        window.addEventListener('mouseup', onDragEnd, { once: true });
        if (focus) {
            windows.focusWindow(id);
        }
        document.body.style.cursor = 'move';
    }

    function onDrag(event) {
        if (!isDragging) return;

        // Check for drop targets. A CSS class now handles pointer-events on the
        // dragging window, allowing elementFromPoint to see what's underneath.
        const elementUnder = document.elementFromPoint(event.clientX, event.clientY);

        // Only allow dropping on another window's title bar for grouping.
        const targetTitleBar = elementUnder?.closest('.title-bar');
        const targetWrapper = targetTitleBar?.closest('.window-wrapper:not(.backed)');
        let newDropTargetId = null;

        if (targetWrapper && targetWrapper !== windowWrapperEl) {
            const targetId = parseInt(targetWrapper.dataset.id, 10);
            if (targetId) {
                newDropTargetId = targetId;
            }
        }

        if (newDropTargetId) {
             dragState.update(s => ({ ...s, dropTargetGroupId: newDropTargetId, dropTargetBoxPanel: null }));
        } else {
            const dropPanel = elementUnder?.closest('[data-box-id][data-location]');
            if (dropPanel) {
                const boxId = parseInt(dropPanel.dataset.boxId, 10);
                const location = dropPanel.dataset.location;
                dragState.update(s => ({ ...s, dropTargetGroupId: null, dropTargetBoxPanel: { boxId, location } }));
            } else {
                dragState.update(s => ({ ...s, dropTargetGroupId: null, dropTargetBoxPanel: null }));
            }
        }

        // Now, update the window's position in the store to make it follow the cursor.
        const { panX, panY, zoom } = get(windowView);
        const worldMouseX = (event.clientX - panX) / zoom;
        const worldMouseY = ((event.clientY - TASKBAR_HEIGHT) - panY) / zoom;
        const newX = worldMouseX - dragOffsetX;
        const newY = worldMouseY - dragOffsetY;
        windows.updateWindowProps(id, { x: newX, y: newY });
    }

    function onDragEnd() { isDragging = false; document.body.style.cursor = 'auto'; window.removeEventListener('mousemove', onDrag); const currentDragState = get(dragState); if (currentDragState) { if (currentDragState.dropTargetGroupId) { windows.groupWindows(currentDragState.draggingGroupId, currentDragState.dropTargetGroupId); } else if (currentDragState.dropTargetBoxPanel) { const { boxId, location } = currentDragState.dropTargetBoxPanel; const allWindows = get(windows); const sourceGroup = allWindows.find(g => g.id === currentDragState.draggingGroupId); if (sourceGroup) { const board_config = generateBoardConfigFromWindow(sourceGroup, allWindows); const board_type = sourceGroup.tabs.length > 1 ? 'tabs' : 'window'; savePanelConfig(boxId, location, board_type, board_config); windows.removeWindow(currentDragState.draggingGroupId); } } } dragState.set(null); restoreFocus(); }
    function onResizeStart(event, directionOverride = '', { focus = true } = {}) {
        if (maximized || isBacked) return;
        let direction = directionOverride || (event.target.classList.contains('resize-handle') ? 'se' : '');
        if (!direction) return;
        isResizing = true;
        resizeDirection = direction;
        initialResizeState = { x, y, width, height, mouseX: event.clientX, mouseY: event.clientY };
        window.addEventListener('mousemove', onResize);
        window.addEventListener('mouseup', onResizeEnd, { once: true });
        if (focus) {
            windows.focusWindow(id);
        }
    }
    function onResize(event) { if (!isResizing) return; const { x: ix, y: iy, width: iw, height: ih, mouseX: startX, mouseY: startY } = initialResizeState; const { zoom } = get(windowView); const dx = (event.clientX - startX) / zoom; const dy = (event.clientY - startY) / zoom; const minWidth = 250, minHeight = 150; let newX = ix, newY = iy, newWidth = iw, newHeight = ih; if (resizeDirection.includes('e')) { newWidth = iw + dx; } else if (resizeDirection.includes('w')) { newWidth = iw - dx; newX = ix + dx; } if (resizeDirection.includes('s')) { newHeight = ih + dy; } else if (resizeDirection.includes('n')) { newHeight = ih - dy; newY = iy + dy; } if (newWidth < minWidth) { if (resizeDirection.includes('w')) { newX -= minWidth - newWidth; } newWidth = minWidth; } if (newHeight < minHeight) { if (resizeDirection.includes('n')) { newY -= minHeight - newHeight; } newHeight = minHeight; } windows.updateWindowProps(id, { x: newX, y: newY, width: newWidth, height: newHeight }); }
    function onResizeEnd() { isResizing = false; window.removeEventListener('mousemove', onResize); restoreFocus(); }
    function handleMiddleClick(event) { if (isBacked) return; if (event.button !== 1) return; event.preventDefault(); if (middleClickTimeout) { clearTimeout(middleClickTimeout); middleClickTimeout = null; windows.toggleCloak(id); return; } middleClickTimeout = setTimeout(() => { middleClickTimeout = null; }, 250); const onMove = () => { clearTimeout(middleClickTimeout); middleClickTimeout = null; if (maximized) return; if (event.target.closest('.content-area-container')) { dragRequest.set({ id, type: 'move', direction: null, clientX: event.clientX, clientY: event.clientY, focus: false }); } else { onDragStart(event, { focus: false }); } }; const onUp = () => { window.removeEventListener('mousemove', onMove); }; window.addEventListener('mousemove', onMove, { once: true }); window.addEventListener('mouseup', onUp, { once: true }); }
    function handleFrameMouseDown(event) {
        // For backed windows, all mouse down interactions are handled by Desktop.svelte
        if (isBacked) return;

        // For front windows, handle middle-click for cloaking/dragging universally on the frame.
        if (event.button === 1) {
            if (event.ctrlKey) { event.preventDefault(); event.stopPropagation(); dispatch('backrequest'); return; }
            handleMiddleClick(event);
            event.stopPropagation();
            return;
        }

        // For other buttons on front windows...
        clearTimeout(focusFollowsMouseTimeout);
        if ((event.altKey || event.metaKey) && !maximized) {
            event.preventDefault();
            if (event.button === 0) onDragStart(event, { focus: false });
            else if (event.button === 2) onResizeStart(event, 'se', { focus: false });
        } else if (event.button === 0 && cloaked && !maximized) {
            event.preventDefault();
            onDragStart(event, { focus: false });
        } else {
            windows.focusWindow(id);
        }
    }

    function handleTitleBarMouseDown(event) {
        if (isBacked) return;
        if (event.target.closest('button') || event.target.closest('.window-control') || event.target.closest('.tab')) {
            if (!isActive) windows.focusWindow(id);
            return;
        }
        if (event.button === 1) {
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
        if (event.altKey || event.metaKey) {
            event.preventDefault();
            if (event.button === 0) {
                onDragStart(event, { focus: false });
            }
            else if (event.button === 2) {
                onResizeStart(event, 'se', { focus: false });
            }
        } else if (event.button === 0) {
            // This is a left-click on a non-maximized title bar.
            // We set up listeners to start the drag ONLY if the mouse moves.
            // This allows the browser's default dblclick event to fire.
            windows.focusWindow(id); // Focus on mousedown regardless.

            const onMove = () => {
                window.removeEventListener('mouseup', onUp); // Drag has started, onDragEnd will handle the final mouseup.
                onDragStart(event);
            };
            const onUp = () => {
                window.removeEventListener('mousemove', onMove); // It was just a click, cleanup.
            };

            window.addEventListener('mousemove', onMove, { once: true });
            window.addEventListener('mouseup', onUp, { once: true });
        }
    }

    function handleMouseEnter() {
        if (get(dragState)) return;
        if (settings?.focusFollowsMouse) {
            clearTimeout(focusFollowsMouseTimeout);
            focusFollowsMouseTimeout = setTimeout(() => {
                if (isBacked) {
                    // An active backed window can re-assert focus if mouse moves over it from a front window.
                    if (isActive) {
                        windows.unfocusAllWindows();
                    }
                    // Inactive backed windows do not activate on mouse-over.
                } else {
                    // A front window will activate if not already active. This will also
                    // deactivate any active backed window via reactive logic in Desktop.svelte.
                    if (!isActive) {
                        windows.setActiveWindow(id);
                    }
                }
            }, settings.focusDelay);
        }
    }

    function handleMouseLeave() {
        clearTimeout(focusFollowsMouseTimeout);
    }

</script>

<style>
    /* ... (Existing styles for window-frame, title-bar etc.) ... */
    .window-wrapper {
        position: absolute;
        transform-origin: 0 0;
    }
    .window-wrapper.dragging {
        pointer-events: none;
    }
    .window-frame, .backed-window-frame {
        display: flex;
        flex-direction: column;
        box-sizing: border-box;
        transition: border-color 0.3s ease-in-out, border-radius 0.3s ease-in-out, box-shadow 0.4s ease-in-out, opacity 0.2s ease-in-out;
    }

    /* Styles for the front (normal) window */
    .window-frame {
        border: 1px solid var(--border-color);
        background-color: transparent;
        border-radius: 6px;
        min-width: 250px;
        min-height: 150px;
        height: 100%;
        width: 100%;
    }
    .window-frame.has-custom-frame { border: none; }
    .window-frame.cloaked { border-color: transparent !important; background-color: transparent; }
    .window-frame.cloaked > *:not(.cloak):not(.resize-handle) { visibility: hidden; }
    .backed-window-frame.cloaked > *:not(.cloak) {
        visibility: hidden;
    }
    .window-frame:not(.active) { border-color: #7f8c8d; }
    .window-wrapper.minimized { display: none; }
    .window-wrapper.maximized .window-frame { border-radius: 0; }
    .window-wrapper.maximized .resize-handle { display: none; }
    .window-wrapper.maximized .title-bar { cursor: default; }

    /* Styles for the back (frameless) window */
    .backed-window-frame {
        border: 1px solid var(--border-color);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        background-color: transparent;
        overflow: hidden;
        border-radius: 6px;
        height: 100%;
        width: 100%;
    }
    .backed-window-frame.selected {
        border-color: rgba(52, 152, 219, 0.7);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3), 0 0 8px rgba(52, 152, 219, 0.6);
    }
    .backed-window-frame:not(.active) {
        cursor: pointer;
    }
    
    @keyframes notice-glow {
        50% { border-color: var(--notice-color); box-shadow: 0 0 20px 5px var(--notice-color), var(--original-shadow, 0 5px 15px rgba(0,0,0,0.3)); }
    }
    .window-frame.noticing {
        animation: notice-glow 1.2s ease-in-out;
        --original-shadow: var(--box-shadow);
    }

    /* ... (Most other styles are fine, just need to scope them correctly) ... */
    .title-bar { flex-shrink: 0; color: var(--title-bar-text); display: flex; justify-content: space-between; align-items: center; padding: 0 8px; cursor: move; border-top-left-radius: 5px; border-top-right-radius: 5px; user-select: none; position: relative; transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out, height 0.3s ease-in-out; }
    .title-bar.drop-target::after { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(52, 152, 219, 0.4); border: 2px dashed #3498db; z-index: 1; pointer-events: none; border-radius: 5px; }
    .title-center { flex-grow: 1; text-align: center; overflow: hidden; height: 100%; display: flex; align-items: flex-end; justify-content: center; }
    .title-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 30px; }
    .tabs-container { position: relative; display: flex; }
    .tab { display: flex; align-items: center; background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; padding: 0 5px; margin-right: 2px; height: 26px; margin-top: auto; max-width: 150px; transition: opacity 0.2s, background-color 0.3s; }
    .tab.active { background-color: var(--window-bg); z-index: 1; }
    .tab.dragging { opacity: 0.4; }
    .drop-indicator { position: absolute; top: 4px; bottom: 0px; width: 2px; background-color: #3498db; pointer-events: none; }
    .tab:not(.active) { opacity: 0.7; }
    .tab:not(.active):hover { opacity: 1; }
    .tab-close-button { background: none; border: none; color: var(--taskbar-text); cursor: pointer; padding: 0 5px; font-size: 1.2em; line-height: 1; opacity: 0.7; }
    .tab-close-button:hover { color: #e74c3c; opacity: 1; }
    .tab-title { flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; padding: 0 5px; }
    .tab.active .tab-title { font-weight: bold; }
    .window-controls { display: flex; gap: 5px; z-index: 2; }
    .window-control { --button-size: calc(var(--frame-height, 30px) * 0.45); width: var(--button-size); height: var(--button-size); display: flex; align-items: center; justify-content: center; font-size: var(--button-size); color: rgba(0,0,0,0.6); font-weight: bold; border-radius: 50%; cursor: pointer; border: 1px solid rgba(0,0,0,0.2); line-height: 1; }
    .close { background-color: #ff5f56; }
    .minimize { background-color: #ffbd2e; }
    .maximize { background-color: #27c93f; }
    .options-menu-button { background-color: #3498db; color: white; line-height: 0.8; }
    .middle-row { flex-grow: 1; display: flex; flex-direction: row; overflow: hidden; }
    .content-area-wrapper { flex-grow: 1; position: relative; overflow: hidden; }
    .content-area-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: auto; padding: 5px; box-sizing: border-box; transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out; }
    .side-frame, .bottom-frame { flex-shrink: 0; transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out, width 0.3s ease-in-out, height 0.3s ease-in-out; }
    .cloak { position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 5; pointer-events: none; border-radius: 5px; transition: opacity 0.3s ease-in-out, background 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
    .resize-handle { position: absolute; z-index: 6; }
    .resize-handle.n { top: -4px; left: 8px; right: 8px; height: 8px; cursor: n-resize; }
    .resize-handle.s { bottom: -4px; left: 8px; right: 8px; height: 8px; cursor: s-resize; }
    .resize-handle.w { top: 8px; bottom: 8px; left: -4px; width: 8px; cursor: w-resize; }
    .resize-handle.e { top: 8px; bottom: 8px; right: -4px; width: 8px; cursor: e-resize; }
    .resize-handle.nw { top: -4px; left: -4px; width: 12px; height: 12px; cursor: nw-resize; }
    .resize-handle.ne { top: -4px; right: -4px; width: 12px; height: 12px; cursor: ne-resize; }
    .resize-handle.sw { bottom: -4px; left: -4px; width: 12px; height: 12px; cursor: sw-resize; }
    .resize-handle.se { bottom: -4px; right: -4px; width: 12px; height: 12px; cursor: se-resize; }
    .options-menu { position: absolute; top: 35px; right: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 1000; display: flex; flex-direction: column; min-width: 150px; padding: 4px 0; user-select: none; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; }
    .menu-item.close-option { color: #e74c3c; }
    .menu-item.close-option:hover:not(:disabled) { background-color: #c0392b; color: white; }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
</style>

<div class="window-wrapper"
    bind:this={windowWrapperEl}
    style:width="{width * scale}px" style:height="{height * scale}px"
    style:z-index="{zIndex}"
    style:transform="{transform}"
    style:--scrollbar-thumb-bg={scrollbarThumbColor}
    style:--scrollbar-track-bg={scrollbarTrackColor}
    class:minimized
    class:maximized={!isBacked && maximized}
    class:backed={isBacked}
    class:dragging={isDragging}
    data-id={id}
    data-type={isBacked ? 'backed_window' : 'window'}
    on:contextmenu|preventDefault|stopPropagation={isBacked ? (e) => dispatch('contextmenubacked', e) : null}
    on:wheel={isBacked ? (e) => dispatch('wheelbacked', e) : null}
>
    <div 
        class:window-frame={!isBacked}
        class:backed-window-frame={isBacked}
        class:active={isActive} 
        class:noticing={!!notice} 
        class:cloaked
        class:selected={isBacked && isSelected}
        style:box-shadow={boxShadowStyle}
        style:--box-shadow={boxShadowStyle} 
        style:--notice-color={notice?.color} 
        on:mousedown={!isBacked ? handleFrameMouseDown : null}
        on:mouseenter={handleMouseEnter}
        on:mouseleave={handleMouseLeave}
    >
        <div class="title-bar" bind:this={titleBarEl} class:drop-target={$dragState?.dropTargetGroupId === id && $dragState?.draggingGroupId !== id} on:mousedown={!isBacked ? handleTitleBarMouseDown : null} on:dblclick={!isBacked ? () => windows.toggleMaximize(id) : null} data-group-id={id} style="height: {frameHeight}px; background: {frameStyle}; opacity: {frameOpacity}; --frame-height: {frameHeight}px;">
            {#if !isBacked}
                <div class="window-controls" on:dblclick|stopPropagation on:mouseup|stopPropagation>
                    <div class="window-control close" title="Close" on:click={() => windows.removeWindow(id)} on:mousedown|stopPropagation>&times;</div>
                    <div class="window-control minimize" title="Minimize" on:click={() => windows.toggleMinimize(id)} on:mousedown|stopPropagation>&mdash;</div>
                </div>
            {/if}

            <div class="title-center">
                {#if !isBacked && tabs.length > 1}
                    <div class="tabs-container" bind:this={tabsContainerEl} on:dblclick|stopPropagation>
                        {#each tabs as tab (tab.id)}
                            <div class="tab" class:active={tab.id === activeTabId} class:dragging={isTabDragging && draggedTabInfo.tabId === tab.id} data-tab-id={tab.id} on:mousedown={e => onTabMouseDown(e, tab)}>
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
            
            {#if !isBacked}
                <div class="window-controls" on:dblclick|stopPropagation on:mouseup|stopPropagation>
                    <div class="window-control maximize" title={maximized ? 'Restore' : 'Maximize'} on:click={() => windows.toggleMaximize(id)} on:mousedown|stopPropagation>
                        {@html maximized ? '&#128470;' : '&#9632;'}
                    </div>
                    <div class="window-control options-menu-button" title="Options" bind:this={optionsButton} on:click|stopPropagation={() => showOptionsMenu = !showOptionsMenu}>≡</div>
                </div>
            {/if}
        </div>

        <div class="middle-row">
            <div class="side-frame left" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};" on:mousedown={!isBacked ? handleFrameMouseDown : null}></div>
            <div class="content-area-wrapper">
                {#each tabs as tab (tab.id)}
                    {@const { component, ...restOfTab } = tab}
                    <div class="content-area-container" style:display={tab.id === activeTabId && !minimized ? 'block' : 'none'} style:pointer-events={isBacked ? (isActive && !cloaked ? null : 'none') : ($desktopInteraction || $dragState || cloaked ? 'none' : null)} style:background={generateBgStyle(sceneSettings)} style:opacity={sceneSettings?.opacity ?? 1.0} on:mousedown={handleContentMouseDown} on:wheel={e => handleContentWheel(e, tab)} on:focusout={e => handleFocusOut(e, tab)}>
                        <div style="height: 100%;" style:zoom={tab.zoom || 1.0}>
                            <svelte:component bind:this={componentInstances[tab.id]} this={component} {...restOfTab} groupId={id} id={tab.id} isActive={isActive && tab.id === activeTabId} {x} {y} {width} {height} {maximized} {isBacked} />
                            {#if componentInstances[tab.id]}
                                <InstanceRegistrar tabId={tab.id} instance={componentInstances[tab.id]} />
                            {/if}
                        </div>
                    </div>
                {/each}
            </div>
            <div class="side-frame right" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};" on:mousedown={!isBacked ? handleFrameMouseDown : null}></div>
        </div>
        <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};" on:mousedown={!isBacked ? handleFrameMouseDown : null}></div>

        {#if !isBacked && showOptionsMenu}
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
        
        <div class="cloak" style:background={cloakStyle} style:opacity={cloakOpacity} style:pointer-events={cloaked ? 'auto' : 'none'}
             on:dblclick|stopPropagation={!isBacked ? () => windows.toggleCloak(id) : null}
             on:mousedown={!isBacked ? handleFrameMouseDown : null}></div>

        {#if !isBacked}
            <div class="resize-handle n" on:mousedown|stopPropagation={e => onResizeStart(e, 'n')}></div>
            <div class="resize-handle s" on:mousedown|stopPropagation={e => onResizeStart(e, 's')}></div>
            <div class="resize-handle w" on:mousedown|stopPropagation={e => onResizeStart(e, 'w')}></div>
            <div class="resize-handle e" on:mousedown|stopPropagation={e => onResizeStart(e, 'e')}></div>
            <div class="resize-handle nw" on:mousedown|stopPropagation={e => onResizeStart(e, 'nw')}></div>
            <div class="resize-handle ne" on:mousedown|stopPropagation={e => onResizeStart(e, 'ne')}></div>
            <div class="resize-handle sw" on:mousedown|stopPropagation={e => onResizeStart(e, 'sw')}></div>
            <div class="resize-handle se" on:mousedown|stopPropagation={e => onResizeStart(e, 'se')}></div>
        {/if}
    </div>

    <WindowSettingsModal bind:show={showGenericSettingsModal} title="Window Settings: {title}" {componentName} {x} {y} {width} {height} showNoticeSettings={true}/>
</div>
