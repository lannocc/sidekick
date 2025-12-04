import { writable, get, readable } from 'svelte/store';
import IoskConsole from './IoskConsole.svelte';
import Calculator from './Calculator.svelte';
import Settings from './Settings.svelte';
import IoskFileExplorer from './IoskFileExplorer.svelte';
import IoskFileViewer from './IoskFileViewer.svelte';
import WebBrowser from './WebBrowser.svelte';
import IoskPrivateChat from './IoskPrivateChat.svelte';
import LocalTerminal from './LocalTerminal.svelte';
import LocalFileExplorer from './LocalFileExplorer.svelte';
import LocalFileViewer from './LocalFileViewer.svelte';
import Ask from './Ask.svelte';
import IoskWatch from './IoskWatch.svelte';
import IoskUserInspector from './IoskUserInspector.svelte';
import NotificationCenter from './NotificationCenter.svelte';
import { TASKBAR_HEIGHT, desktopSettings, windowSettings, notificationHistory, unreadNoticeCount, desktopView, windowView } from './desktop.js';
import { createBackedWindow, deleteBackedWindow, createBox, boxes, desktopShortcuts, backedWindows } from './local.js';

let windowGroupIdCounter = 0;
let tabIdCounter = 0;

// Store for managing drag-and-drop grouping state
// Shape can be:
// null
// { draggingGroupId: number, dropTargetGroupId: number | null }
// { draggingGroupId: number, dropTargetBoxPanel: { boxId: number, location: string } | null }
export const dragState = writable(null);
// Store for requesting a drag/resize action from another component
export const dragRequest = writable(null);

// Map component type strings to actual components for restoring layouts
export const componentMap = {
    'IoskConsole': IoskConsole,
    'Calculator': Calculator,
    'Settings': Settings,
    'IoskFileExplorer': IoskFileExplorer,
    'IoskFileViewer': IoskFileViewer,
    'WebBrowser': WebBrowser,
    'IoskPrivateChat': IoskPrivateChat,
    'LocalTerminal': LocalTerminal,
    'LocalFileExplorer': LocalFileExplorer,
    'LocalFileViewer': LocalFileViewer,
    'Ask': Ask,
    'IoskWatch': IoskWatch,
    'IoskUserInspector': IoskUserInspector,
    'NotificationCenter': NotificationCenter,
};

export function getComponentType(component) {
    for (const [name, comp] of Object.entries(componentMap)) {
        if (comp === component) {
            return name;
        }
    }
    return 'Unknown';
}

function findTabById(groups, tabId) {
    if (!tabId) return null;
    for (const group of groups) {
        const tab = group.tabs.find(t => t.id === tabId);
        if (tab) return tab;
    }
    return null;
}

export function generateBoardConfigFromWindow(group, allWindows) {
    const layoutTabs = group.tabs.map(tab => {
        const associatedConsole = findTabById(allWindows, tab.consoleId);
        return {
            originalId: tab.id,
            componentType: getComponentType(tab.component),
            title: tab.title,
            maximized: group.maximized,
            wsUrl: tab.wsUrl, username: tab.username,
            localUser: tab.localUser, remoteUser: tab.remoteUser,
            consoleConnection: tab.consoleConnection || (associatedConsole ? associatedConsole.consoleConnection : null),
            initialPath: tab.currentPath, path: tab.path,
            mode: tab.mode, initialUrl: tab.currentUrl,
            zoom: tab.zoom,
            initialCommand: tab.initialCommand,
            initialPwd: tab.initialPwd,
            initialInterval: tab.initialInterval,
            initialState: tab.initialState,
            consoleId: tab.consoleId, // Keep for remapping
        };
    });
    return {
        x: group.x, y: group.y, width: group.width, height: group.height,
        maximized: group.maximized,
        activeTabId: group.activeTabId,
        tabs: layoutTabs
    };
}

function findOptimalPosition(props, allWindows, currentWindowId) {
    if (typeof window === 'undefined') {
        return { x: 50, y: 50 }; // SSR fallback
    }

    const { width, height, sourceEvent, sourceTabId } = props;
    const { panX, panY, zoom } = get(windowView);

    const obstacles = allWindows.filter(w => !w.minimized).map(w => ({
        x: w.x, y: w.y, width: w.width, height: w.height
    }));

    const checkCollision = (rect) => {
        for (const obs of obstacles) {
            if (rect.x < obs.x + obs.width &&
                rect.x + rect.width > obs.x &&
                rect.y < obs.y + obs.height &&
                rect.y + rect.height > obs.y) {
                return true;
            }
        }
        return false;
    };

    // Calculate the visible area in world coordinates
    const margin = 10; // screen pixels
    const view = {
        x: (-panX / zoom) + (margin / zoom),
        y: (-panY / zoom) + (margin / zoom),
        width: (window.innerWidth / zoom) - (2 * margin / zoom),
        height: ((window.innerHeight - TASKBAR_HEIGHT) / zoom) - (2 * margin / zoom),
    };

    const clampToView = (pos) => {
        const newX = Math.max(view.x, Math.min(pos.x, view.x + view.width - width));
        const newY = Math.max(view.y, Math.min(pos.y, view.y + view.height - height));
        return { x: newX, y: newY };
    };

    if (sourceTabId) {
        const sourceGroup = allWindows.find(g => g.tabs.some(t => t.id === sourceTabId));
        if (sourceGroup) {
            const sourceRect = { x: sourceGroup.x, y: sourceGroup.y, width: sourceGroup.width, height: sourceGroup.height };
            const positions = [
                { x: sourceRect.x + sourceRect.width + 10, y: sourceRect.y }, // Right
                { x: sourceRect.x, y: sourceRect.y + sourceRect.height + 10 }, // Below
                { x: sourceRect.x - width - 10, y: sourceRect.y }, // Left
                { x: sourceRect.x + sourceRect.width - width, y: sourceRect.y + sourceRect.height + 10 },
                { x: sourceRect.x, y: sourceRect.y - height - 10 }, // Above
            ];

            for (const pos of positions) {
                const clampedPos = clampToView(pos);
                if (!checkCollision({ ...clampedPos, width, height })) {
                    return clampedPos;
                }
            }
        }
    }

    let startPos;
    if (sourceEvent) {
        // Convert click event to world coordinates
        const worldX = (sourceEvent.clientX - panX) / zoom;
        const worldY = ((sourceEvent.clientY - TASKBAR_HEIGHT) - panY) / zoom;
        startPos = { x: worldX - width / 2, y: worldY - height / 2 };
    } else {
        // Default to center of the current view
        const worldCenterX = view.x + view.width / 2;
        const worldCenterY = view.y + view.height / 2;
        startPos = { x: worldCenterX - width / 2, y: worldCenterY - height / 2 };
    }

    let candidatePos = clampToView(startPos);
    if (!checkCollision({ ...candidatePos, width, height })) {
        return candidatePos;
    }

    // Spiral search outwards from the start point
    let x = startPos.x + width / 2;
    let y = startPos.y + height / 2;
    let step = 30, leg = 0, armLength = 1, count = 0;
    for (let i = 0; i < 200; i++) {
        const testPos = { x: x - width / 2, y: y - height / 2 };
        if (!checkCollision({ ...testPos, width, height })) {
            return testPos;
        }
        switch (leg) {
            case 0: x += step; break;
            case 1: y += step; break;
            case 2: x -= step; break;
            case 3: y -= step; break;
        }
        if (++count >= armLength) {
            count = 0;
            leg = (leg + 1) % 4;
            if (leg % 2 === 0) armLength++;
        }
    }

    return { x: view.x + (currentWindowId % 10) * 20, y: view.y + (currentWindowId % 10) * 20 };
}

