<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { windows, newSettings, dragRequest, componentMap, generateBoardConfigFromWindow, dragState, instanceRegistry } from './windows.js';
    import Window from './Window.svelte';
    import { desktopSettings, dashActive, desktopView, windowView, TASKBAR_HEIGHT, selectedItems, wasDraggingItems, desktopInteraction, activeBoxId, currentBoxId, skyCloakEnabled } from './desktop.js';
    import { boxes, desktopShortcuts, backedWindows, updateDesktopSettings, updateBoxTransform, updateShortcutTransform, updateBackedWindowTransform, createBackedWindow, createBox, resolveAssetDataUrl, generateBgStyle } from './bridge.js';
    import Box from './Box.svelte';
    import Dash from './Dash.svelte';
    import Shortcut from './Shortcut.svelte';
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { connectionStatus } from './bridge.js';
    import { fade } from 'svelte/transition';
    import InstanceRegistrar from './InstanceRegistrar.svelte';

    // *** MODIFICATION START ***
    // Create a single derived store for all window-like entities to render.
    // This is the key to preserving component instances across front/back transitions.
    $: allRenderableWindows = (() => {
        const frontWindows = $windows.map(w => ({ ...w, isBacked: false, scale: 1.0 }));

        // Initialize seenKeys with all keys from front windows to detect collisions between front/back layers.
        const seenKeys = new Set(frontWindows.map(w => w.id));

        const mappedBackedWindows = ($backedWindows || []).map(bw => {
            const config = bw.config;
            // The preferred key is originalGroupId for component persistence, otherwise the db id.
            let persistentId = bw.originalGroupId != null ? bw.originalGroupId : bw.id;

            // Check if this preferred key is already taken by a front window or another backed window.
            if (seenKeys.has(persistentId)) {
                console.warn(`Duplicate key (${persistentId}) found for backed window (collides with front window or other backed window). Using unique DB ID ${bw.id} as key to prevent crash.`);
                // Fallback to the unique DB id.
                persistentId = bw.id;
            }

            // It's possible the fallback DB ID is also a duplicate. This is a rare
            // but possible edge case. If it happens, we must not crash.
            if (seenKeys.has(persistentId)) {
                console.error(`Unresolvable key collision for backed window ${bw.id}. Using prefixed key as last resort.`);
                persistentId = `dbid-${bw.id}`;
            }

            seenKeys.add(persistentId);

            return {
                ...config,
                // Explicitly override with live data from the backed window record
                x: bw.x,
                y: bw.y,
                scale: bw.scale || 1.0,
                zIndex: bw.z_index || 1,

                // Set derived/unified properties
                id: persistentId,
                isActive: interactiveBackedWindowId === persistentId,
                originalBackedId: bw.id,
                isBacked: true,
                tabs: config.tabs.map(t => {
                    // Spread the saved state from initialState onto the tab object itself,
                    // making it consistent with how windows are restored.
                    const tabProps = { ...t, ...(t.initialState || {}) };
                    tabProps.component = componentMap[t.componentType];
                    tabProps.id = t.originalId;
                    return tabProps;
                }),
                notice: null, // Backed windows don't have notices for now
                minimized: false, // Backed windows can't be minimized
                // Pass the full backed window object for the context menu
                backedWindowObject: bw,
            };
        });

        return [...frontWindows, ...mappedBackedWindows];
    })();
    // *** MODIFICATION END ***

    const initialSettings = get(desktopSettings);
    desktopView.set({
        panX: initialSettings.panX,
        panY: initialSettings.panY,
        zoom: initialSettings.zoom,
    });
    // windowView is initialized in desktop.js

    let innerWidth, innerHeight, desktopWidth, desktopHeight;
    let totalContentBounds;
    let desktopEl;
    let backedComponentInstances = {};
    let backedWindowMiddleClickTimeout = new Map();
    let backedWindowLeftClickTimeout = new Map();

    let taskbarHeight;
    $: taskbarHeight = $desktopSettings.sky?.frame?.height ?? TASKBAR_HEIGHT;

    // --- Backed Window Interaction State ---
    let interactiveBackedWindowId = null;

    // If a front window becomes active, deactivate the backed window.
    $: if ($windows.some(w => w.isActive)) {
        if (interactiveBackedWindowId !== null) {
            interactiveBackedWindowId = null;
        }
    }

    $: displayableBoxes = $boxes.filter(b => b.parent_box_id === $currentBoxId);

    $: isDesktopEmpty = allRenderableWindows.length === 0 &&
                        ($desktopShortcuts || []).length === 0 &&
                        (displayableBoxes || []).length === 0;

    // --- View Control Mode ---
    let viewControlMode = 'both'; // 'back', 'both', 'front'
    let ctrlPressed = false;
    let shiftPressed = false;

    $: displayViewControlMode = (() => {
        if ($connectionStatus !== 'connected') {
            return 'front';
        }
        // Only override when controls are visible, indicating a recent/ongoing interaction
        if (controlsVisible && (ctrlPressed || shiftPressed)) {
            if (ctrlPressed && shiftPressed) return 'both';
            if (ctrlPressed) return 'back';
            if (shiftPressed) return 'front';
        }
        return viewControlMode;
    })();

    // --- Context Menu State ---
    let contextMenu = {
        visible: false,
        x: 0,
        y: 0,
        sourceEvent: null,
    };

    // --- Backed Window Context Menu State ---
    let backedWindowContextMenu = {
        visible: false,
        x: 0,
        y: 0,
        window: null,
    };

    function showBackedWindowContextMenu(event, backedWindow) {
        closeContextMenu(); // Close the main desktop one if open
        backedWindowContextMenu = {
            visible: true,
            x: event.clientX,
            y: event.clientY,
            window: backedWindow,
        };
    }

    function closeBackedWindowContextMenu() {
        backedWindowContextMenu.visible = false;
    }

    function unbackAndRestoreWindow() {
        if (backedWindowContextMenu.window) {
            windows.unbackWindow(backedWindowContextMenu.window);
        }
        closeBackedWindowContextMenu();
    }

    let resolvedBgImageUrl = null;

    $: sceneSettings = $desktopSettings.sky?.scene;

    $: {
        if (sceneSettings?.bgType === 'image' && sceneSettings?.bgImage) {
            const urlToLoad = sceneSettings.bgImage;
            resolveAssetDataUrl(urlToLoad).then(url => {
                // Prevent race condition if user quickly changes selection
                if (get(desktopSettings).sky.scene.bgImage === urlToLoad) {
                    resolvedBgImageUrl = url;
                }
            });
        } else {
            resolvedBgImageUrl = null;
        }
    }

    $: backgroundStyle = generateBgStyle(sceneSettings, resolvedBgImageUrl);
    $: sceneOpacity = sceneSettings?.opacity ?? 1.0;
    $: backWindowBgStyle = generateBgStyle($desktopSettings.windows?.back, null); // Second param not needed here
    $: backWindowSettings = $desktopSettings.windows?.back;

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
        closeBackedWindowContextMenu();
    }

    function openSettingsMenu() {
        closeContextMenu();
        newSettings({ sourceEvent: contextMenu.sourceEvent });
    }

    function handleNewBoxClick() {
        closeContextMenu();
        const name = prompt("Enter a name for the new Box:", "New Box");
        if (!name) return;

        const context = prompt("Enter the local filesystem path for the Box:", "/");
        if (context === null) return; // User cancelled

        const event = contextMenu.sourceEvent;
        createBox(name, 'local', context, {
            screenX: event.clientX,
            screenY: event.clientY,
            parent_box_id: get(currentBoxId)
        });
    }

    function handleNewShortcutClick() {
        closeContextMenu();
        const name = prompt("Enter a name for the shortcut:", "My Shortcut");
        if (!name) return;

        let type = prompt("Enter shortcut type ('file' or 'dir'):", "dir")?.toLowerCase().trim();
        if (type !== 'file' && type !== 'dir') {
            alert("Invalid type. Please enter 'file' or 'dir'.");
            return;
        }

        const path = prompt(`Enter the path for the ${type}:`, "/");
        if (path === null) return; // User cancelled

        const event = contextMenu.sourceEvent;
        const { panX, panY, zoom } = get(desktopView);

        // Adjust for icon size so it's centered on cursor
        const iconWidth = 80 / 2;
        const iconHeight = 64 / 2;
        const worldX = ((event.clientX - panX) / zoom) - iconWidth;
        const worldY = (((event.clientY - taskbarHeight) - panY) / zoom) - iconHeight;

        desktopShortcuts.add({
            name,
            type,
            path,
            x: worldX,
            y: worldY
        });
    }

    // --- Bird's Eye View & Fit/Center Logic ---
    $: allItems = [
        ...allRenderableWindows.filter(w => !w.maximized).map(w => ({
            ...w,
            type: w.isBacked ? 'backed_window' : 'window',
            baseWidth: w.width, // for backed_window compatibility
            baseHeight: w.height,
            width: w.width * (w.scale || 1.0),
            height: w.height * (w.scale || 1.0)
        })),
        ...($desktopShortcuts || []).map(s => {
            const scale = s.scale || 1.0;
            const unscaledWidth = s.renderWidth || 90;
            const unscaledHeight = s.renderHeight || 90;
            return {
                ...s,
                type: 'shortcut',
                width: unscaledWidth * scale,
                height: unscaledHeight * scale
            };
        }),
        ...(displayableBoxes || []).map(b => {
            const BASE_WIDTH = 180;
            const scale = b.scale ?? 1.0;
            const dynamicAspectRatio = (desktopHeight > 0 && desktopWidth > 0) ? desktopHeight / desktopWidth : 0;
            const aspectRatio = b.aspect_ratio ?? dynamicAspectRatio;
            const boxWidth = BASE_WIDTH * scale;
            const boxHeight = BASE_WIDTH * aspectRatio * scale;
            return {
                ...b,
                width: boxWidth,
                height: boxHeight,
                type: 'box',
            };
        }),
    ];

    $: relativeDesktopZoom = $windowView.zoom !== 0 ? $desktopView.zoom / $windowView.zoom : 1;

    $: minimapItems = (() => {
        if (displayViewControlMode === 'back') {
            return allItems.filter(item => item.type !== 'window');
        } else if (displayViewControlMode === 'front') {
            return allItems.filter(item => item.type === 'window');
        } else { // 'both' mode
            const frontItems = allItems.filter(item => item.type === 'window');
            const relativePanX = $windowView.zoom > 0 ? ($desktopView.panX - $windowView.panX) / $windowView.zoom : 0;
            const relativePanY = $windowView.zoom > 0 ? ($desktopView.panY - $windowView.panY) / $windowView.zoom : 0;

            const backItems = allItems
                .filter(item => item.type !== 'window')
                .map(item => ({
                    ...item,
                    x: (item.x * relativeDesktopZoom) + relativePanX,
                    y: (item.y * relativeDesktopZoom) + relativePanY,
                    width: item.width * relativeDesktopZoom,
                    height: item.height * relativeDesktopZoom,
                }));
            return [...frontItems, ...backItems];
        }
    })();

    $: totalContentBounds = (() => {
        if (minimapItems.length === 0) {
            return { x: 0, y: 0, width: 0, height: 0, defined: false };
        } else {
            const minX = Math.min(...minimapItems.map(i => i.x));
            const minY = Math.min(...minimapItems.map(i => i.y));
            const maxX = Math.max(...minimapItems.map(i => i.x + i.width));
            const maxY = Math.max(...minimapItems.map(i => i.y + i.height));
            return { x: minX, y: minY, width: maxX - minX, height: maxY - minY, defined: true };
        }
    })();

    const MINIMAP_MAX_DIM = 150; // pixels
    $: minimapScale = totalContentBounds && totalContentBounds.defined && totalContentBounds.width > 0 && totalContentBounds.height > 0
        ? Math.min(MINIMAP_MAX_DIM / totalContentBounds.width, MINIMAP_MAX_DIM / totalContentBounds.height)
        : 0;

    $: minimapWidth = totalContentBounds && totalContentBounds.defined ? totalContentBounds.width * minimapScale : 0;
    $: minimapHeight = totalContentBounds && totalContentBounds.defined ? totalContentBounds.height * minimapScale : 0;

    $: backViewportRect = totalContentBounds && totalContentBounds.defined && $desktopView.zoom > 0 ? {
        x: ((displayViewControlMode === 'both' && $windowView.zoom > 0 ?
            (-$windowView.panX / $windowView.zoom) :
            (-$desktopView.panX / $desktopView.zoom)
        ) - totalContentBounds.x) * minimapScale,
        y: ((displayViewControlMode === 'both' && $windowView.zoom > 0 ?
            (-$windowView.panY / $windowView.zoom) :
            (-$desktopView.panY / $desktopView.zoom)
        ) - totalContentBounds.y) * minimapScale,
        width: ((displayViewControlMode === 'both' && $windowView.zoom > 0 ? desktopWidth / $windowView.zoom : desktopWidth / $desktopView.zoom)) * minimapScale,
        height: ((displayViewControlMode === 'both' && $windowView.zoom > 0 ? desktopHeight / $windowView.zoom : desktopHeight / $desktopView.zoom)) * minimapScale
    } : { x: 0, y: 0, width: 0, height: 0 };

    $: frontViewportRect = totalContentBounds && totalContentBounds.defined && $windowView.zoom > 0 ? {
        x: ((-$windowView.panX / $windowView.zoom) - totalContentBounds.x) * minimapScale,
        y: ((-$windowView.panY / $windowView.zoom) - totalContentBounds.y) * minimapScale,
        width: (desktopWidth / $windowView.zoom) * minimapScale,
        height: (desktopHeight / $windowView.zoom) * minimapScale
    } : { x: 0, y: 0, width: 0, height: 0 };


    // --- View Controls State & Logic ---
    let controlsVisible = false;
    let controlsTimeout;
    let isMouseOverControls = false;

    function showControls() {
        if (isDesktopEmpty) return;
        controlsVisible = true;
        if (controlsTimeout) clearTimeout(controlsTimeout);
        if (!isMouseOverControls) {
            controlsTimeout = setTimeout(() => {
                controlsVisible = false;
            }, 3000); // Linger for 3 seconds
        }
    }

    function handleControlsMouseEnter() {
        isMouseOverControls = true;
        if (controlsTimeout) clearTimeout(controlsTimeout);
    }

    function handleControlsMouseLeave() {
        isMouseOverControls = false;
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
        const mode = getCurrentMode();
        if (mode === 'back' || mode === 'both') {
            desktopView.update(view => ({
                ...view,
                panX: view.panX + dx,
                panY: view.panY + dy,
            }));
            updateDesktopSettings(get(desktopView));
        }
        if (mode === 'front' || mode === 'both') {
            windowView.update(view => ({
                ...view,
                panX: view.panX + dx,
                panY: view.panY + dy,
            }));
        }
    }

    function zoom(direction) { // 1 for in, -1 for out
        showControls();
        const mode = getCurrentMode();
        const zoomer = (view) => {
            const newZoom = Math.max(minZoom, Math.min(maxZoom, view.zoom + direction * zoomStepButton));
            if (newZoom === view.zoom) return view;

            // Zoom towards center of the screen
            const centerX = desktopWidth / 2;
            const centerY = desktopHeight / 2;

            const mouseWorldX = (centerX - view.panX) / view.zoom;
            const mouseWorldY = (centerY - view.panY) / view.zoom;

            const newPanX = centerX - mouseWorldX * newZoom;
            const newPanY = centerY - mouseWorldY * newZoom;

            return { zoom: newZoom, panX: newPanX, panY: newPanY };
        };

        if (mode === 'back' || mode === 'both') {
            desktopView.update(zoomer);
            updateDesktopSettings(get(desktopView));
        }
        if (mode === 'front' || mode === 'both') {
            windowView.update(zoomer);
        }
    }

    function resetPan() {
        showControls();
        const mode = getCurrentMode();
        if (mode === 'back' || mode === 'both') {
            desktopView.update(v => ({ ...v, panX: 0, panY: 0 }));
            updateDesktopSettings(get(desktopView));
        }
        if (mode === 'front' || mode === 'both') {
            windowView.update(v => ({ ...v, panX: 0, panY: 0 }));
        }
    }

    function resetZoom() {
        showControls();
        const mode = getCurrentMode();
        const zoomResetter = (view) => {
            if (view.zoom === 1.0) return view;
            const newZoom = 1.0;

            const centerX = desktopWidth / 2;
            const centerY = desktopHeight / 2;

            const mouseWorldX = (centerX - view.panX) / view.zoom;
            const mouseWorldY = (centerY - view.panY) / view.zoom;

            const newPanX = centerX - mouseWorldX * newZoom;
            const newPanY = centerY - mouseWorldY * newZoom;

            return { zoom: newZoom, panX: newPanX, panY: newPanY };
        };

        if (mode === 'back' || mode === 'both') {
            desktopView.update(zoomResetter);
            updateDesktopSettings(get(desktopView));
        }
        if (mode === 'front' || mode === 'both') {
            windowView.update(zoomResetter);
        }
    }

    function resetView() {
        showControls();
        const mode = getCurrentMode();
        if (mode === 'back' || mode === 'both') {
            desktopView.set({ panX: 0, panY: 0, zoom: 1.0 });
            updateDesktopSettings(get(desktopView));
        }
        if (mode === 'front' || mode === 'both') {
            windowView.set({ panX: 0, panY: 0, zoom: 1.0 });
        }
    }

    function fitAndCenterView() {
        showControls();
        const targetView = targetFitView;

        if (displayViewControlMode === 'both') {
            const currentWindowView = get(windowView);
            const currentDesktopView = get(desktopView);

            // We can only preserve the relation if window zoom is not zero.
            if (currentWindowView.zoom !== 0) {
                // targetFitView is calculated for the combined view in the front-layer's coordinate space.
                // We apply it to the front view, then derive the new back view while preserving the relative transform.
                const relativeZoom = currentDesktopView.zoom / currentWindowView.zoom;
                const relativePanX = (currentDesktopView.panX - currentWindowView.panX) / currentWindowView.zoom;
                const relativePanY = (currentDesktopView.panY - currentWindowView.panY) / currentWindowView.zoom;

                windowView.set(targetView);

                const newDesktopZoom = targetView.zoom * relativeZoom;
                const newDesktopPanX = (relativePanX * targetView.zoom) + targetView.panX;
                const newDesktopPanY = (relativePanY * targetView.zoom) + targetView.panY;

                const newDesktopView = {
                    zoom: newDesktopZoom,
                    panX: newDesktopPanX,
                    panY: newDesktopPanY,
                };
                desktopView.set(newDesktopView);
                updateDesktopSettings(newDesktopView);

            } else {
                // Fallback: Just set both to the same target view.
                desktopView.set(targetView);
                updateDesktopSettings(targetView);
                windowView.set(targetView);
            }
        } else if (displayViewControlMode === 'back') {
            desktopView.set(targetView);
            updateDesktopSettings(targetView);
        } else if (displayViewControlMode === 'front') {
            windowView.set(targetView);
        }
    }

    $: targetFitView = (() => {
        if (!totalContentBounds.defined || minimapItems.length === 0 || !desktopWidth) {
            return { panX: 0, panY: 0, zoom: 1.0 };
        }

        const PADDING = 100; // pixels in world space
        const bounds = totalContentBounds;

        const contentWidth = bounds.width + PADDING * 2;
        const contentHeight = bounds.height + PADDING * 2;

        if (contentWidth <= 0 || contentHeight <= 0) {
            return { panX: 0, panY: 0, zoom: 1.0 };
        }

        const zoomX = desktopWidth / contentWidth;
        const zoomY = desktopHeight / contentHeight;
        let newZoom = Math.min(zoomX, zoomY);

        newZoom = Math.max(minZoom, Math.min(maxZoom, newZoom)); // Clamp zoom

        const contentCenterX = bounds.x + bounds.width / 2;
        const contentCenterY = bounds.y + bounds.height / 2;

        const newPanX = (desktopWidth / 2) - (contentCenterX * newZoom);
        const newPanY = (desktopHeight / 2) - (contentCenterY * newZoom);

        return { zoom: newZoom, panX: newPanX, panY: newPanY };
    })();

    $: isBestFit = (() => {
        const checkFit = (view) => {
            return view && targetFitView &&
                (Math.abs(view.zoom - targetFitView.zoom) < 0.01 &&
                 Math.abs(view.panX - targetFitView.panX) < 1 &&
                 Math.abs(view.panY - targetFitView.panY) < 1);
        };
        if (displayViewControlMode === 'back') return checkFit($desktopView);
        if (displayViewControlMode === 'front') return checkFit($windowView);
        if (displayViewControlMode === 'both') {
            // In 'both' mode, 'fit' targets the front view and adjusts the back view
            // relatively. So, we only need to check if the front view is fit.
            return checkFit($windowView);
        }
        return false;
    })();

    // --- Dynamic Disabled States for View Controls ---
    $: isZoomResetDisabled = (() => {
        if (displayViewControlMode === 'back') return $desktopView.zoom === 1.0;
        if (displayViewControlMode === 'front') return $windowView.zoom === 1.0;
        if (displayViewControlMode === 'both') return $desktopView.zoom === 1.0 && $windowView.zoom === 1.0;
        return false;
    })();

    $: isPanResetDisabled = (() => {
        const isBackReset = $desktopView.panX === 0 && $desktopView.panY === 0;
        const isFrontReset = $windowView.panX === 0 && $windowView.panY === 0;
        if (displayViewControlMode === 'back') return isBackReset;
        if (displayViewControlMode === 'front') return isFrontReset;
        if (displayViewControlMode === 'both') return isBackReset && isFrontReset;
        return false;
    })();

    $: isViewResetDisabled = (() => {
        const isBackReset = $desktopView.panX === 0 && $desktopView.panY === 0 && $desktopView.zoom === 1.0;
        const isFrontReset = $windowView.panX === 0 && $windowView.panY === 0 && $windowView.zoom === 1.0;
        if (displayViewControlMode === 'back') return isBackReset;
        if (displayViewControlMode === 'front') return isFrontReset;
        if (displayViewControlMode === 'both') return isBackReset && isFrontReset;
        return false;
    })();


    // --- Pan and Zoom state ---
    let isPanning = false;
    let wasPanning = false;
    let pannedBackLayer = false;
    let lastMousePos = { x: 0, y: 0 };
    let saveViewTimeout;

    // --- Minimap Interaction State ---
    let isMinimapDragging = false;
    let wasMinimapDragging = false;
    let minimapLastPos = {x: 0, y: 0};
    let minimapElementRef = null;

    function handleMinimapMouseDown(event) {
        if (event.button !== 0) return; // Only left-click
        event.stopPropagation(); // Prevent desktop panning

        isMinimapDragging = true;
        wasMinimapDragging = false;
        minimapLastPos = { x: event.clientX, y: event.clientY };
        minimapElementRef = event.currentTarget; // Get ref to the birdseye-view div
        showControls();

        window.addEventListener('mousemove', handleMinimapMouseMove);
        window.addEventListener('mouseup', handleMinimapMouseUp, { once: true });
    }

    function handleMinimapMouseMove(event) {
        if (!isMinimapDragging) return;
        showControls(); // Keep controls visible while dragging
        wasMinimapDragging = true; // Any move is a drag

        const dx = event.clientX - minimapLastPos.x;
        const dy = event.clientY - minimapLastPos.y;

        if (minimapScale > 0) {
            const frontZoom = get(windowView).zoom;
            const backZoom = get(desktopView).zoom;

            if (displayViewControlMode === 'back' || displayViewControlMode === 'both') {
                const panDx = -(dx / minimapScale) * frontZoom;
                const panDy = -(dy / minimapScale) * frontZoom;

                desktopView.update(view => ({ ...view, panX: view.panX + panDx, panY: view.panY + panDy }));
            }
            if (displayViewControlMode === 'front' || displayViewControlMode === 'both') {
                // The front layer pan is always calculated with its own zoom, as the minimap
                // is either showing only front items, or is normalized to the front layer's space.
                const panDx = -(dx / minimapScale) * $windowView.zoom;
                const panDy = -(dy / minimapScale) * $windowView.zoom;

                windowView.update(view => ({ ...view, panX: view.panX + panDx, panY: view.panY + panDy }));
            }
        }

        minimapLastPos = { x: event.clientX, y: event.clientY };
    }

    function handleMinimapMouseUp(event) {
        if (!isMinimapDragging) return;

        if (wasMinimapDragging) {
            // Persist final position after drag
            if (displayViewControlMode === 'back' || displayViewControlMode === 'both') {
                updateDesktopSettings(get(desktopView));
            }
        } else if (minimapElementRef) {
            // This was a click, not a drag.
            const rect = minimapElementRef.getBoundingClientRect();
            const clickOnMinimapX = event.clientX - rect.left;
            const clickOnMinimapY = event.clientY - rect.top;

            if (minimapScale > 0) {
                // Convert click coordinates from minimap space to world space
                let clickedWorldX = (clickOnMinimapX / minimapScale) + totalContentBounds.x;
                let clickedWorldY = (clickOnMinimapY / minimapScale) + totalContentBounds.y;

                if (displayViewControlMode === 'back' || displayViewControlMode === 'both') {
                    // When in 'both' mode, the click is in the normalized (front) space.
                    // We need to convert it back to the back layer's space for that layer.
                    let backWorldX = clickedWorldX;
                    let backWorldY = clickedWorldY;
                    if (displayViewControlMode === 'both' && relativeDesktopZoom !== 0) {
                        backWorldX /= relativeDesktopZoom;
                        backWorldY /= relativeDesktopZoom;
                    }

                    const view = get(desktopView);
                    const newPanX = (desktopWidth / 2) - (backWorldX * view.zoom);
                    const newPanY = (desktopHeight / 2) - (backWorldY * view.zoom);
                    desktopView.set({ zoom: view.zoom, panX: newPanX, panY: newPanY });
                    updateDesktopSettings(get(desktopView));
                }
                if (displayViewControlMode === 'front' || displayViewControlMode === 'both') {
                    const view = get(windowView);
                    const newPanX = (desktopWidth / 2) - (clickedWorldX * view.zoom);
                    const newPanY = (desktopHeight / 2) - (clickedWorldY * view.zoom);
                    windowView.set({ zoom: view.zoom, panX: newPanX, panY: newPanY });
                }
            }
        }

        isMinimapDragging = false;
        minimapElementRef = null;
        window.removeEventListener('mousemove', handleMinimapMouseMove);
    }

    // --- Item Scaling State ---
    let scalingSession = {
        active: false,
        targetId: null,
        startStates: [],
        pushedItems: new Map(),
    };

    function handleKeyUpForScale(event) {
        if ((event.key === 'Control' || event.key === 'Alt') && scalingSession.active) {
            // Persist final positions for both scaled and pushed items.
            const finalItems = allItems.filter(item => {
                const uniqueId = `${item.type}-${item.id}`;
                return uniqueId === scalingSession.targetId || scalingSession.pushedItems.has(uniqueId);
            });

            finalItems.forEach(item => {
                if (item.type === 'box') {
                    updateBoxTransform(item.id, item.x, item.y, item.scale);
                } else if (item.type === 'shortcut') {
                    updateShortcutTransform(item.id, item.x, item.y, item.scale || 1.0);
                } else if (item.type === 'backed_window') {
                    updateBackedWindowTransform(item.originalBackedId || item.id, item.x, item.y, item.scale);
                }
            });

            // Reset session
            scalingSession.active = false;
            scalingSession.targetId = null;
        }
    }

    function handleItemScaleRequest(event) {
        const { id, type, newScale } = event.detail;
        const uniqueId = `${type}-${id}`;

        // Start a new session if not active or if the target item has changed.
        if (!scalingSession.active || scalingSession.targetId !== uniqueId) {
            scalingSession.active = true;
            scalingSession.targetId = uniqueId;
            scalingSession.startStates = allItems.map(i => ({ ...i }));
            scalingSession.pushedItems.clear();
        }

        // 1. Create a working copy from start states and apply the new scale.
        let frameItems = scalingSession.startStates.map(i => ({ ...i }));
        const sourceItem = frameItems.find(i => `${i.type}-${i.id}` === uniqueId);
        if (!sourceItem) return;

        sourceItem.scale = newScale;

        if (type === 'shortcut') {
            const unscaledWidth = sourceItem.renderWidth || 90;
            const unscaledHeight = sourceItem.renderHeight || 90;
            sourceItem.width = unscaledWidth * newScale;
            sourceItem.height = unscaledHeight * newScale;
        } else if (type === 'box') {
            const BASE_WIDTH = 180;
            // Use stored aspect ratio from the item being scaled.
            const dynamicAspectRatio = (desktopHeight > 0 && desktopWidth > 0) ? desktopHeight / desktopWidth : 0;
            const aspectRatio = sourceItem.aspect_ratio ?? dynamicAspectRatio;
            sourceItem.width = BASE_WIDTH * newScale;
            sourceItem.height = BASE_WIDTH * aspectRatio * newScale;
        } else if (type === 'backed_window') {
            sourceItem.width = sourceItem.baseWidth * newScale;
            sourceItem.height = sourceItem.baseHeight * newScale;
        }

        // 2. Resolve collisions.
        const activeItemIds = new Set([uniqueId]);
        const updatedFrameItems = resolveCollisions(
            frameItems,
            activeItemIds,
            scalingSession.startStates,
            scalingSession.pushedItems
        );

        // 3. Update stores for live preview.
        const itemsToUpdate = new Set([...activeItemIds, ...scalingSession.pushedItems.keys()]);
        updateStoresAfterCollision(updatedFrameItems, itemsToUpdate);
    }

    // --- Selection and Dragging State ---
    let isSelecting = false;
    let isDraggingItems = false;
    let selectionRect = { visible: false, x1: 0, y1: 0, x2: 0, y2: 0 };
    let dragStartData = { mouse: { x: 0, y: 0 }, items: new Map(), button: 0 };
    let dragStartItemStates = [];
    let pushedItemsOriginalPositions = new Map();

    // Helper to get the visual bounding box of an item, accounting for transforms
    const getItemBoundingBox = (item) => {
        let box = { x: item.x, y: item.y, width: item.width, height: item.height };

        if (item.type === 'shortcut') {
            const scale = item.scale || 1.0;
            if (scale === 1.0) return box;

            // item.width and item.height are already scaled. To get unscaled, we divide by scale.
            const unscaledWidth = item.width / scale;
            const unscaledHeight = item.height / scale;

            const offsetX = (unscaledWidth / 2) * (1 - scale);
            const offsetY = (unscaledHeight / 2) * (1 - scale);

            box.x = item.x + offsetX;
            box.y = item.y + offsetY;
        }

        return box;
    };


    let desktopMiddleClickTimeout;

    function toggleSkyCloak() {
        skyCloakEnabled.update(v => !v);
    }

    function handleDesktopMiddleClick(event) {
        event.preventDefault();

        // Double-click detection
        if (desktopMiddleClickTimeout) {
            clearTimeout(desktopMiddleClickTimeout);
            desktopMiddleClickTimeout = null;
            toggleSkyCloak();
            return;
        }

        // Set a timeout to clear the double-click state. If another click
        // arrives before this, it's a double-click.
        desktopMiddleClickTimeout = setTimeout(() => {
            desktopMiddleClickTimeout = null;
        }, 250);

        // Drag detection: if the mouse moves, cancel the double-click timer and start panning.
        const onMove = () => {
            clearTimeout(desktopMiddleClickTimeout);
            desktopMiddleClickTimeout = null;
            handleDesktopPanStart(event);
        };

        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
        };

        window.addEventListener('mousemove', onMove, { once: true });
        window.addEventListener('mouseup', onUp, { once: true });
    }

    // --- MODIFICATION START: Updated Global Mouse Down Handler ---
    function handleGlobalMouseDown(event) {
        if (event.target.closest('.window-wrapper:not(.backed)')) {
            // A click landed on a front window. Window.svelte's handlers run first.
            // If it was a middle click that Window.svelte decided not to handle (e.g., no scrollable content),
            // the event will bubble here. In that case, we treat it as a desktop pan.
            if (event.button === 1) {
                handleDesktopMiddleClick(event);
            }
            // For any click on a front window, we don't want the logic below (unfocusing, etc) to run.
            // Window.svelte is responsible for its own focus management.
            return;
        }

        const targetItemEl = event.target.closest('.shortcut, .box, .window-wrapper.backed');

        // Clicking anything other than a front window (and not a middle click)
        // should clear front window focus.
        if (event.button !== 1) {
            windows.unfocusAllWindows();
        }

        // If we're not clicking on a backed window itself (and not a middle click),
        // clear the active backed window.
        if (event.button !== 1 && (!targetItemEl || targetItemEl.dataset.type !== 'backed_window')) {
            interactiveBackedWindowId = null;
        }

        if (targetItemEl) {
            handleItemMouseDown(event, targetItemEl);
        } else {
            // This is a click on the desktop background.
            if (event.target.classList.contains('desktop-background')) {
                if (event.button === 1) { // Middle mouse for panning
                    handleDesktopMiddleClick(event);
                } else if (event.button === 0) { // Left mouse for selection
                    handleMarqueeSelectStart(event);
                }
            }
        }
    }
    // --- MODIFICATION END ---

    function startItemDrag(event, itemEl) {
        const id = itemEl.dataset.id;
        const type = itemEl.dataset.type;
        const uniqueId = `${type}-${id}`;

        if (event.button !== 0 && event.button !== 1) {
            desktopInteraction.set(false);
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (event.button === 0) {
            if (event.ctrlKey) {
                selectedItems.update(s => {
                    const newSet = new Set(s);
                    if (newSet.has(uniqueId)) {
                        newSet.delete(uniqueId);
                    } else {
                        newSet.add(uniqueId);
                    }
                    return newSet;
                });
            } else if (!get(selectedItems).has(uniqueId)) {
                selectedItems.set(new Set([uniqueId]));
            }
        }

        dragStartData.button = event.button;

        isDraggingItems = true;
        dragStartItemStates = allItems.map(i => ({ ...i }));
        pushedItemsOriginalPositions.clear();

        const { panX, panY, zoom } = get(desktopView);
        dragStartData.mouse = {
            x: (event.clientX - panX) / zoom,
            y: ((event.clientY - taskbarHeight) - panY) / zoom
        };

        dragStartData.items.clear();

        if (event.button === 0) {
            get(selectedItems).forEach(selUniqueId => {
                const [itemType, itemId] = selUniqueId.split('-');
                const item = allItems.find(i => i.type === itemType && String(i.id) === itemId);
                if (item) {
                    dragStartData.items.set(selUniqueId, { x: item.x, y: item.y, type: item.type, scale: item.scale });
                }
            });
        } else { // event.button === 1
            const item = allItems.find(i => i.type === type && String(i.id) === id);
            if (item) {
                dragStartData.items.set(uniqueId, { x: item.x, y: item.y, type: item.type, scale: item.scale });
            }
        }

        window.addEventListener('mousemove', handleItemDragMove);
        window.addEventListener('mouseup', handleItemDragEnd, { once: true });
    }

    function handleItemMouseDown(event, itemEl) {
        const id = itemEl.dataset.id;
        const type = itemEl.dataset.type;
        const isInteractive = type === 'backed_window' && parseInt(id, 10) === interactiveBackedWindowId;

        if (type === 'backed_window' && event.shiftKey && event.button === 1) {
            event.preventDefault();
            event.stopPropagation();
            const backedWindow = $backedWindows.find(bw => (bw.originalGroupId || bw.id) == id);
            if (backedWindow) {
                windows.unbackWindow(backedWindow);
            }
            return;
        }

        const backedWindowItem = (type === 'backed_window') ? $backedWindows.find(bw => (bw.originalGroupId || bw.id) == id) : null;
        const isCloaked = backedWindowItem ? backedWindowItem.config.cloaked : false;

        if (type === 'backed_window' && event.button === 1) {
            if (backedWindowMiddleClickTimeout.has(id)) {
                clearTimeout(backedWindowMiddleClickTimeout.get(id));
                backedWindowMiddleClickTimeout.delete(id);
                event.preventDefault();
                event.stopPropagation();

                if (backedWindowItem) {
                    const newConfig = { ...backedWindowItem.config, cloaked: !isCloaked };
                    updateBackedWindowTransform(backedWindowItem.id, backedWindowItem.x, backedWindowItem.y, backedWindowItem.scale, newConfig);
                }
                return;
            }
            const timeoutId = setTimeout(() => backedWindowMiddleClickTimeout.delete(id), 250);
            backedWindowMiddleClickTimeout.set(id, timeoutId);
        }

        if (isInteractive && isCloaked && event.button === 0) {
            if (backedWindowLeftClickTimeout.has(id)) {
                clearTimeout(backedWindowLeftClickTimeout.get(id));
                backedWindowLeftClickTimeout.delete(id);
                event.preventDefault();
                event.stopPropagation();

                if (backedWindowItem) {
                    const newConfig = { ...backedWindowItem.config, cloaked: false };
                    updateBackedWindowTransform(backedWindowItem.id, backedWindowItem.x, backedWindowItem.y, backedWindowItem.scale, newConfig);
                }
                return;
            }
            const timeoutId = setTimeout(() => backedWindowLeftClickTimeout.delete(id), 250);
            backedWindowLeftClickTimeout.set(id, timeoutId);
        }

        const isTitleBarClick = !!event.target.closest('.title-bar');
        if (isInteractive && event.button !== 1) {
            if (!isCloaked && !isTitleBarClick) return;
        }

        desktopInteraction.set(true);

        // For middle-click, use "drag-on-move" pattern to prevent choppiness from browser interference.
        if (event.button === 1) {
            event.preventDefault();
            event.stopPropagation();

            const onMove = () => {
                window.removeEventListener('mouseup', onUp); // A drag has started, the real dragEnd handler will take over.
                if (backedWindowMiddleClickTimeout.has(id)) {
                    clearTimeout(backedWindowMiddleClickTimeout.get(id));
                    backedWindowMiddleClickTimeout.delete(id);
                }
                handleDesktopPanStart(event);
            };

            const onUp = () => {
                window.removeEventListener('mousemove', onMove);
                desktopInteraction.set(false); // It was just a click, reset state.
            };

            window.addEventListener('mousemove', onMove, { once: true });
            window.addEventListener('mouseup', onUp, { once: true });
            return;
        }

        // For left-click, start the drag immediately.
        startItemDrag(event, itemEl);
    }

    function resolveCollisions(frameItems, activeItemIds, startStates, pushedItemsMap) {
        const MAX_ITERATIONS = 30; // Safety break for complex chain reactions

        const isColliding = (boxA, boxB) => (
            boxA.x < boxB.x + boxB.width &&
            boxA.x + boxA.width > boxB.x &&
            boxA.y < boxB.y + boxB.height &&
            boxA.y + boxA.height > boxB.y
        );

        for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
            let collisionsFound = 0;

            for (let i = 0; i < frameItems.length; i++) {
                for (let j = i + 1; j < frameItems.length; j++) {
                    const itemA = frameItems[i];
                    const itemB = frameItems[j];

                    const boxA = getItemBoundingBox(itemA);
                    const boxB = getItemBoundingBox(itemB);

                    if (!isColliding(boxA, boxB)) continue;

                    collisionsFound++;

                    const uniqueIdA = `${itemA.type}-${itemA.id}`;
                    const uniqueIdB = `${itemB.type}-${itemB.id}`;

                    const isAActive = activeItemIds.has(uniqueIdA);
                    const isBActive = activeItemIds.has(uniqueIdB);

                    // Items in the active set (e.g., dragged together) don't push each other.
                    if (isAActive && isBActive) continue;

                    const originalA = startStates.find(s => `${s.type}-${s.id}` === uniqueIdA);
                    const originalB = startStates.find(s => `${s.type}-${s.id}` === uniqueIdB);

                    // Safeguard against missing original states.
                    if (!originalA || !originalB) {
                        continue;
                    }

                    const hasAMoved = Math.abs(itemA.x - originalA.x) > 0.1 || Math.abs(itemA.y - originalA.y) > 0.1;
                    const hasBMoved = Math.abs(itemB.x - originalB.x) > 0.1 || Math.abs(itemB.y - originalB.y) > 0.1;

                    let pusher, pushed, pusherBox, pushedBox;

                    if (isAActive) {
                        [pusher, pushed, pusherBox, pushedBox] = [itemA, itemB, boxA, boxB];
                    } else if (isBActive) {
                        [pusher, pushed, pusherBox, pushedBox] = [itemB, itemA, boxB, boxA];
                    } else if (hasAMoved && !hasBMoved) {
                        [pusher, pushed, pusherBox, pushedBox] = [itemA, itemB, boxA, boxB];
                    } else if (!hasAMoved && hasBMoved) {
                        [pusher, pushed, pusherBox, pushedBox] = [itemB, itemA, boxB, boxA];
                    } else if (hasAMoved && hasBMoved) {
                        const displacementA = Math.hypot(itemA.x - originalA.x, itemA.y - originalA.y);
                        const displacementB = Math.hypot(itemB.x - originalB.x, itemB.y - originalB.y);

                        if (displacementA > displacementB) {
                            [pusher, pushed, pusherBox, pushedBox] = [itemA, itemB, boxA, boxB];
                        } else {
                            [pusher, pushed, pusherBox, pushedBox] = [itemB, itemA, boxB, boxA];
                        }
                    } else {
                        // The remaining case is !hasAMoved && !hasBMoved (two static, overlapping items).
                        continue;
                    }

                    const pushedUniqueId = `${pushed.type}-${pushed.id}`;
                    if (!pushedItemsMap.has(pushedUniqueId)) {
                        pushedItemsMap.set(pushedUniqueId, { x: pushed.x, y: pushed.y });
                    }

                    const overlapX = Math.min(pusherBox.x + pusherBox.width, pushedBox.x + pushedBox.width) - Math.max(pusherBox.x, pushedBox.x);
                    const overlapY = Math.min(pusherBox.y + pusherBox.height, pushedBox.y + pushedBox.height) - Math.max(pusherBox.y, pushedBox.y);

                    if (overlapX < overlapY) {
                        const sign = Math.sign((pushedBox.x + pushedBox.width / 2) - (pusherBox.x + pusherBox.width / 2));
                        pushed.x += overlapX * (sign || 1);
                    } else {
                        const sign = Math.sign((pushedBox.y + pushedBox.height / 2) - (pusherBox.y + pusherBox.height / 2));
                        pushed.y += overlapY * (sign || 1);
                    }
                }
            }

            if (collisionsFound === 0) break;
        }
        return frameItems;
    }

    function updateStoresAfterCollision(frameItems, itemsToUpdate) {
        const newBoxPositions = new Map();
        const newShortcutPositions = new Map();
        const newBackedWindowPositions = new Map();

        frameItems.forEach(item => {
            const uniqueId = `${item.type}-${item.id}`;
            if (itemsToUpdate.has(uniqueId)) {
                const pos = { x: Math.round(item.x), y: Math.round(item.y), scale: item.scale };
                const idStr = String(item.id);

                if (item.type === 'box') {
                    newBoxPositions.set(idStr, pos);
                } else if (item.type === 'shortcut') {
                    newShortcutPositions.set(idStr, pos);
                } else if (item.type === 'backed_window') {
                    newBackedWindowPositions.set(String(item.originalBackedId || item.id), pos);
                }
            }
        });

        if (newBoxPositions.size > 0) {
            boxes.update(all => all.map(b => newBoxPositions.has(String(b.id)) ? { ...b, ...newBoxPositions.get(String(b.id)) } : b));
        }
        if (newShortcutPositions.size > 0) {
            desktopShortcuts.update(all => all.map(s => newShortcutPositions.has(String(s.id)) ? { ...s, ...newShortcutPositions.get(String(s.id)) } : s));
        }
        if (newBackedWindowPositions.size > 0) {
            backedWindows.update(all => all.map(bw => newBackedWindowPositions.has(String(bw.id)) ? { ...bw, ...newBackedWindowPositions.get(String(bw.id)) } : bw));
        }
    }

    function handleItemDragMove(event) {
        if (!isDraggingItems) return;

        if (!get(wasDraggingItems)) {
            // On first move, cancel any pending double-click actions and set the dragging flag/cursor
            backedWindowMiddleClickTimeout.forEach(timeout => clearTimeout(timeout));
            backedWindowMiddleClickTimeout.clear();
            backedWindowLeftClickTimeout.forEach(timeout => clearTimeout(timeout));
            backedWindowLeftClickTimeout.clear();
            document.body.classList.add('is-dragging-item');
            wasDraggingItems.set(true);
        }

        const { panX, panY, zoom } = get(desktopView);
        const mouseNow = {
            x: (event.clientX - panX) / zoom,
            y: ((event.clientY - taskbarHeight) - panY) / zoom
        };
        const dx = mouseNow.x - dragStartData.mouse.x;
        const dy = mouseNow.y - dragStartData.mouse.y;

        // 1. Create a working copy and apply user drag delta
        let frameItems = dragStartItemStates.map(i => ({...i}));
        const draggedItemIds = new Set(dragStartData.items.keys());

        frameItems.forEach(item => {
            const uniqueId = `${item.type}-${item.id}`;
            if (draggedItemIds.has(uniqueId)) {
                const initial = dragStartData.items.get(uniqueId);
                item.x = initial.x + dx;
                item.y = initial.y + dy;
            }
        });

        // 2. Iteratively resolve collisions
        const updatedFrameItems = resolveCollisions(
            frameItems,
            draggedItemIds,
            dragStartItemStates,
            pushedItemsOriginalPositions
        );

        // 3. Update Svelte stores for any items that have been part of the drag interaction
        const itemsToUpdate = new Set([...draggedItemIds, ...pushedItemsOriginalPositions.keys()]);
        updateStoresAfterCollision(updatedFrameItems, itemsToUpdate);
    }

    function handleItemDragEnd() {
        desktopInteraction.set(false);
        document.body.classList.remove('is-dragging-item');
        if (get(wasDraggingItems)) {
            // Persist final positions for both dragged and pushed items.
            const finalItems = allItems.filter(item => {
                const uniqueId = `${item.type}-${item.id}`;
                return dragStartData.items.has(uniqueId) || pushedItemsOriginalPositions.has(uniqueId);
            });

            finalItems.forEach(item => {
                if (item.type === 'box') {
                    updateBoxTransform(item.id, item.x, item.y, item.scale);
                } else if (item.type === 'shortcut') {
                    updateShortcutTransform(item.id, item.x, item.y, item.scale || 1.0);
                } else if (item.type === 'backed_window') {
                    updateBackedWindowTransform(item.originalBackedId || item.id, item.x, item.y, item.scale);
                }
            });
        } else if (dragStartData.button === 0) {
            // This was a click (not a drag), and it was a left-click. Activate the window.
            const selected = [...dragStartData.items.keys()];
            if (selected.length === 1 && selected[0].startsWith('backed_window-')) {
                const [_, idStr] = selected[0].split('-');
                interactiveBackedWindowId = parseInt(idStr, 10);
                windows.unfocusAllWindows();
            }
        }

        isDraggingItems = false;
        dragStartItemStates = [];
        pushedItemsOriginalPositions.clear();
        window.removeEventListener('mousemove', handleItemDragMove);
        setTimeout(() => wasDraggingItems.set(false), 0);
    }

    function handleMarqueeSelectStart(event) {
        desktopInteraction.set(true);
        isSelecting = true;
        wasDraggingItems.set(false);

        selectionRect = {
            visible: true,
            x1: event.clientX,
            y1: event.clientY,
            x2: event.clientX,
            y2: event.clientY
        };

        if (!event.ctrlKey) {
            selectedItems.set(new Set());
        }

        window.addEventListener('mousemove', handleMarqueeSelectMove);
        window.addEventListener('mouseup', handleMarqueeSelectEnd, { once: true });
    }

    function handleMarqueeSelectMove(event) {
        if (!isSelecting) return;
        wasDraggingItems.set(true);
        selectionRect.x2 = event.clientX;
        selectionRect.y2 = event.clientY;
    }

    function handleMarqueeSelectEnd() {
        desktopInteraction.set(false);
        if (!isSelecting) return;

        const { panX, panY, zoom } = get(desktopView);
        const x1 = (Math.min(selectionRect.x1, selectionRect.x2) - panX) / zoom;
        const y1 = ((Math.min(selectionRect.y1, selectionRect.y2) - taskbarHeight) - panY) / zoom;
        const x2 = (Math.max(selectionRect.x1, selectionRect.x2) - panX) / zoom;
        const y2 = ((Math.max(selectionRect.y1, selectionRect.y2) - taskbarHeight) - panY) / zoom;

        const currentlySelected = get(selectedItems);
        const newlySelected = new Set(currentlySelected);

        allItems.forEach(item => {
            if (item.type === 'box' || item.type === 'shortcut' || item.type === 'backed_window') {
                const box = getItemBoundingBox(item);
                const itemRight = box.x + box.width;
                const itemBottom = box.y + box.height;
                // Check for intersection
                if (box.x < x2 && itemRight > x1 && box.y < y2 && itemBottom > y1) {
                    newlySelected.add(`${item.type}-${item.id}`);
                }
            }
        });

        selectedItems.set(newlySelected);

        isSelecting = false;
        selectionRect.visible = false;
        window.removeEventListener('mousemove', handleMarqueeSelectMove);
        setTimeout(() => wasDraggingItems.set(false), 0);
    }

    function getEffectiveMode(event, baseMode) {
        // During pan/zoom, modifier keys can temporarily override the mode
        if (event.ctrlKey && event.shiftKey) return 'both';
        if (event.ctrlKey) return 'back';
        if (event.shiftKey) return 'front';
        return baseMode;
    }

    function getCurrentMode(event = null) {
        if (get(connectionStatus) !== 'connected') {
            return 'front';
        }
        // During pan/zoom, modifier keys can temporarily override the mode
        if (event) {
            if (event.ctrlKey && event.shiftKey) return 'both';
            if (event.ctrlKey) return 'back';
            if (event.shiftKey) return 'front';
        }
        return viewControlMode;
    }

    function handleDesktopPanStart(event) {
        if (isDesktopEmpty) return;
        // The check for the correct target is now in handleGlobalMouseDown
        desktopInteraction.set(true);
        isPanning = true;
        wasPanning = false;
        pannedBackLayer = false; // Reset flag
        lastMousePos = { x: event.clientX, y: event.clientY };

        window.addEventListener('mousemove', handleDesktopMouseMove);
        window.addEventListener('mouseup', handleDesktopMouseUp, { once: true });
    }

    function handleDesktopMouseMove(event) {
        if (!isPanning) return;
        showControls();
        wasPanning = true; // If we move, it's a pan

        const dx = event.clientX - lastMousePos.x;
        const dy = event.clientY - lastMousePos.y;

        const mode = getCurrentMode(event);

        if (mode === 'back' || mode === 'both') {
            pannedBackLayer = true;
            desktopView.update(view => ({ ...view, panX: view.panX + dx, panY: view.panY + dy }));
        }
        if (mode === 'front' || mode === 'both') {
            windowView.update(view => ({ ...view, panX: view.panX + dx, panY: view.panY + dy }));
        }

        lastMousePos = { x: event.clientX, y: event.clientY };
    }

    function handleDesktopMouseUp() {
        desktopInteraction.set(false);
        if (isPanning && wasPanning) {
            // Persist final position if we actually panned
            if (pannedBackLayer) {
                updateDesktopSettings(get(desktopView));
            }
        }
        isPanning = false;
        wasPanning = false;
        window.removeEventListener('mousemove', handleDesktopMouseMove);
    }

    function handleDesktopWheel(event) {
        if (isDesktopEmpty) return;
        // Only zoom if scrolling on the desktop background itself, not on window content etc.
        if (!event.target.classList.contains('desktop-background')) return;

        event.preventDefault();
        showControls();

        const mode = getCurrentMode(event);

        const zoomer = (currentView) => {
            const zoomFactor = 0.001;
            const newZoom = Math.max(minZoom, Math.min(maxZoom, currentView.zoom - event.deltaY * zoomFactor));
            if (newZoom === currentView.zoom) return currentView;

            const mouseX = event.offsetX;
            const mouseY = event.offsetY;
            const mouseWorldX = (mouseX - currentView.panX) / currentView.zoom;
            const mouseWorldY = (mouseY - currentView.panY) / currentView.zoom;
            const newPanX = mouseX - mouseWorldX * newZoom;
            const newPanY = mouseY - mouseWorldY * newZoom;

            return { zoom: newZoom, panX: newPanX, panY: newPanY };
        };

        if (mode === 'back' || mode === 'both') {
            desktopView.update(zoomer);
        }
        if (mode === 'front' || mode === 'both') {
            windowView.update(zoomer);
        }

        // Debounce saving
        if (saveViewTimeout) clearTimeout(saveViewTimeout);
        saveViewTimeout = setTimeout(() => {
            if (mode === 'back' || mode === 'both') {
                updateDesktopSettings(get(desktopView));
            }
        }, 300);
    }

    function handleDrop(event) {
        event.preventDefault();

        const shortcutMoveData = event.dataTransfer.getData('application/sidekick-shortcut-move');
        const fsItemData = event.dataTransfer.getData('application/sidekick-fs-item');
        const { panX, panY, zoom } = get(desktopView);

        // Adjust for icon size so it's centered on cursor
        const iconWidth = 80 / 2;
        const iconHeight = 64 / 2;
        const worldX = ((event.clientX - panX) / zoom) - iconWidth;
        const worldY = (((event.clientY - taskbarHeight) - panY) / zoom) - iconHeight;

        if (shortcutMoveData) {
            try {
                const { id } = JSON.parse(shortcutMoveData);
                const shortcut = get(desktopShortcuts).find(s => s.id === id);
                const currentScale = shortcut ? shortcut.scale || 1.0 : 1.0;
                updateShortcutTransform(id, worldX, worldY, currentScale);
            } catch (e) {
                console.error("Failed to handle shortcut move drop:", e);
            }
        } else if (fsItemData) {
            try {
                const item = JSON.parse(fsItemData);
                desktopShortcuts.add({
                    ...item,
                    x: worldX,
                    y: worldY
                });
            } catch (e) {
                console.error("Failed to handle fs item drop:", e);
            }
        }
    }

    function handleBackRequest(windowToBack) {
        // 1. Generate config for the new backed window, capturing live state
        const config = generateBoardConfigFromWindow(windowToBack, get(windows));
        const frontWindow = get(windows).find(w => w.id === windowToBack.id);
        config.cloaked = frontWindow ? frontWindow.cloaked : false;
        const configStr = JSON.stringify(config);

        // Get view states for coordinate transformation
        const wv = $windowView;
        const dv = $desktopView;

        if (wv.zoom === 0 || dv.zoom === 0) {
            console.error("Cannot back window with zero zoom level.");
            return;
        }

        // Calculate the midpoint of the front window in front-layer world coordinates
        const frontWorldMidX = windowToBack.x + windowToBack.width / 2;
        const frontWorldMidY = windowToBack.y + windowToBack.height / 2;

        // Transform this midpoint to back-layer world coordinates
        const backWorldMidX = ((frontWorldMidX * wv.zoom) + wv.panX - dv.panX) / dv.zoom;
        const backWorldMidY = ((frontWorldMidY * wv.zoom) + wv.panY - dv.panY) / dv.zoom;

        const zoomFactor = dv.zoom / wv.zoom;
        const newWidth = windowToBack.width * zoomFactor;
        const newHeight = windowToBack.height * zoomFactor;

        const newX = backWorldMidX - newWidth / 2;
        const newY = backWorldMidY - newHeight / 2;

        const tempNewItem = {
            id: windowToBack.id, // Use the same ID to allow Svelte to transition the component
            type: 'backed_window',
            x: newX, y: newY,
            width: newWidth, height: newHeight,
            baseWidth: newWidth,
            baseHeight: newHeight,
            scale: 1.0,
            config: configStr,
        };

        // 2. Prepare for collision resolution
        let frameItems = [...allItems.filter(i => i.type !== 'window' && i.id !== windowToBack.id), tempNewItem];
        const activeItemIds = new Set([`backed_window-${windowToBack.id}`]);
        const startStates = frameItems.map(i => ({ ...i, config: i.config ? JSON.parse(JSON.stringify(i.config)) : undefined }));
        const pushedItemsMap = new Map();

        // 3. Resolve collisions
        const updatedFrameItems = resolveCollisions(frameItems, activeItemIds, startStates, pushedItemsMap);

        const backedItem = updatedFrameItems.find(item => item.id === windowToBack.id);
        if (!backedItem) {
            console.error("Could not find item to back after collision resolution.");
            return;
        }

        // 4. Perform an atomic, optimistic update to prevent component destruction
        backedWindows.update(bws => {
            const optimisticBackedWindow = {
                id: `temp-${Date.now()}`, // Temporary ID, will be replaced by backend response
                originalGroupId: backedItem.id,
                config: JSON.parse(backedItem.config),
                x: backedItem.x,
                y: backedItem.y,
                width: backedItem.width,
                height: backedItem.height,
                scale: backedItem.scale,
                z_index: 1, // Placeholder
            };
            return [...bws, optimisticBackedWindow];
        });
        windows.removeWindow(windowToBack.id);

        // 5. Persist all changes to the backend asynchronously
        const itemsToUpdate = new Set([...activeItemIds, ...pushedItemsMap.keys()]);
        updatedFrameItems.forEach(item => {
            const uniqueId = `${item.type}-${item.id}`;
            if (!itemsToUpdate.has(uniqueId)) return;

            if (item.id === windowToBack.id) {
                 // The originalGroupId is crucial for preserving the component instance key.
                createBackedWindow(item.config, item.x, item.y, item.width, item.height, item.scale, item.id);
            } else {
                if (item.type === 'box') {
                    updateBoxTransform(item.id, item.x, item.y, item.scale);
                } else if (item.type === 'shortcut') {
                    updateShortcutTransform(item.id, item.x, item.y, item.scale || 1.0);
                } else if (item.type === 'backed_window') {
                    updateBackedWindowTransform(item.originalBackedId || item.id, item.x, item.y, item.scale);
                }
            }
        });
    }


    onMount(() => {
        // The WebSocket connection is now established in SideKick.svelte
        window.addEventListener('click', closeContextMenu);
        window.addEventListener('click', closeBackedWindowContextMenu);
        window.addEventListener('keyup', handleKeyUpForScale);
    });
    onDestroy(() => {
        window.removeEventListener('click', closeContextMenu);
        window.removeEventListener('click', closeBackedWindowContextMenu);
        window.removeEventListener('keyup', handleKeyUpForScale);
        if (saveViewTimeout) clearTimeout(saveViewTimeout);
        if (controlsTimeout) clearTimeout(controlsTimeout);
        if (desktopMiddleClickTimeout) clearTimeout(desktopMiddleClickTimeout);
        backedWindowMiddleClickTimeout.forEach(timeout => clearTimeout(timeout));
        backedWindowLeftClickTimeout.forEach(timeout => clearTimeout(timeout));
        window.removeEventListener('mousemove', handleDesktopMouseMove);
        window.removeEventListener('mouseup', handleDesktopMouseUp);
        window.removeEventListener('mousemove', handleMinimapMouseMove);
        window.removeEventListener('mouseup', handleMinimapMouseUp);
        window.removeEventListener('mousemove', handleItemDragMove);
        window.removeEventListener('mouseup', handleItemDragEnd);
        window.removeEventListener('mousemove', handleMarqueeSelectMove);
        window.removeEventListener('mouseup', handleMarqueeSelectEnd);
    });

    $: normalizedSelectionRect = {
        left: Math.min(selectionRect.x1, selectionRect.x2),
        top: Math.min(selectionRect.y1, selectionRect.y2),
        width: Math.abs(selectionRect.x1 - selectionRect.x2),
        height: Math.abs(selectionRect.y1 - selectionRect.y2)
    };
