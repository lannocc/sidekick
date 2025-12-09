<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, createEventDispatcher } from 'svelte';
    import { get } from 'svelte/store';
    import { newAskWindow, dragState, windows, generateBoardConfigFromWindow, newWebBrowser, newLocalFileExplorer, newLocalTerminal } from './windows.js';
    import { updateBox, deleteBox, savePanelConfig, updateBoxTransform, setBoxCover } from './local.js';
    import { dashLayouts, desktopView, selectedItems, wasDraggingItems, TASKBAR_HEIGHT, desktopSettings } from './desktop.js';
    import Panel from './Panel.svelte';

    export let box;

    const dispatch = createEventDispatcher();

    // --- Position, Size, and Scale ---
    let x = box.x ?? 100 + (box.id % 5) * 200;
    let y = box.y ?? 100 + Math.floor(box.id / 5) * 150;
    let scale = box.scale ?? 1.0;

    // Make local state reactive to prop changes from the store
    $: if (box.x != null) x = box.x;
    $: if (box.y != null) y = box.y;
    $: if (box.scale != null) scale = box.scale;
    $: coverPanelLocation = box.cover_panel_location;
    $: canSetCover = !coverPanelLocation;
    $: isSelected = $selectedItems.has(`box-${box.id}`);
    $: maxWindowZ = Math.max(100, ...$windows.map(w => w.zIndex));

    // --- Unfold State ---
    let isUnfolded = false;
    let hoveredPanelKey = null; // Key ('x_y') of the currently hovered panel

    $: isMenuOpen = contextMenu.visible || panelContextMenu.visible || showPanelPicker;
    $: isExpanded = isUnfolded || isMenuOpen;

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

    $: state = isExpanded ? 'active' : 'inactive';
    
    $: frameSettings = $desktopSettings.boxes?.frame?.[state];
    $: frameStyle = generateBgStyle(frameSettings);
    $: frameWidth = frameSettings?.width ?? 0;
    $: frameOpacity = frameSettings?.opacity ?? 1.0;
    $: boxShadowStyle = frameSettings?.shadowEnabled
        ? `${frameSettings.shadowInset ? 'inset ' : ''}${frameSettings.shadowX}px ${frameSettings.shadowY}px ${frameSettings.shadowBlur}px ${frameSettings.shadowSpread}px ${frameSettings.shadowColor}`
        : 'none';
    
    $: sceneSettings = $desktopSettings.boxes?.scene?.[state];
    $: sceneStyle = generateBgStyle(sceneSettings);
    $: sceneOpacity = sceneSettings?.opacity ?? 1.0;
    
    // Cloak uses 'inactive' settings since it's only visible when the box is folded/inactive
    $: cloakSettings = $desktopSettings.boxes?.cloak?.inactive;
    $: cloakStyle = generateBgStyle(cloakSettings);
    $: cloakOpacity = cloakSettings?.opacity ?? 1.0;


    // --- Panel Grid Logic ---
    $: panels = box.panels || {};
    $: panelDistances = getPanelDistances(panels);

    // Get the URL for the cover image if one is set
    $: coverImageUrl = (() => {
        if (!coverPanelLocation || !panels) return null;
        const coverPanel = panels[coverPanelLocation];
        if (coverPanel?.board_type === 'image' && coverPanel.board_config?.url) {
            return coverPanel.board_config.url;
        }
        return null;
    })();

    /**
     * Calculates the path distance from the center (0,0) to each panel
     * by traversing the parent-child links of the panels. This ensures the
     * unfold animation follows the attachment order.
     * @param {Object} panels - The map of panel objects.
     * @returns {Object} A map of panel key ('x_y') to its distance from the center.
     */
    function getPanelDistances(panels) {
        const distances = { '0_0': 0 };
        const panelKeys = Object.keys(panels);

        let changed = true;
        // Iteratively calculate distances. A panel's distance can only be calculated
        // if its parent's distance is already known. The loop continues until a full
        // pass makes no new calculations, meaning all connected panels are resolved.
        while (changed) {
            changed = false;
            for (const key of panelKeys) {
                if (distances[key] !== undefined) continue;

                const panel = panels[key];

                // Check if the panel has a defined parent.
                if (panel && panel.parent_loc_x != null && panel.parent_loc_y != null) {
                    const parentKey = `${panel.parent_loc_x}_${panel.parent_loc_y}`;
                    // If the parent's distance is known, calculate this panel's distance.
                    if (distances[parentKey] !== undefined) {
                        distances[key] = distances[parentKey] + 1;
                        changed = true;
                    }
                } else if (key !== '0_0') {
                    // For panels without a parent (e.g., legacy data), or orphans,
                    // fallback to Manhattan distance from the center.
                    distances[key] = Math.abs(panel.loc_x) + Math.abs(panel.loc_y);
                    changed = true;
                }
            }
        }

        // Final fallback for any panels that might be part of a detached chain
        // where the root of the chain has no parent info.
        for (const key of panelKeys) {
            if (distances[key] === undefined) {
                const panel = panels[key];
                distances[key] = Math.abs(panel.loc_x) + Math.abs(panel.loc_y);
            }
        }

        return distances;
    }

    $: centerPanel = panels['0_0'];
    $: sidePanels = Object.values(panels)
        .filter(p => p.loc_x !== 0 || p.loc_y !== 0)
        .map(p => ({
            ...p,
            distance: panelDistances[`${p.loc_x}_${p.loc_y}`] ?? (Math.abs(p.loc_x) + Math.abs(p.loc_y))
        }));

    $: occupiedCoords = new Set(Object.keys(panels));
    $: availableSlots = (() => {
        const slots = [];

        // Create a map of all coordinates to check for neighbors, ensuring uniqueness
        const coordsToCheck = new Map([['0_0', { x: 0, y: 0, key: '0_0' }]]);
        for (const panel of Object.values(panels)) {
            const key = `${panel.loc_x}_${panel.loc_y}`;
            coordsToCheck.set(key, { x: panel.loc_x, y: panel.loc_y, key });
        }

        // Sort them by path distance from center to ensure deterministic behavior.
        // Fallback to manhattan distance for disconnected panels.
        const sortedCoords = Array.from(coordsToCheck.values()).sort((a, b) => {
            const distA = panelDistances[a.key] ?? (Math.abs(a.x) + Math.abs(a.y));
            const distB = panelDistances[b.key] ?? (Math.abs(b.x) + Math.abs(b.y));
            if (distA !== distB) return distA - distB;
            // Stable sort for items with same distance
            if (a.y !== b.y) return a.y - b.y;
            return a.x - b.x;
        });

        for (const coord of sortedCoords) {
            const { x: loc_x, y: loc_y, key: parentKey } = coord;
            const parentDist = panelDistances[parentKey] ?? (Math.abs(loc_x) + Math.abs(loc_y));
            const neighbors = [
                { x: loc_x, y: loc_y - 1, from: 'bottom', parent: { x: loc_x, y: loc_y } }, // Slot is above panel
                { x: loc_x, y: loc_y + 1, from: 'top',    parent: { x: loc_x, y: loc_y } },    // Slot is below panel
                { x: loc_x - 1, y: loc_y, from: 'right',  parent: { x: loc_x, y: loc_y } },  // Slot is left of panel
                { x: loc_x + 1, y: loc_y, from: 'left',   parent: { x: loc_x, y: loc_y } },   // Slot is right of panel
            ];

            for (const neighbor of neighbors) {
                const neighborKey = `${neighbor.x}_${neighbor.y}`;
                // Create a slot for each potential connection, even if the target coordinate is the same.
                if (neighborKey !== '0_0' && !occupiedCoords.has(neighborKey)) {
                    slots.push({ ...neighbor, distance: parentDist + 1 });
                }
            }
        }

        return slots;
    })();

    let innerWidth, innerHeight;
    const BASE_WIDTH = 180;
    // The dynamic calculation becomes a fallback for older boxes without a stored ratio.
    $: dynamicAspectRatio = (innerHeight > 0 && innerWidth > 0) ? (innerHeight - TASKBAR_HEIGHT) / innerWidth : 0;
    $: aspectRatio = box.aspect_ratio ?? dynamicAspectRatio;

    $: boxWidth = BASE_WIDTH * scale;
    $: boxHeight = BASE_WIDTH * aspectRatio * scale;

    let boxEl;
    let saveTransformTimeout;
    let clickTimeout = null;

    // When the box is no longer expanded (closed AND menus are closed),
    // also clear the specific panel key to hide available slots.
    $: if (!isExpanded) {
        hoveredPanelKey = null;
    }

    // --- Dynamic Unfold Direction ---
    let unfoldDirection = 'up';

    function updateUnfoldDirection() {
        if (!boxEl || typeof window === 'undefined') return;
        // Check if the vertical midpoint of the box is in the top or bottom half of theviewport
        const boxMidY = y + boxEl.offsetHeight / 2;
        unfoldDirection = boxMidY > window.innerHeight / 2 ? 'up' : 'down';
    }

    // Update direction whenever the 'y' coordinate changes (e.g., during drag)
    $: y, updateUnfoldDirection();


    // --- Context Menu State ---
    let contextMenu = { visible: false, x: 0, y: 0 };
    let panelContextMenu = { visible: false, x: 0, y: 0, location: null };

    function handlePanelRightClick(event, loc_x, loc_y) {
        event.preventDefault();
        event.stopPropagation();

        const { panX, panY, zoom } = get(desktopView);
        const menuX = (event.clientX - panX) / zoom;
        const menuY = (event.clientY - 40 - panY) / zoom; // -40 for taskbar height

        const panelKey = `${loc_x}_${loc_y}`;
        const panelConfig = panels[panelKey];

        // If center panel is empty, show the main box context menu.
        if (loc_x === 0 && loc_y === 0 && !panelConfig) {
            closePanelContextMenu();
            contextMenu = { visible: true, x: menuX, y: menuY };
            return;
        }

        // For any non-empty panel (including a non-empty center), show the panel context menu.
        if (panelConfig) {
            closeContextMenu();
            panelContextMenu = { visible: true, x: menuX, y: menuY, location: { x: loc_x, y: loc_y } };
        }
    }
    function closeContextMenu() {
        contextMenu.visible = false;
    }
    function closePanelContextMenu() {
        panelContextMenu.visible = false;
    }

    // Close menu or fold box on outside click or Esc key
    function handleWindowClick(event) {
        const clickedOnAnotherBox = event.target.closest('.box') && !boxEl?.contains(event.target);

        // Determine if the click was inside this component's interactive area (box + its popups)
        const clickedInsideComponent = boxEl?.contains(event.target) ||
            (contextMenu.visible && event.target.closest('.context-menu')) ||
            (panelContextMenu.visible && event.target.closest('.context-menu')) ||
            (showPanelPicker && event.target.closest('.panel-picker'));

        if (!clickedInsideComponent && !clickedOnAnotherBox) {
            if (isUnfolded) {
                isUnfolded = false;
            }
            // Also close any open menus
            if (contextMenu.visible) {
                closeContextMenu();
            }
            if (panelContextMenu.visible) {
                closePanelContextMenu();
            }
            if (showPanelPicker) {
                showPanelPicker = false;
            }
        }
    }

    function handleKeyDown(event) {
        if (event.key === 'Escape') {
            if (contextMenu.visible) {
                closeContextMenu();
            } else if (panelContextMenu.visible) {
                closePanelContextMenu();
            } else if (showPanelPicker) {
                showPanelPicker = false;
            } else if (isUnfolded) {
                isUnfolded = false;
            }
        }
    }

    onMount(() => {
        updateUnfoldDirection(); // Set initial direction
        window.addEventListener('click', handleWindowClick, true); // Use capture phase
        window.addEventListener('keydown', handleKeyDown);
    });
    onDestroy(() => {
        window.removeEventListener('click', handleWindowClick, true); // Use capture phase
        window.removeEventListener('keydown', handleKeyDown);
        if (clickTimeout) clearTimeout(clickTimeout);
    });

    // --- Context Menu Actions ---
    function renameBox() {
        closeContextMenu();
        const newName = prompt(`Rename box "${box.name}":`, box.name);
        if (newName && newName.trim() !== '' && newName !== box.name) {
            updateBox(box.id, newName);
        }
    }

    function deleteBoxConfirm() {
        closeContextMenu();
        if (confirm(`Are you sure you want to delete the box "${box.name}"?`)) {
            deleteBox(box.id);
        }
    }

    function askBox() {
        closeContextMenu();
        if (box.type === 'local') {
            newAskWindow([box.context]);
            isUnfolded = false;
        }
    }

    function openTerminal() {
        closeContextMenu();
        if (box.type === 'local' && box.context) {
            newLocalTerminal({ title: `Terminal - ${box.name}`, initialPath: box.context });
            isUnfolded = false;
        }
    }

    function openFiles() {
        closeContextMenu();
        if (box.type === 'local' && box.context) {
            newLocalFileExplorer({ title: `Files - ${box.name}`, initialPath: box.context });
            isUnfolded = false;
        }
    }

    function setCoverImage() {
        closeContextMenu();
        if (!canSetCover) {
            alert("A cover image is already set.");
            return;
        }
        const url = prompt("Enter URL for cover image:");
        if (url) {
            // Pick a preferred empty slot, e.g., 'top' at (0, -1)
            const preferredSlot = availableSlots.find(s => s.x === 0 && s.y === -1) || availableSlots[0];
            if (!preferredSlot) {
                alert("Could not find an available panel slot.");
                return;
            }
            const { x, y, parent } = preferredSlot;
            const locationKey = `${x}_${y}`;
            savePanelConfig(box.id, x, y, 'image', { url }, parent);
            setBoxCover(box.id, locationKey);
            isUnfolded = false;
        }
    }

    function setCoverImageFromPicker() {
        const { location, parent } = panelPickerProps; // location is {x, y}
        showPanelPicker = false;
        isUnfolded = false;

        const url = prompt("Enter URL for cover image:");
        if (url) {
            const locationKey = `${location.x}_${location.y}`;
            savePanelConfig(box.id, location.x, location.y, 'image', { url }, parent);
            setBoxCover(box.id, locationKey);
        }
    }

    function clearCoverImage() {
        closeContextMenu();
        if (coverPanelLocation) {
            const [loc_x, loc_y] = coverPanelLocation.split('_').map(Number);
            savePanelConfig(box.id, loc_x, loc_y, 'empty', null, null);
            setBoxCover(box.id, null);
        }
    }

    function clearPanel() {
        const { location } = panelContextMenu; // location is {x, y}
        closePanelContextMenu();
        const panelKey = `${location.x}_${location.y}`;
        if (location && panels[panelKey]) {
            if (coverPanelLocation === panelKey) {
                setBoxCover(box.id, null);
            }
            savePanelConfig(box.id, location.x, location.y, 'empty', null, null);
            isUnfolded = false;
        }
    }

    // --- Scaling & Drop Target Logic ---
    function handleWheel(event) {
        if (event.ctrlKey || event.altKey) {
            event.preventDefault();
            const zoomStep = 0.05;
            const delta = event.deltaY < 0 ? zoomStep : -zoomStep;
            const currentScale = box.scale ?? 1.0;
            const newScale = Math.max(0.2, currentScale + delta);
            dispatch('scale', { id: box.id, newScale });
        }
    }

    function handlePanelMouseEnter(loc_x, loc_y) {
        const panelKey = `${loc_x}_${loc_y}`;
        // Only update hovered key for existing panels or the center panel.
        // This makes adjacent slots appear.
        if (panels[panelKey] || (loc_x === 0 && loc_y === 0)) {
            hoveredPanelKey = panelKey;
        }

        const state = get(dragState);
        if (state?.draggingGroupId) {
            dragState.update(s => ({...s, dropTargetBoxPanel: { boxId: box.id, location: {x: loc_x, y: loc_y} }}));
        }
    }

    function handlePanelMouseLeave(loc_x, loc_y) {
        const state = get(dragState);
        const currentTarget = state?.dropTargetBoxPanel;
        if (currentTarget?.boxId === box.id && currentTarget?.location?.x === loc_x && currentTarget?.location?.y === loc_y) {
            dragState.update(s => ({...s, dropTargetBoxPanel: null}));
        }
    }

    function handleDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'link';
    }

    function handleDrop(event, loc_x, loc_y, parent) {
        event.preventDefault();
        try {
            const data = JSON.parse(event.dataTransfer.getData('application/json'));
            if (data.type === 'dashLayout') {
                savePanelConfig(box.id, loc_x, loc_y, 'dash', data.layout, parent);
            }
        } catch(e) {
            console.error("Drop failed:", e);
        }
    }

    // --- Panel Picker State & Logic ---
    let showPanelPicker = false;
    let panelPickerProps = {}; // { location: {x,y}, parent: {x,y}, clientX, clientY }

    function getActiveTabTitle(win) {
        if (!win || !win.tabs) return '...';
        const activeTab = win.tabs.find(t => t.id === win.activeTabId);
        return activeTab ? activeTab.title : (win.tabs[0]?.title || 'Window');
    }

    function selectWindow(group) {
        const { location, parent } = panelPickerProps; // location is {x, y}
        const board_config = generateBoardConfigFromWindow(group);
        const board_type = group.tabs.length > 1 ? 'tabs' : 'window';
        savePanelConfig(box.id, location.x, location.y, board_type, board_config, parent);
        windows.removeWindow(group.id);
        showPanelPicker = false;
        isUnfolded = false;
    }

    function selectDash(layout) {
        const { location, parent } = panelPickerProps; // location is {x, y}
        savePanelConfig(box.id, location.x, location.y, 'dash', layout, parent);
        showPanelPicker = false;
        isUnfolded = false;
    }

    // --- Panel Click Logic ---
    function handleCenterPanelSingleClick() {
        isUnfolded = !isUnfolded;
    }

    function handleCenterPanelDoubleClick() {
        if (box.type === 'local' && box.context) {
            isUnfolded = false;
            newLocalFileExplorer({ initialPath: box.context, title: `Files - ${box.name}` });
        }
    }

    function handleSidePanelClick(event, loc_x, loc_y, isAvailableSlot, parent) {
        if (!isUnfolded) {
            isUnfolded = true;
            return;
        }

        if (showPanelPicker) {
            showPanelPicker = false;
            return;
        }

        const panelKey = `${loc_x}_${loc_y}`;
        const panelConfig = panels[panelKey];

        if (isAvailableSlot || !panelConfig || panelConfig.board_type === 'empty') {
            event.stopPropagation();
            const { panX, panY, zoom } = get(desktopView);
            panelPickerProps = {
                location: { x: loc_x, y: loc_y },
                parent: parent,
                clientX: (event.clientX - panX) / zoom,
                clientY: (event.clientY - 40 - panY) / zoom,
            };
            showPanelPicker = true;
        } else {
            const { board_type, board_config } = panelConfig;

            if (board_type === 'image') {
                if (board_config?.url) newWebBrowser({ initialUrl: board_config.url });
            } else if (board_type === 'window' || board_type === 'tabs') {
                windows.restoreWindow(board_config);
            } else if (board_type === 'dash' && board_config?.windowGroups) {
                for (const group of board_config.windowGroups) {
                    windows.restoreWindow(group);
                }
            }
            isUnfolded = false;
        }
    }

    function handlePanelClick(event, loc_x, loc_y, isAvailableSlot = false, parent = null) {
        if (get(wasDraggingItems) || event.ctrlKey) return;

        if (loc_x === 0 && loc_y === 0) { // Center panel
            if (clickTimeout) {
                clearTimeout(clickTimeout);
                clickTimeout = null;
                handleCenterPanelDoubleClick();
            } else {
                clickTimeout = setTimeout(() => {
                    clickTimeout = null;
                    handleCenterPanelSingleClick();
                }, 250);
            }
        } else { // Side panel
            handleSidePanelClick(event, loc_x, loc_y, isAvailableSlot, parent);
        }
    }


    function isDropTarget(loc_x, loc_y) {
        const target = $dragState?.dropTargetBoxPanel;
        return target?.boxId === box.id && target?.location?.x === loc_x && target?.location?.y === loc_y;
    }