function createSerializableLayout(allWindows) {
    if (typeof window === 'undefined') return null;

    const windowGroups = allWindows.map(group => {
        const config = generateBoardConfigFromWindow(group, allWindows);
        return {
            ...config,
            zIndex: group.zIndex,
        };
    });

    return {
        desktop: {
            width: window.innerWidth,
            height: window.innerHeight - TASKBAR_HEIGHT,
        },
        windowGroups,
    };
}


function createWindowManager() {
    const rehydrateLayout = (layout) => {
        if (!layout || !layout.windowGroups) return [];
        
        windowGroupIdCounter = 0;
        tabIdCounter = 0;
        const idMap = new Map();

        let newGroups = [];
        const sortedGroupsData = [...layout.windowGroups].sort((a,b) => (a.zIndex || 0) - (b.zIndex || 0));

        for (const groupData of sortedGroupsData) {
            const newTabs = groupData.tabs.map(tabData => {
                const component = componentMap[tabData.componentType];
                if (!component) return null;
                const { componentType, originalId, ...props } = tabData;
                const allWindowSettings = get(windowSettings);
                const componentSettings = allWindowSettings[tabData.componentType];
                const defaultZoom = componentSettings?.defaultZoom ?? 1.0;
                const newTabId = ++tabIdCounter;
                idMap.set(originalId, newTabId);
                return { id: newTabId, component, componentName: tabData.componentType, ...props, zoom: props.zoom ?? defaultZoom, originalId };
            }).filter(Boolean);

            if (newTabs.length === 0) continue;

            newGroups.push({
                id: ++windowGroupIdCounter,
                x: groupData.x, y: groupData.y, width: groupData.width, height: groupData.height,
                minimized: false,
                maximized: groupData.maximized,
                isActive: false,
                zIndex: groupData.zIndex,
                prevX: groupData.x, prevY: groupData.y, prevWidth: groupData.width, prevHeight: groupData.height,
                notice: null,
                tabs: newTabs,
                activeTabId: groupData.activeTabId,
            });
        }

        let topZ = -1;
        let topWindowId = -1;
        for (const group of newGroups) {
            group.activeTabId = idMap.get(group.activeTabId) || (group.tabs.length > 0 ? group.tabs[0].id : null);
            for (const tab of group.tabs) {
                if (tab.consoleId) {
                    tab.consoleId = idMap.get(tab.consoleId) || tab.consoleId;
                }
                delete tab.originalId;
            }
            if (group.zIndex > topZ) {
                topZ = group.zIndex;
                topWindowId = group.id;
            }
        }
        if (topWindowId !== -1) {
            const topWindow = newGroups.find(g => g.id === topWindowId);
            if (topWindow) topWindow.isActive = true;
        }
        
        return newGroups;
    };

    let initialWindows = [];
    if (typeof window !== 'undefined') {
        try {
            const savedLayoutJson = localStorage.getItem('sidekickWindowLayout');
            if (savedLayoutJson) {
                const savedLayout = JSON.parse(savedLayoutJson);
                initialWindows = rehydrateLayout(savedLayout);
            }
        } catch (e) {
            console.error("Failed to load and restore window layout:", e);
            localStorage.removeItem('sidekickWindowLayout');
        }
    }
    
    const { subscribe, update } = writable(initialWindows);

    subscribe(allWindows => {
        if (typeof window !== 'undefined') {
            const layoutToSave = createSerializableLayout(allWindows);
            if (layoutToSave) {
                localStorage.setItem('sidekickWindowLayout', JSON.stringify(layoutToSave));
            }
        }
    });

    // Subscribe to window view changes to update maximized windows
    if (typeof window !== 'undefined') {
        windowView.subscribe(({ panX, panY, zoom }) => {
            update(windows => {
                const desktopWidth = window.innerWidth;
                const desktopHeight = window.innerHeight - TASKBAR_HEIGHT;
                let changed = false;

                const newWindows = windows.map(w => {
                    if (w.maximized) {
                        changed = true;
                        return {
                            ...w,
                            x: -panX / zoom,
                            y: -panY / zoom,
                            width: desktopWidth / zoom,
                            height: desktopHeight / zoom,
                        };
                    }
                    return w;
                });
                return changed ? newWindows : windows;
            });
        });
    }

    const addWindow = (component, props = {}) => {
        const groupProps = { x: props.x, y: props.y, width: props.width, height: props.height };
        const tabProps = { ...props };
        ['x', 'y', 'width', 'height'].forEach(p => delete tabProps[p]);

        const defaults = { title: 'New Window', width: 800, height: 600 };

        const allWindowSettings = get(windowSettings);
        const componentName = Object.keys(componentMap).find(key => componentMap[key] === component) || 'Unknown';
        const savedSettings = allWindowSettings[componentName];
        const useSavedPosition = savedSettings && savedSettings.positioning === 'manual';

        const newWindowWidth = useSavedPosition ? savedSettings.width : (groupProps.width ?? defaults.width);
        const newWindowHeight = useSavedPosition ? savedSettings.height : (groupProps.height ?? defaults.height);
        let newX, newY;

        if (useSavedPosition) {
            newX = savedSettings.x;
            newY = savedSettings.y;
        } else if (groupProps.x != null && groupProps.y != null) {
            newX = groupProps.x;
            newY = groupProps.y;
        } else {
            const placementProps = {
                width: newWindowWidth,
                height: newWindowHeight,
                sourceEvent: props.sourceEvent,
                sourceTabId: props.consoleId || props.sourceTabId,
            };
            const pos = findOptimalPosition(placementProps, get(windows), windowGroupIdCounter + 1);
            newX = pos.x;
            newY = pos.y;
        }

        const newTab = {
            id: ++tabIdCounter,
            component: component,
            componentName: componentName,
            ...tabProps,
            zoom: savedSettings?.defaultZoom ?? 1.0,
            lastFocusedElement: null,
        };

        const newWindowGroup = {
            id: ++windowGroupIdCounter,
            x: newX,
            y: newY,
            width: newWindowWidth,
            height: newWindowHeight,
            zIndex: 100,
            minimized: false,
            maximized: false,
            isActive: true,
            prevX: 0, prevY: 0, prevWidth: 0, prevHeight: 0,
            tabs: [newTab],
            activeTabId: newTab.id,
            notice: null,
        };

        update(windows => {
            const updatedWindows = windows.map(w => ({ ...w, zIndex: w.zIndex - 10, isActive: false }));
            newWindowGroup.zIndex = updatedWindows.reduce((max, w) => Math.max(max, w.zIndex), 99) + 1;
            return [...updatedWindows, newWindowGroup];
        });
        return { groupId: newWindowGroup.id, tabId: newTab.id };
    };

    const removeTab = (groupId, tabId) => {
        update(windows => {
            const groupIndex = windows.findIndex(g => g.id === groupId);
            if (groupIndex === -1) return windows;

            const group = windows[groupIndex];
            const tabIndex = group.tabs.findIndex(t => t.id === tabId);
            if (tabIndex === -1) return windows;

            // Handle IoskConsole confirmation
            const tabToRemove = group.tabs[tabIndex];
            if (tabToRemove.component === IoskConsole && tabToRemove.isConsoleConnected) {
                if (!confirm("This console has an active connection. Are you sure you want to close it?")) {
                    return windows;
                }
            }

            if (group.tabs.length === 1) {
                // Last tab, remove the whole group
                return windows.filter(g => g.id !== groupId);
            } else {
                // More tabs remain, just remove one
                const newTabs = group.tabs.filter(t => t.id !== tabId);
                let newActiveTabId = group.activeTabId;

                if (group.activeTabId === tabId) {
                    // If the active tab was closed, activate the previous one or the first one
                    newActiveTabId = (newTabs[tabIndex] || newTabs[tabIndex - 1] || newTabs[0]).id;
                }

                const newGroup = { ...group, tabs: newTabs, activeTabId: newActiveTabId };
                const newWindows = [...windows];
                newWindows[groupIndex] = newGroup;
                return newWindows;
            }
        });
    };

    const removeWindow = (groupId) => {
        update(currentWindows => {
            const group = currentWindows.find(g => g.id === groupId);
            if (!group) return currentWindows;

            // Check if any tab requires confirmation
            for (const tab of group.tabs) {
                 if (tab.component === IoskConsole && tab.isConsoleConnected) {
                    if (!confirm(`Console "${tab.title}" has an active connection. Are you sure you want to close it?`)) {
                        return currentWindows;
                    }
                    // Only need to confirm once for the whole group
                    break;
                }
            }
            return currentWindows.filter(g => g.id !== groupId);
        });
    };

    const setActiveTab = (groupId, tabId) => {
        update(windows => windows.map(g => g.id === groupId ? { ...g, activeTabId: tabId } : g));
        focusWindow(groupId);
    };

    const groupWindows = (sourceGroupId, targetGroupId) => {
        update(windows => {
            const sourceGroup = windows.find(g => g.id === sourceGroupId);
            const targetGroup = windows.find(g => g.id === targetGroupId);

            if (!sourceGroup || !targetGroup) return windows;

            const newTabs = [...targetGroup.tabs, ...sourceGroup.tabs];
            const newActiveTabId = sourceGroup.tabs[0].id;

            // Remove source, update target
            return windows
                .filter(g => g.id !== sourceGroupId)
                .map(g => g.id === targetGroupId ? { ...g, tabs: newTabs, activeTabId: newActiveTabId } : g);
        });
        focusWindow(targetGroupId);
    };

    const setActiveWindow = (id) => {
        update(windows => {
            const targetWindow = windows.find(w => w.id === id);
            if (targetWindow && targetWindow.isActive) return windows;

            return windows.map(w => ({ ...w, isActive: w.id === id }));
        });
    };

    const focusWindow = (id) => {
        update(windows => {
            const currentTopWindow = windows.reduce((top, w) => (!top || w.zIndex > top.zIndex) ? w : top, null);
            if (currentTopWindow && currentTopWindow.id === id && currentTopWindow.isActive) return windows;

            const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
            return windows.map(w => {
                if (w.id === id) return { ...w, zIndex: maxZ + 1, isActive: true };
                return { ...w, isActive: false };
            });
        });
    };

    const updateWindowProps = (id, newProps) => {
        update(windows => windows.map(w => w.id === id ? { ...w, ...newProps } : w));
    };

    const updateTabProps = (groupId, tabId, newProps) => {
        update(windows => windows.map(g => {
            if (g.id === groupId) {
                return {
                    ...g,
                    tabs: g.tabs.map(t => t.id === tabId ? { ...t, ...newProps } : t)
                };
            }
            return g;
        }));
    };

    const changeTabZoom = (groupId, tabId, delta) => {
        update(windows => {
            const group = windows.find(g => g.id === groupId);
            if (!group) return windows;
            const tab = group.tabs.find(t => t.id === tabId);
            if (!tab) return windows;

            const currentZoom = tab.zoom || 1.0;
            const newZoom = currentZoom + delta;
            const clampedZoom = Math.max(0.5, Math.min(3.0, newZoom));

            if (clampedZoom !== currentZoom) {
                const newTabs = group.tabs.map(t => t.id === tabId ? { ...t, zoom: clampedZoom } : t);
                return windows.map(g => g.id === groupId ? { ...g, tabs: newTabs } : g);
            }
            return windows;
        });
    };

    const resetTabZoom = (groupId, tabId) => {
        const group = get(windows).find(g => g.id === groupId);
        if (!group) return;
        const tab = group.tabs.find(t => t.id === tabId);
        if (!tab) return;

        const allWindowSettings = get(windowSettings);
        const componentSettings = allWindowSettings[tab.componentName];
        const defaultZoom = componentSettings?.defaultZoom ?? 1.0;

        updateTabProps(groupId, tabId, { zoom: defaultZoom });
    };

    const toggleMinimize = (id) => {
        update(windows => {
            const winToToggle = windows.find(w => w.id === id);
            if (!winToToggle) return windows;

            if (winToToggle.minimized) {
                const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
                return windows.map(w => {
                    if (w.id === id) return { ...w, minimized: false, zIndex: maxZ + 1, isActive: true };
                    return { ...w, isActive: false };
                });
            } else {
                const updated = windows.map(w => (w.id === id ? { ...w, minimized: true, isActive: false } : w));
                const nextWindow = updated.filter(w => !w.minimized).reduce((top, w) => (!top || w.zIndex > top.zIndex) ? w : top, null);
                if(nextWindow) focusWindow(nextWindow.id);
                return updated;
            }
        });
    };

    const toggleMaximize = (id) => {
        update(windows => {
            const { panX, panY, zoom } = get(windowView);
            const desktopWidth = window.innerWidth;
            const desktopHeight = window.innerHeight - TASKBAR_HEIGHT;

            const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
            return windows.map(w => {
                if (w.id === id) {
                    const newProps = w.maximized
                        ? { maximized: false, x: w.prevX, y: w.prevY, width: w.prevWidth, height: w.prevHeight }
                        : {
                            maximized: true,
                            prevX: w.x, prevY: w.y, prevWidth: w.width, prevHeight: w.height,
                            x: -panX / zoom,
                            y: -panY / zoom,
                            width: desktopWidth / zoom,
                            height: desktopHeight / zoom,
                          };
                    return { ...w, ...newProps, zIndex: maxZ + 1, isActive: true };
                }
                return { ...w, isActive: false };
            });
        });
    };

    const closeAllWindows = () => {
        let windowsToKeep = [];
        let windowsToCheck = get(windows);

        for (const group of windowsToCheck) {
            let tabsToKeep = [];
            for (const tab of group.tabs) {
                if (tab.component === IoskConsole && tab.isConsoleConnected) {
                    if (!confirm(`Console "${tab.title}" has an active connection. Close it anyway?`)) {
                        tabsToKeep.push(tab);
                    }
                }
            }
            if (tabsToKeep.length > 0) {
                windowsToKeep.push({ ...group, tabs: tabsToKeep });
            }
        }
        update(() => windowsToKeep);
    };

    const minimizeAllWindows = () => update(ws => ws.map(w => ({...w, minimized: true, isActive: false })));

    const restoreAllWindows = () => {
        update(currentWindows => {
            if (!currentWindows.some(w => w.minimized)) return currentWindows;
            let updatedWindows = currentWindows.map(w => ({...w, minimized: false}));
            if (!updatedWindows.some(w => w.isActive) && updatedWindows.length > 0) {
                const topWindow = updatedWindows.reduce((top, w) => (!top || w.zIndex > top.zIndex) ? w : top, null);
                if (topWindow) {
                    updatedWindows = updatedWindows.map(w => w.id === topWindow.id ? { ...w, isActive: true } : w);
                }
            }
            return updatedWindows;
        });
    };

    const cycleWindow = (forward) => {
        update(currentWindows => {
            const openWindows = currentWindows.filter(w => !w.minimized).sort((a, b) => b.zIndex - a.zIndex);
            if (openWindows.length < 2) return currentWindows;
            const openZIndices = openWindows.map(w => w.zIndex).sort((a,b) => a - b);
            let newOrder = [...openWindows];
            if (forward) newOrder.push(newOrder.shift());
            else newOrder.unshift(newOrder.pop());

            const newProps = {};
            const activeId = newOrder[0].id;
            newOrder.forEach((win, index) => {
                newProps[win.id] = { zIndex: openZIndices[openZIndices.length - 1 - index], isActive: win.id === activeId };
            });

            return currentWindows.map(w => newProps[w.id] ? { ...w, ...newProps[w.id] } : w);
        });
    };

    const reorderTab = (groupId, draggedTabId, targetTabId) => {
        update(windows => {
            const groupIndex = windows.findIndex(g => g.id === groupId);
            if (groupIndex === -1) return windows;

            const group = windows[groupIndex];
            const tabs = [...group.tabs];

            const draggedIndex = tabs.findIndex(t => t.id == draggedTabId);
            if (draggedIndex === -1) return windows;

            const [draggedTab] = tabs.splice(draggedIndex, 1);

            if (targetTabId === null) {
                tabs.push(draggedTab);
            } else {
                const targetIndex = tabs.findIndex(t => t.id == targetTabId);
                if (targetIndex !== -1) {
                    tabs.splice(targetIndex, 0, draggedTab);
                } else {
                    tabs.push(draggedTab);
                }
            }

            const newGroup = { ...group, tabs };
            const newWindows = [...windows];
            newWindows[groupIndex] = newGroup;
            return newWindows;
        });
    };

    const detachTabToNewWindow = (sourceGroupId, tabId, newX, newY) => {
        update(windows => {
            const sourceGroupIndex = windows.findIndex(g => g.id === sourceGroupId);
            if (sourceGroupIndex === -1) return windows;

            const sourceGroup = windows[sourceGroupIndex];
            const tabToDetach = sourceGroup.tabs.find(t => t.id === tabId);
            if (!tabToDetach || sourceGroup.tabs.length < 2) return windows;

            // 1. Modify source group
            const newSourceTabs = sourceGroup.tabs.filter(t => t.id !== tabId);
            let newWindows = [...windows];

            let newActiveTabId = sourceGroup.activeTabId;
            if (newActiveTabId === tabId) {
                newActiveTabId = newSourceTabs[0].id;
            }
            newWindows[sourceGroupIndex] = { ...sourceGroup, tabs: newSourceTabs, activeTabId: newActiveTabId };

            // 2. Create new group for detached tab
            const newWindowGroup = {
                id: ++windowGroupIdCounter,
                x: newX, y: newY,
                width: sourceGroup.width, height: sourceGroup.height,
                zIndex: 100, minimized: false, maximized: false, isActive: true,
                prevX: 0, prevY: 0, prevWidth: 0, prevHeight: 0,
                tabs: [tabToDetach],
                activeTabId: tabToDetach.id,
                notice: null,
            };

            // 3. Add new group and update z-indices/active state
            newWindows = newWindows.map(w => ({ ...w, isActive: w.id === newWindowGroup.id, zIndex: w.id === sourceGroupId ? w.zIndex : w.zIndex - 1 }));
            newWindowGroup.zIndex = newWindows.reduce((max, w) => Math.max(max, w.zIndex), 99) + 1;
            newWindows.push(newWindowGroup);

            return newWindows;
        });
    };

    const restoreWindow = (groupData) => {
        const tabs = groupData.tabs.map(tabData => {
            const component = componentMap[tabData.componentType];
            if (!component) return null;

            const { componentType, ...props } = tabData;

            const allWindowSettings = get(windowSettings);
            const componentSettings = allWindowSettings[tabData.componentType];
            const defaultZoom = componentSettings?.defaultZoom ?? 1.0;

            return {
                id: ++tabIdCounter,
                component,
                componentName: tabData.componentType,
                ...props,
                zoom: props.zoom ?? defaultZoom,
            };
        }).filter(Boolean);

        if (tabs.length === 0) return;

        const activeTabInNewGroup = tabs.find(t => t.originalId === groupData.activeTabId);
        const newActiveTabId = activeTabInNewGroup ? activeTabInNewGroup.id : (tabs[0] ? tabs[0].id : null);

        // Clean up originalId from tabs
        tabs.forEach(t => delete t.originalId);

        update(windows => {
            const updatedWindows = windows.map(w => ({ ...w, isActive: false }));
            const maxZ = updatedWindows.reduce((max, w) => Math.max(max, w.zIndex), 99);

            const newGroup = {
                id: ++windowGroupIdCounter,
                x: groupData.x, y: groupData.y, width: groupData.width, height: groupData.height,
                minimized: false,
                maximized: groupData.maximized,
                isActive: true,
                zIndex: maxZ + 1,
                prevX: groupData.x, prevY: groupData.y, prevWidth: groupData.width, prevHeight: groupData.height,
                notice: null,
                tabs: tabs,
                activeTabId: newActiveTabId,
            };
            return [...updatedWindows, newGroup];
        });
    };

    const restoreLayout = (layout) => {
        if (!layout || !layout.windowGroups) return;

        const idMap = new Map(); // Map<originalId, newId>

        // --- Scaling Logic ---
        const savedDesktopWidth = layout.desktop?.width || window.innerWidth;
        const savedDesktopHeight = layout.desktop?.height || (window.innerHeight - 40);
        const currentDesktopWidth = window.innerWidth;
        const currentDesktopHeight = window.innerHeight - 40;
        const scaleX = currentDesktopWidth / savedDesktopWidth;
        const scaleY = currentDesktopHeight / savedDesktopHeight;

        const newGroups = [];

        // --- 1st Pass: Create new objects, generate new IDs, and populate map ---
        for (const groupData of layout.windowGroups) {
            const scaledGroupData = { ...groupData };
            if (!scaledGroupData.maximized) {
                scaledGroupData.x = Math.round(scaledGroupData.x * scaleX);
                scaledGroupData.y = Math.round(scaledGroupData.y * scaleY);
                scaledGroupData.width = Math.round(scaledGroupData.width * scaleX);
                scaledGroupData.height = Math.round(scaledGroupData.height * scaleY);
            }

            const newTabs = scaledGroupData.tabs.map(tabData => {
                const component = componentMap[tabData.componentType];
                if (!component) return null;

                const { componentType, originalId, ...props } = tabData;
                const allWindowSettings = get(windowSettings);
                const componentSettings = allWindowSettings[tabData.componentType];
                const defaultZoom = componentSettings?.defaultZoom ?? 1.0;
                const newTabId = ++tabIdCounter;
                idMap.set(originalId, newTabId);

                return {
                    id: newTabId,
                    component,
                    componentName: tabData.componentType,
                    ...props,
                    zoom: props.zoom ?? defaultZoom,
                    originalId: originalId // Keep for 2nd pass
                };
            }).filter(Boolean);

            if (newTabs.length === 0) continue;

            const newGroup = {
                id: ++windowGroupIdCounter,
                x: scaledGroupData.x, y: scaledGroupData.y, width: scaledGroupData.width, height: scaledGroupData.height,
                minimized: false,
                maximized: scaledGroupData.maximized,
                isActive: false, // Set later
                zIndex: 0,       // Set later
                prevX: scaledGroupData.x, prevY: scaledGroupData.y, prevWidth: scaledGroupData.width, prevHeight: scaledGroupData.height,
                notice: null,
                tabs: newTabs,
                activeTabId: scaledGroupData.activeTabId, // Keep old ID for 2nd pass
            };
            newGroups.push(newGroup);
        }

        // --- 2nd Pass: Remap all ID-based references ---
        for (const group of newGroups) {
            group.activeTabId = idMap.get(group.activeTabId) || (group.tabs.length > 0 ? group.tabs[0].id : null);
            for (const tab of group.tabs) {
                if (tab.consoleId) {
                    tab.consoleId = idMap.get(tab.consoleId) || tab.consoleId;
                }
                delete tab.originalId;
            }
        }

        // --- Final Step: Update the Svelte store once with all new windows ---
        update(windows => {
            const updatedWindows = windows.map(w => ({ ...w, isActive: false }));
            let maxZ = updatedWindows.reduce((max, w) => Math.max(max, w.zIndex), 99);

            newGroups.forEach(g => {
                g.zIndex = ++maxZ;
            });

            if (newGroups.length > 0) {
                newGroups[newGroups.length - 1].isActive = true;
            }

            return [...updatedWindows, ...newGroups];
        });
    };

    const backWindow = (groupId) => {
        const allWindows = get(windows);
        const group = allWindows.find(g => g.id === groupId);
        if (!group) return;

        const config = generateBoardConfigFromWindow(group, allWindows);
        const configStr = JSON.stringify(config);

        createBackedWindow(configStr, group.x, group.y, group.width, group.height, 1.0);
        removeWindow(groupId);
    };

    const unbackWindow = (backedWindow) => {
        // Get current view states for coordinate transformation
        const dv = get(desktopView);
        const wv = get(windowView);

        // Get the visual dimensions of the backed window on the back layer, accounting for scale
        const scale = backedWindow.scale || 1.0;
        const backedVisualWidth = backedWindow.width * scale;
        const backedVisualHeight = backedWindow.height * scale;

        // Calculate the midpoint of the backed window in back-layer world coordinates
        const backWorldMidX = backedWindow.x + backedVisualWidth / 2;
        const backWorldMidY = backedWindow.y + backedVisualHeight / 2;
        
        // Transform this midpoint into front-layer world coordinates
        // This is the core transformation: from back-world -> screen -> front-world
        const frontWorldMidX = ((backWorldMidX * dv.zoom) + dv.panX - wv.panX) / wv.zoom;
        const frontWorldMidY = ((backWorldMidY * dv.zoom) + dv.panY - wv.panY) / wv.zoom;
        
        // Get the original, unscaled dimensions of the window to be restored from its config
        const restoredWindowWidth = backedWindow.config.width;
        const restoredWindowHeight = backedWindow.config.height;

        // Calculate the new top-left (x, y) for the restored window in front-layer world coordinates
        const newX = frontWorldMidX - restoredWindowWidth / 2;
        const newY = frontWorldMidY - restoredWindowHeight / 2;
        
        // Now, proceed with unbacking
        deleteBackedWindow(backedWindow.id);
        
        // Call restoreWindow, passing the original config but overriding x, y, width, height
        // with the newly calculated values that are correct for the front layer.
        restoreWindow({ 
            ...backedWindow.config, 
            x: newX, 
            y: newY, 
            width: restoredWindowWidth, 
            height: restoredWindowHeight 
        });
    };

    // --- Sentinel Implementation ---

    const resolveNoticeSettings = (componentName) => {
        const globalDefaults = get(desktopSettings).noticeDefaults;
        const allWindowOverrides = get(windowSettings);
        const override = allWindowOverrides[componentName]?.notice;

        if (!globalDefaults.enabled && override?.mode !== 'enabled') {
            return { enabled: false };
        }

        if (override?.mode === 'disabled') {
            return { enabled: false };
        }

        if (override?.mode === 'enabled') {
            // Merge global and override settings. Override takes precedence.
            return {
                enabled: true,
                visual: { ...globalDefaults.visual, ...override.visual },
                audio: { ...globalDefaults.audio, ...override.audio },
            };
        }

        // Default case: use global settings ('global' mode or no override)
        return globalDefaults;
    };

    const playNoticeSound = (audioSettings) => {
        if (!audioSettings.sound || audioSettings.sound === 'none') return;
        const src = audioSettings.sound === 'custom' ? audioSettings.url : `/assets/${audioSettings.sound}`;
        try {
            new Audio(src).play().catch(e => console.error("Notice audio play failed:", e));
        } catch (e) {
            console.error("Could not play notice audio.", e);
        }
    };

    const logToNotificationCenter = (group, tab, payload) => {
        const newNotification = {
            id: Date.now(),
            groupId: group.id,
            tabId: tab.id,
            timestamp: new Date(),
            icon: tab.componentName,
            summary: payload.summary || `Activity in ${tab.title}`,
            read: false,
        };
        notificationHistory.update(history => [newNotification, ...history].slice(0, 100)); // Keep last 100
        unreadNoticeCount.update(n => n + 1);
    };

    const notifyActivity = (groupId, tabId, payload = {}, force = false) => {
        update(windows => {
            const group = windows.find(g => g.id === groupId);
            if (!group || (group.isActive && !force)) {
                return windows; // Don't notify for active windows unless forced
            }

            const tab = group.tabs.find(t => t.id === tabId);
            if (!tab) return windows;

            const settings = resolveNoticeSettings(tab.componentName);
            if (!settings.enabled) return windows;

            const noticeId = Date.now();
            const updatedGroup = { ...group, notice: { id: noticeId, color: settings.visual.color } };

            if (settings.audio.enabled && settings.audio.sound && settings.audio.sound !== 'none') {
                playNoticeSound(settings.audio);
            }

            logToNotificationCenter(group, tab, payload);

            setTimeout(() => {
                update(currentWindows => currentWindows.map(w =>
                    (w.id === groupId && w.notice?.id === noticeId) ? { ...w, notice: null } : w
                ));
            }, settings.visual.duration);

            return windows.map(w => w.id === groupId ? updatedGroup : w);
        });
    };

    return {
        subscribe,
        addWindow,
        removeWindow,
        removeTab,
        focusWindow,
        setActiveWindow,
        setActiveTab,
        updateWindowProps,
        updateTabProps,
        changeTabZoom,
        resetTabZoom,
        toggleMinimize,
        toggleMaximize,
        closeAllWindows,
        minimizeAllWindows,
        restoreAllWindows,
        cycleWindow,
        groupWindows,
        reorderTab,
        detachTabToNewWindow,
        restoreWindow,
        restoreLayout,
        notifyActivity,
        backWindow,
        unbackWindow,
    };
}