</script>

<style>
    :global(body.is-dragging-item), :global(body.is-dragging-item *) {
        cursor: move !important;
    }
    .desktop {
        flex-grow: 1;
        position: relative;
        width: 100%;
        height: 100%;
    }
    .desktop-background {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-position: center;
        transition: background 0.5s ease-in-out, opacity 0.5s ease-in-out;
        /* Fallback background color */
        background-color: var(--background-color);
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
        z-index: 23000;
        display: flex;
        flex-direction: column;
        padding: 4px 0;
        min-width: 120px;
    }

    .context-menu-separator {
        height: 1px;
        background-color: var(--border-color);
        margin: 4px 0;
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

    .context-menu button:not(:disabled):hover {
        background-color: var(--taskbar-button-hover-bg);
    }

    .context-menu button:disabled {
        color: var(--text-color-light);
        cursor: not-allowed;
        opacity: 0.5;
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

    .shortcuts-layer {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none;
    }

    .boxes-layer {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none; /* Parent container is not interactive */
    }
    .boxes-layer > :global(*), .shortcuts-layer > :global(*) {
        pointer-events: auto; /* Children (boxes, shortcuts) are interactive */
    }
    /* MODIFIED */
    .windows-container {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
    }
    .windows-container > :global(*) {
        pointer-events: auto;
    }

    .selection-box {
        position: fixed;
        border: 1px solid rgba(52, 152, 219, 0.8);
        background-color: rgba(52, 152, 219, 0.2);
        z-index: 9999;
        pointer-events: none;
    }

    /* --- View Controls --- */
    .view-controls {
        position: absolute;
        top: 20px;
        right: 20px;
        z-index: 22000;
        display: flex;
        flex-direction: column;
        align-items: center;
        backdrop-filter: blur(5px);
        gap: 8px;
        border-radius: 8px;
        padding: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    .view-mode-controls {
        display: flex;
        background-color: rgba(40, 40, 40, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        overflow: hidden;
        width: 100%;
    }

    .view-mode-controls button {
        flex-grow: 1;
        background: none;
        border: none;
        color: white;
        padding: 6px 0;
        cursor: pointer;
        font-size: 12px;
        transition: background-color: 0.2s;
        height: auto;
        width: auto;
        border-radius: 0;
    }

    .view-mode-controls button:not(:last-child) {
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }

    .view-mode-controls button.active {
        background-color: rgba(255, 255, 255, 0.2);
        font-weight: bold;
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

    .action-controls {
        display: flex;
        width: 100%;
        justify-content: space-between;
    }

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
        transition: background-color: 0.2s, opacity: 0.2s;
    }
    .view-controls button:not(:disabled):hover {
        background-color: rgba(255, 255, 255, 0.2);
    }
    .view-controls button:not(:disabled):active {
        background-color: rgba(255, 255, 255, 0.3);
    }
    .view-controls button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .view-controls .zoom-reset {
        width: auto;
        padding: 0 8px;
        font-size: 14px;
    }

    /* --- Bird's Eye View --- */
    .birdseye-view {
        position: relative;
        background-color: rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 4px;
        overflow: hidden;
        flex-shrink: 0;
        cursor: pointer; /* To indicate it's interactive */
    }

    .birdseye-item {
        position: absolute;
        background-color: rgba(255,255,255,0.3);
        border: 1px solid rgba(255,255,255,0.5);
        box-sizing: border-box;
    }

    .birdseye-item.window {
        background-color: rgba(100, 150, 255, 0.4);
        border-color: rgba(100, 150, 255, 0.7);
    }

    .birdseye-viewport {
        position: absolute;
        border: 1px solid #f39c12; /* Orange, stands out */
        box-sizing: border-box;
        pointer-events: none;
    }
    .birdseye-viewport.front {
        border: 1px solid #3498db; /* Blue for front layer */
    }
</style>

<svelte:window
    bind:innerWidth
    bind:innerHeight
    on:keydown={e => {
        if (e.key === 'Control' && !e.repeat) ctrlPressed = true;
        if (e.key === 'Shift' && !e.repeat) shiftPressed = true;
    }}
    on:keyup={e => {
        if (e.key === 'Control') ctrlPressed = false;
        if (e.key === 'Shift') shiftPressed = false;
    }}
    on:blur={() => {
        ctrlPressed = false;
        shiftPressed = false;
    }}
/>

<div class="desktop" bind:this={desktopEl} bind:clientWidth={desktopWidth} bind:clientHeight={desktopHeight} class:dash-active={$dashActive} on:contextmenu|preventDefault={handleRightClick} on:mousedown={handleGlobalMouseDown} on:wheel={handleDesktopWheel} on:dragover|preventDefault on:drop={handleDrop} style="overflow: hidden;">
    <div class="desktop-background" style:background={backgroundStyle || ''} style:opacity={sceneOpacity}></div>
    <!-- BACK LAYER (for non-window items) -->
    <div class="desktop-content back-layer">
        {#if $connectionStatus === 'connected'}
            <div class="shortcuts-layer" style:z-index={$activeBoxId !== null ? 0 : 'auto'}>
                {#each $desktopShortcuts as shortcut (shortcut.id)}
                    <Shortcut {...shortcut} on:scale={e => handleItemScaleRequest({ detail: { ...e.detail, type: 'shortcut' } })}/>
                {/each}
            </div>
            <div class="boxes-layer">
                {#each displayableBoxes as box (box.id)}
                    <Box {box} on:scale={e => handleItemScaleRequest({ detail: { ...e.detail, type: 'box' } })}/>
                {/each}
            </div>
        {/if}
    </div>

    <!-- UNIFIED WINDOWS CONTAINER -->
    <div class="windows-container">
        {#each allRenderableWindows as win (win.id)}
            <Window
                {...win}
                on:backrequest={() => handleBackRequest(win)}
                on:contextmenubacked={(event) => showBackedWindowContextMenu(event, win.backedWindowObject)}
                on:backedmouseenterfocus={() => {
                    interactiveBackedWindowId = win.id;
                    windows.unfocusAllWindows();
                }}
                on:wheelbacked={e => {
                    if (e.ctrlKey || e.altKey) {
                        e.preventDefault();
                        const zoomStep = 0.05;
                        const delta = e.deltaY < 0 ? zoomStep : -zoomStep;
                        const newScale = Math.max(0.2, win.scale + delta);
                        handleItemScaleRequest({ detail: { id: win.id, newScale, type: 'backed_window' } });
                    }
                }}
            />
        {/each}
    </div>

    {#if selectionRect.visible}
        <div
            class="selection-box"
            style:left="{normalizedSelectionRect.left}px"
            style:top="{normalizedSelectionRect.top}px"
            style:width="{normalizedSelectionRect.width}px"
            style:height="{normalizedSelectionRect.height}px"
        />
    {/if}

    {#if controlsVisible}
        <div class="view-controls" transition:fade={{ duration: 142 }} on:mouseenter={handleControlsMouseEnter} on:mouseleave={handleControlsMouseLeave}>
            {#if $connectionStatus === 'connected'}
                <div class="view-mode-controls">
                    <button class:active={displayViewControlMode === 'back'} on:click={() => viewControlMode = 'back'}>Back</button>
                    <button class:active={displayViewControlMode === 'both'} on:click={() => viewControlMode = 'both'}>Both</button>
                    <button class:active={displayViewControlMode === 'front'} on:click={() => viewControlMode = 'front'}>Front</button>
                </div>
            {/if}
            {#if totalContentBounds && totalContentBounds.defined && minimapWidth > 0 && minimapHeight > 0}
                <div class="birdseye-view" style:width="{minimapWidth}px" style:height="{minimapHeight}px" on:mousedown={handleMinimapMouseDown}>
                    <!-- Items -->
                    {#each minimapItems as item (`${item.type}-${item.id}`)}
                        <div
                            class="birdseye-item"
                            class:window={item.type === 'window'}
                            style:left="{(item.x - totalContentBounds.x) * minimapScale}px"
                            style:top="{(item.y - totalContentBounds.y) * minimapScale}px"
                            style:width="{item.width * minimapScale}px"
                            style:height="{item.height * minimapScale}px"
                        />
                    {/each}
                    <!-- Viewports -->
                    {#if displayViewControlMode === 'back' || displayViewControlMode === 'both'}
                        <div
                            class="birdseye-viewport back"
                            style:left="{backViewportRect.x}px"
                            style:top="{backViewportRect.y}px"
                            style:width="{backViewportRect.width}px"
                            style:height="{backViewportRect.height}px"
                        />
                    {/if}
                    {#if displayViewControlMode === 'front' || displayViewControlMode === 'both'}
                         <div
                            class="birdseye-viewport front"
                            style:left="{frontViewportRect.x}px"
                            style:top="{frontViewportRect.y}px"
                            style:width="{frontViewportRect.width}px"
                            style:height="{frontViewportRect.height}px"
                        />
                    {/if}
                </div>
            {/if}
            <div class="zoom-controls">
                <button on:click={() => zoom(-1)} title="Zoom Out">-</button>
                <button class="zoom-reset" on:click={resetZoom} title="Reset Zoom" disabled={isZoomResetDisabled}>1:1</button>
                <button on:click={() => zoom(1)} title="Zoom In">+</button>
            </div>
            <div class="pan-controls">
                <button class="pan-up" on:click={() => pan(0, panStep)} title="Pan Up">▲</button>
                <button class="pan-left" on:click={() => pan(panStep, 0)} title="PaLeft">◀</button>
                <button class="pan-reset" on:click={resetPan} title="Reset Pan" disabled={isPanResetDisabled}>●</button>
                <button class="pan-right" on:click={() => pan(-panStep, 0)} title="Pan Right">▶</button>
                <button class="pan-down" on:click={() => pan(0, -panStep)} title="Pan Down">▼</button>
            </div>
            <div class="action-controls">
                <button class="zoom-reset" on:click={resetView} title="Reset View" disabled={isViewResetDisabled}>Reset</button>
                <button class="zoom-reset" on:click={fitAndCenterView} title="Fit to C" disabled={isBestFit}>Fit</button>
            </div>
        </div>
    {/if}

    {#if contextMenu.visible && !wasPanning}
        <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
            <button on:click={handleNewBoxClick} disabled={$connectionStatus !== 'connected'} title={$connectionStatus !== 'connected' ? 'SKYBRIDGE REQUIRED' : null}>New Box</button>
            <button on:click={handleNewShortcutClick} disabled={$connectionStatus !== 'connected'} title={$connectionStatus !== 'connected' ? 'SKYBRIDGE REQUIRED' : null}>New Shortcut</button>
            <div class="context-menu-separator"></div>
            <button on:click={openSettingsMenu}>Settings...</button>
        </div>
    {/if}

    {#if backedWindowContextMenu.visible}
        <div class="context-menu" style="top: {backedWindowContextMenu.y}px; left: {backedWindowContextMenu.x}px;" on:click|stopPropagation>
            <button on:click={unbackAndRestoreWindow}>Restore Window</button>
        </div>
    {/if}

    {#if $dashActive}
        <Dash />
    {/if}
</div>