</script>

<style>
    .box {
        position: absolute;
        cursor: pointer;
        user-select: none;
        transition: z-index 0s 0.3s, border-color 0.2s ease-in-out; /* Delay z-index change until after animation */
        border: 1px solid transparent;
        border-radius: 7px; /* A bit larger than panel's 6px */
    }
    .box.selected {
        border-color: rgba(52, 152, 219, 0.9);
        box-shadow: 0 0 8px rgba(52, 152, 219, 0.7);
    }
    .box:not(.selected):hover {
        border-color: rgba(255, 255, 255, 0.4);
    }

    .box.is-unfolded {
        transition-delay: 0s;
    }

    .box-cloak {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        z-index: 4;
        transition: opacity 0.3s ease-in-out;
        cursor: pointer;
        box-sizing: border-box;
    }
    .box.is-unfolded .box-cloak {
        opacity: 0;
        pointer-events: none;
    }

    .box-cloak-scene {
        width: 100%;
        height: 100%;
        position: absolute;
        top: 0;
        left: 0;
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out;
    }
    .box-cloak-content {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 5px;
        color: var(--title-bar-text);
        text-align: center;
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out;
    }

    .box-cover {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 5; /* On top of the default cloak */
        border-radius: 6px;
        overflow: hidden;
        opacity: 1;
        transition: opacity 0.3s ease-in-out;
        cursor: pointer;
    }

    .box.is-unfolded .box-cover {
        opacity: 0;
        pointer-events: none; /* Allow interaction with panels underneath when unfolded */
    }

    .cover-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .panel {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        box-sizing: border-box;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        color: var(--title-bar-text);
        text-align: center;
    }
    .panel-scene {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out;
    }

    .center {
        z-index: 3;
        cursor: pointer;
    }

    /* --- NEW FRAME STYLES --- */
    .box-frame {
        display: flex;
        flex-direction: column;
        width: 100%;
        height: 100%;
        box-sizing: border-box;
        border-radius: 6px;
        overflow: hidden;
        background: transparent;
        transition: box-shadow 0.3s ease-in-out;
    }
    .top-frame, .bottom-frame, .side-frame {
        flex-shrink: 0;
        transition: background 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-in-out, width 0.3s ease-in-out, height 0.3s ease-in-out;
    }
    .middle-row {
        flex-grow: 1;
        display: flex;
        flex-direction: row;
        overflow: hidden;
    }
    .content-area-wrapper {
        flex-grow: 1;
        position: relative;
        overflow: hidden;
    }
    .content-area-wrapper.drop-target {
        outline: 2px solid #3498db;
        outline-offset: -2px;
    }

    /* All side panels start hidden and scaled down */
    .panel:not(.center) {
        z-index: 1;
        opacity: 0;
        transform: scale(0.95) var(--pos-transform, translate(0,0));
        pointer-events: none;
    }

    /* Initial state for empty panels - start scaled to zero for correct animation */
    .panel.is-empty.from-bottom {
        transform-origin: bottom center;
        transform: var(--pos-transform, translate(0,0)) scaleY(0);
    }
    .panel.is-empty.from-top {
        transform-origin: top center;
        transform: var(--pos-transform, translate(0,0)) scaleY(0);
    }
    .panel.is-empty.from-right {
        transform-origin: right center;
        transform: var(--pos-transform, translate(0,0)) scaleX(0);
    }
    .panel.is-empty.from-left {
        transform-origin: left center;
        transform: var(--pos-transform, translate(0,0)) scaleX(0);
    }

    /* Unfold EXISTING side panels on click */
    .box.is-unfolded .panel:not(.center):not(.is-empty) {
        opacity: var(--frame-opacity);
        transform: var(--pos-transform, translate(0,0));
        pointer-events: auto;
        transition-delay: var(--unfold-delay, 0s);
    }

    /* Make VISIBLE empty slots interactive */
    .box.is-unfolded .panel.is-empty.is-visible {
        opacity: var(--frame-opacity);
        pointer-events: auto;
        transition-delay: var(--unfold-delay, 0s);
    }

    /* Skinny/flat styles for VISIBLE empty side panels when expanded */
    .box.is-unfolded .panel.is-empty.is-visible.from-bottom {
        transform-origin: bottom center;
        transform: var(--pos-transform, translate(0,0)) scaleY(0.15);
        clip-path: polygon(0% 100%, 100% 100%, 85% 0%, 15% 0%);
    }
    .box.is-unfolded .panel.is-empty.is-visible.from-top {
        transform-origin: top center;
        transform: var(--pos-transform, translate(0,0)) scaleY(0.15);
        clip-path: polygon(15% 100%, 85% 100%, 100% 0%, 0% 0%);
    }
    .box.is-unfolded .panel.is-empty.is-visible.from-right {
        transform-origin: right center;
        transform: var(--pos-transform, translate(0,0)) scaleX(0.15);
        clip-path: polygon(0% 15%, 0% 85%, 100% 100%, 100% 0%);
    }
    .box.is-unfolded .panel.is-empty.is-visible.from-left {
        transform-origin: left center;
        transform: var(--pos-transform, translate(0,0)) scaleX(0.15);
        clip-path: polygon(0% 0%, 100% 15%, 100% 85%, 0% 100%);
    }

    .box-name {
        font-size: 1.1em;
        font-weight: bold;
        word-break: break-word;
    }
    .box-context {
        font-size: 0.8em;
        opacity: 0.7;
        margin-top: 5px;
        word-break: break-all;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .context-menu {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10001;
        display: flex;
        flex-direction: column;
        padding: 4px 0;
        min-width: 150px;
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
    .context-menu button:disabled {
        color: #7f8c8d;
        cursor: not-allowed;
        background-color: transparent;
    }
    .menu-separator { height: 1px; background-color: var(--border-color); margin: 4px 0; }
    .context-menu .delete { color: #e74c3c; }
    .context-menu .delete:hover { background-color: #c0392b; color: white; }

    .panel-picker {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        z-index: 10001;
        display: flex;
        flex-direction: column;
        padding: 4px 0;
        min-width: 200px;
        max-height: 300px;
        overflow-y: auto;
    }
    .picker-header {
        padding: 4px 12px;
        font-weight: bold;
        color: var(--title-bar-text);
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
    }
    .picker-item {
        background: none;
        border: none;
        color: var(--taskbar-text);
        padding: 8px 12px;
        text-align: left;
        cursor: pointer;
        font-size: 14px;
        width: 100%;
    }
    .picker-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .empty-message {
        padding: 8px 12px;
        color: #7f8c8d;
        font-style: italic;
    }
</style>

<svelte:window bind:innerWidth bind:innerHeight />

<div
    class="box"
    class:is-unfolded={isUnfolded}
    class:selected={isSelected}
    data-id={box.id}
    data-type="box"
    bind:this={boxEl}
    style:left="{x}px"
    style:top="{y}px"
    style:width="{boxWidth}px"
    style:height="{boxHeight}px"
    style:z-index={isExpanded ? maxWindowZ + 1 : 10}
    on:wheel={handleWheel}
    on:scale
>
    <!-- Default Cloak (visible when folded) -->
    {#if !coverImageUrl}
    <div 
        class="box-cloak" 
        on:click={e => handlePanelClick(e, 0, 0)}
        on:contextmenu={e => handlePanelRightClick(e, 0, 0)}
    >
        <div class="box-frame" style:box-shadow={boxShadowStyle}>
            <div class="top-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
            <div class="middle-row">
                <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                <div class="content-area-wrapper">
                    <div class="box-cloak-scene" style:background={sceneStyle} style:opacity={sceneOpacity}>
                    </div>
                    <div class="box-cloak-content" style:background={cloakStyle} style:opacity={cloakOpacity}>
                        <div class="box-name">{box.name}</div>
                        <div class="box-context" title={box.context}>{box.context}</div>
                    </div>
                </div>
                <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
            </div>
            <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
        </div>
    </div>
    {/if}

    <!-- User-defined Cover Image (also visible when folded) -->
    {#if coverImageUrl}
        <div class="box-cover" on:click={(e) => handlePanelClick(e, 0, 0)}>
            <img src={coverImageUrl} alt="{box.name} cover" class="cover-image" />
        </div>
    {/if}

    <!-- Existing Side Panels -->
    {#each sidePanels as panel (panel.id)}
        {@const parent = {x: panel.parent_loc_x, y: panel.parent_loc_y}}
        <div
            class="panel"
            style:--pos-transform="translateX({panel.loc_x * 105}%) translateY({panel.loc_y * 105}%)"
            style:--unfold-delay="{(panel.distance - 1) * 75}ms"
            style:--frame-opacity={frameOpacity}
            on:click={e => handlePanelClick(e, panel.loc_x, panel.loc_y)}
            on:contextmenu={e => handlePanelRightClick(e, panel.loc_x, panel.loc_y)}
            on:mouseenter={() => handlePanelMouseEnter(panel.loc_x, panel.loc_y)}
            on:mouseleave={() => handlePanelMouseLeave(panel.loc_x, panel.loc_y)}
            on:dragover={handleDragOver}
            on:drop={e => handleDrop(e, panel.loc_x, panel.loc_y, parent)}
        >
            <div class="box-frame" style:box-shadow={boxShadowStyle}>
                <div class="top-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                <div class="middle-row">
                    <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                    <div class="content-area-wrapper" class:drop-target={isDropTarget(panel.loc_x, panel.loc_y)}>
                        <div class="panel-scene" style:background={sceneStyle} style:opacity={sceneOpacity}>
                            <Panel board_type={panel.board_type} board_config={panel.board_config} />
                        </div>
                    </div>
                    <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                </div>
                <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
            </div>
        </div>
    {/each}

    <!-- Available Slots for new panels -->
    {#each availableSlots as slot (`${slot.x}_${slot.y}_from_${slot.parent.x}_${slot.parent.y}`)}
        {@const parentKey = `${slot.parent.x}_${slot.parent.y}`}
        <div
            class="panel is-empty from-{slot.from}"
            class:is-visible={hoveredPanelKey === parentKey}
            style:--pos-transform="translateX({slot.x * 105}%) translateY({slot.y * 105}%)"
            style:--unfold-delay="{(slot.distance - 1) * 75}ms"
            style:--frame-opacity={frameOpacity}
            on:click={e => handlePanelClick(e, slot.x, slot.y, true, slot.parent)}
            on:contextmenu|preventDefault|stopPropagation
            on:mouseenter={() => handlePanelMouseEnter(slot.x, slot.y)}
            on:mouseleave={() => handlePanelMouseLeave(slot.x, slot.y)}
            on:dragover={handleDragOver}
            on:drop={e => handleDrop(e, slot.x, slot.y, slot.parent)}
        >
            <div class="box-frame" style:box-shadow={boxShadowStyle}>
                <div class="top-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                <div class="middle-row">
                    <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                    <div class="content-area-wrapper" class:drop-target={isDropTarget(slot.x, slot.y)}>
                        <div class="panel-scene" style:background={sceneStyle} style:opacity={sceneOpacity} />
                    </div>
                    <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                </div>
                <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
            </div>
        </div>
    {/each}

    <!-- Center Panel with Content -->
    <div 
        class="panel center" 
        style:opacity={isUnfolded ? 1 : 0}
        style:pointer-events={isUnfolded ? 'auto' : 'none'}
        on:click={e => handlePanelClick(e, 0, 0, false, null)} 
        on:contextmenu={e => handlePanelRightClick(e, 0, 0)} 
        on:mouseenter={() => handlePanelMouseEnter(0, 0)} 
        on:mouseleave={() => handlePanelMouseLeave(0, 0)} 
        on:dragover={handleDragOver} 
        on:drop={e => handleDrop(e, 0, 0, null)}
    >
        <div class="box-frame" style:box-shadow={boxShadowStyle}>
            <div class="top-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
            <div class="middle-row">
                <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
                <div class="content-area-wrapper" class:drop-target={isDropTarget(0, 0)}>
                    <div class="panel-scene" style:background={sceneStyle} style:opacity={sceneOpacity}>
                        {#if centerPanel}
                            <Panel board_type={centerPanel.board_type} board_config={centerPanel.board_config} />
                        {:else}
                            <div class="box-name">{box.name}</div>
                            <div class="box-context" title={box.context}>{box.context}</div>
                        {/if}
                    </div>
                </div>
                <div class="side-frame" style="width: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
            </div>
            <div class="bottom-frame" style="height: {frameWidth}px; background: {frameStyle}; opacity: {frameOpacity};"></div>
        </div>
    </div>
</div>

{#if contextMenu.visible}
    <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
        <button on:click={askBox} disabled={box.type !== 'local'}>Ask...</button>
        <button on:click={openTerminal} disabled={box.type !== 'local'}>Terminal</button>
        <button on:click={openFiles} disabled={box.type !== 'local'}>Files</button>
        <div class="menu-separator"></div>
        <button on:click={renameBox}>Rename...</button>
        <div class="menu-separator"></div>
        <button on:click={setCoverImage} disabled={!canSetCover}>Set Cover Image...</button>
        <button on:click={clearCoverImage} disabled={!coverPanelLocation}>Clear Cover Image</button>
        <div class="menu-separator"></div>
        <button on:click={deleteBoxConfirm} class="delete">Delete</button>
    </div>
{/if}

{#if panelContextMenu.visible}
    <div class="context-menu" style="top: {panelContextMenu.y}px; left: {panelContextMenu.x}px;" on:click|stopPropagation>
        <button on:click={clearPanel}>Clear</button>
    </div>
{/if}

<!-- Panel Picker UI -->
{#if showPanelPicker}
    <div class="panel-picker" style:top="{panelPickerProps.clientY}px" style:left="{panelPickerProps.clientX}px" on:click|stopPropagation>
        {#if !coverPanelLocation}
            <button class="picker-item" on:click={setCoverImageFromPicker}>
                Set Cover Image...
            </button>
            <div class="menu-separator"></div>
        {/if}

        <div class="picker-header">Open Windows</div>
        {#each $windows as win (win.id)}
            <button class="picker-item" on:click={() => selectWindow(win)}>
                {getActiveTabTitle(win)}
            </button>
        {:else}
            <div class="empty-message">No open windows</div>
        {/each}

        <div class="picker-header" style="margin-top: 5px;">Saved Dashes</div>
        {#each $dashLayouts as layout (layout.id)}
            <button class="picker-item" on:click={() => selectDash(layout)}>
                {layout.name}
            </button>
        {:else}
            <div class="empty-message">No saved dashes</div>
        {/each}
    </div>
{/if}