export const windows = createWindowManager();

export const activeConsoles = readable(new Map(), set => {
    const unsubscribe = windows.subscribe(allWindows => {
        const newActiveConsoles = new Map();
        for (const group of allWindows) {
            for (const tab of group.tabs) {
                if (tab.componentName === 'IoskConsole' && tab.isConsoleConnected && tab.consoleConnection) {
                    const key = `${tab.consoleConnection.user}@${tab.consoleConnection.url}`;
                    if (!newActiveConsoles.has(key)) {
                        newActiveConsoles.set(key, tab);
                    }
                }
            }
        }
        set(newActiveConsoles);
    });

    return () => unsubscribe();
});

export const instanceRegistry = {
    instances: new Map(),
    register(tabId, instance) {
        this.instances.set(tabId, instance);
    },
    unregister(tabId) {
        this.instances.delete(tabId);
    },
    get(tabId) {
        return this.instances.get(tabId);
    }
};


// --- Window Creation Functions ---

export function newIoskConnection(props = {}) {
    const allWindowSettings = get(windowSettings);
    const componentSettings = allWindowSettings['IoskConsole'];
    const globalSettings = get(desktopSettings);

    windows.addWindow(IoskConsole, {
        title: 'IOSK Connection',
        wsUrl: componentSettings?.defaultUrl ?? globalSettings.ioskUrl,
        username: componentSettings?.defaultUsername ?? globalSettings.ioskUsername,
        ...props,
    });
}
export function newCalculator(props = {}) {
    windows.addWindow(Calculator, { title: 'Calculator', width: 320, height: 450, ...props });
}
export function newSettings(props = {}) {
    windows.addWindow(Settings, { title: 'Settings', width: 420, height: 711, ...props });
}
export function newNotificationCenter(props = {}) {
    const allWindows = get(windows);
    const existingNCTab = allWindows.flatMap(g => g.tabs).find(t =>
        t.componentName === 'NotificationCenter'
    );

    if (existingNCTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingNCTab.id));
        if (group.minimized) windows.toggleMinimize(group.id);
        else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingNCTab.id);
        return;
    }

    windows.addWindow(NotificationCenter, { title: 'Notifications', width: 475, height: 475, ...props });
}
export function newIoskFileExplorer(consoleTabId, consoleTitle, props = {}) {
    const title = `Files - ${consoleTitle || `Console ${consoleTabId}`}`;
    const explorerSettings = get(windowSettings)['IoskFileExplorer'];
    windows.addWindow(IoskFileExplorer, { title, consoleId: consoleTabId, initialPath: explorerSettings?.initialPath || '.', width: 500, height: 500, ...props });
}
export function newIoskFileViewer(consoleTabId, path, props = {}) {
    const title = path.split('/').pop() || path;
    windows.addWindow(IoskFileViewer, { title: `View - ${title}`, consoleId: consoleTabId, path: path, width: 700, height: 500, ...props });
}
export function newWebBrowser(props = {}) {
    const browserSettings = get(windowSettings)['WebBrowser'];
    const initialUrl = browserSettings?.defaultUrl || (typeof window !== 'undefined' ? window.location.origin : 'about:blank');
    windows.addWindow(WebBrowser, { title: 'Web Browser', initialUrl, width: 1024, height: 768, ...props });
}
export function newIoskPrivateChat(consoleTabId, localUser, remoteUser, props = {}) {
    const allWindows = get(windows);
    const existingChatTab = allWindows.flatMap(g => g.tabs).find(t =>
        t.componentName === 'IoskPrivateChat' && t.consoleId === consoleTabId && t.remoteUser === remoteUser
    );

    if (existingChatTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingChatTab.id));
        if (group.minimized) windows.toggleMinimize(group.id);
        else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingChatTab.id);
        return;
    }

    const title = remoteUser.split('.')[0];
    windows.addWindow(IoskPrivateChat, { title: `Chat with ${title}`, consoleId: consoleTabId, localUser, remoteUser, width: 450, height: 400, ...props });
}

export function newLocalTerminal(props = {}) {
    windows.addWindow(LocalTerminal, { title: 'Local Terminal', width: 800, height: 500, ...props });
}

export function newLocalFileExplorer(props = {}) {
    const defaultProps = { title: 'Local Files', width: 500, height: 600 };
    windows.addWindow(LocalFileExplorer, { ...defaultProps, ...props });
}

export function newLocalFileViewer(props = {}) {
    const title = (props.path || '').split('/').pop() || props.path;
    windows.addWindow(LocalFileViewer, { title: `View - ${title}`, width: 700, height: 500, ...props });
}

export function newAskWindow(initialFiles = [], props = {}) {
    windows.addWindow(Ask, { title: 'Ask', initialFiles, width: 900, height: 600, ...props });
}

export function newIoskWatch(consoleTabId, pwd, props = {}) {
    const allWindows = get(windows);
    const consoleTab = allWindows.flatMap(g => g.tabs).find(t => t.id === consoleTabId);
    if (!consoleTab || !consoleTab.isConsoleConnected) {
        alert("Cannot open Watch window. The selected console is not connected.");
        return;
    }

    windows.addWindow(IoskWatch, {
        title: 'Watch',
        consoleId: consoleTabId,
        consoleConnection: consoleTab.consoleConnection, // Pass this for Dash restore
        initialPwd: pwd,
        width: 700,
        height: 400,
        ...props,
    });
}


export function newIoskUserInspector(consoleTabId, targetUser, consoleWs, props = {}) {
    const allWindows = get(windows);

    // Find if an inspector for this user from this console already exists
    const existingInspectorTab = allWindows.flatMap(g => g.tabs).find(t =>
        t.componentName === 'IoskUserInspector' && !t.isDetached && t.consoleId === consoleTabId && t.targetUser === targetUser
    );

    if (existingInspectorTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingInspectorTab.id));
        if (group.minimized) windows.toggleMinimize(group.id);
        else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingInspectorTab.id);
        return;
    }

    // If not, create a new one, but first check if console is connected
    const consoleTab = allWindows.flatMap(g => g.tabs).find(t => t.id === consoleTabId);
    if (!consoleTab || !consoleTab.isConsoleConnected) {
        alert("Cannot inspect context. The selected console is not connected.");
        return;
    }

    const title = `Inspector - ${targetUser}`;
    windows.addWindow(IoskUserInspector, {
        title,
        consoleId: consoleTabId,
        targetUser: targetUser,
        consoleWs: consoleWs, // Pass the WebSocket instance
        consoleConnection: consoleTab.consoleConnection, // For dash restore
        width: 700,
        height: 700,
        ...props,
    });
}

export function newBox(props = {}) {
    const { name, context, sourceEvent } = props;

    // --- Calculate Aspect Ratio ---
    const desktopHeight = window.innerHeight - TASKBAR_HEIGHT;
    const desktopWidth = window.innerWidth;
    const aspectRatio = (desktopHeight > 0 && desktopWidth > 0) ? desktopHeight / desktopWidth : 1.0;

    // --- Find Optimal Position on Back Layer ---
    const BOX_BASE_WIDTH = 180;
    const BOX_BASE_HEIGHT = BOX_BASE_WIDTH * aspectRatio;

    // Reconstruct obstacles from stores, similar to `allItems` in Desktop.svelte
    const obstacles = [
        ...get(boxes).map(b => {
            const scale = b.scale ?? 1.0;
            const ar = b.aspect_ratio ?? aspectRatio;
            return { x: b.x, y: b.y, width: BOX_BASE_WIDTH * scale, height: BOX_BASE_WIDTH * ar * scale };
        }),
        ...get(desktopShortcuts).map(s => {
            const scale = s.scale || 1.0;
            const unscaledWidth = s.renderWidth || 90;
            const unscaledHeight = s.renderHeight || 90;
            return { x: s.x, y: s.y, width: unscaledWidth * scale, height: unscaledHeight * scale };
        }),
        ...get(backedWindows).map(bw => {
            const scale = bw.scale || 1.0;
            return { x: bw.x, y: bw.y, width: bw.width * scale, height: bw.height * scale };
        })
    ];

    const { panX, panY, zoom } = get(desktopView);

    const checkCollision = (rect) => {
        for (const obs of obstacles) {
            if (rect.x < obs.x + obs.width && rect.x + rect.width > obs.x &&
                rect.y < obs.y + obs.height && rect.y + rect.height > obs.y) {
                return true;
            }
        }
        return false;
    };

    let startPos;
    if (sourceEvent) {
        const worldX = (sourceEvent.clientX - panX) / zoom;
        const worldY = ((sourceEvent.clientY - TASKBAR_HEIGHT) - panY) / zoom;
        startPos = { x: worldX - BOX_BASE_WIDTH / 2, y: worldY - BOX_BASE_HEIGHT / 2 };
    } else {
        startPos = { x: 100, y: 100 }; // Fallback
    }

    let candidatePos = startPos;
    if (checkCollision({ ...candidatePos, width: BOX_BASE_WIDTH, height: BOX_BASE_HEIGHT })) {
        let x = startPos.x + BOX_BASE_WIDTH / 2;
        let y = startPos.y + BOX_BASE_HEIGHT / 2;
        let step = 30, leg = 0, armLength = 1, count = 0;
        let found = false;
        for (let i = 0; i < 200; i++) {
            const testPos = { x: x - BOX_BASE_WIDTH / 2, y: y - BOX_BASE_HEIGHT / 2 };
            if (!checkCollision({ ...testPos, width: BOX_BASE_WIDTH, height: BOX_BASE_HEIGHT })) {
                candidatePos = testPos;
                found = true;
                break;
            }
            switch (leg) {
                case 0: x += step; break;
                case 1: y += step; break;
                case 2: x -= step; break;
                case 3: y -= step; break;
            }
            if (++count >= armLength) {
                count = 0;
                leg = (leg + 1) % 4;
                if (leg % 2 === 0) armLength++;
            }
        }
        if (!found) candidatePos = startPos; // Fallback if no spot is found
    }
    
    createBox(name, 'local', context, aspectRatio, candidatePos.x, candidatePos.y);
}