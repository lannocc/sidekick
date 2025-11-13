import { writable, get } from 'svelte/store';
import IoskConsole from './IoskConsole.svelte';
import Calculator from './Calculator.svelte';
import Settings from './Settings.svelte';
import IoskFileExplorer from './IoskFileExplorer.svelte';
import IoskFileViewer from './IoskFileViewer.svelte';
import WebBrowser from './WebBrowser.svelte';
import IoskPrivateChat from './IoskPrivateChat.svelte';
import { desktopSettings, windowSettings } from './desktopStore.js';

let windowGroupIdCounter = 0;
let tabIdCounter = 0;

// Store for managing drag-and-drop grouping state
export const dragState = writable(null);

// Map component type strings to actual components for restoring layouts
const componentMap = {
    'IoskConsole': IoskConsole,
    'Calculator': Calculator,
    'Settings': Settings,
    'IoskFileExplorer': IoskFileExplorer,
    'IoskFileViewer': IoskFileViewer,
    'WebBrowser': WebBrowser,
    'IoskPrivateChat': IoskPrivateChat
};

function createWindowManager() {
    const { subscribe, update } = writable([]);

    const addWindow = (component, props = {}) => {
        const groupProps = { x: props.x, y: props.y, width: props.width, height: props.height };
        const tabProps = { ...props };
        ['x', 'y', 'width', 'height'].forEach(p => delete tabProps[p]);

        const defaults = { title: 'New Window', width: 800, height: 600 };

        const allWindowSettings = get(windowSettings);
        const componentName = Object.keys(componentMap).find(key => componentMap[key] === component) || 'Unknown';
        const savedSettings = allWindowSettings[componentName];
        const useSavedPosition = savedSettings && savedSettings.positioning === 'manual';

        const newTab = {
            id: ++tabIdCounter,
            component: component,
            componentName: componentName,
            ...tabProps,
            lastFocusedElement: null,
        };

        const newWindowGroup = {
            id: ++windowGroupIdCounter,
            x: useSavedPosition ? savedSettings.x : (groupProps.x ?? 50 + (windowGroupIdCounter % 10) * 20),
            y: useSavedPosition ? savedSettings.y : (groupProps.y ?? 50 + (windowGroupIdCounter % 10) * 20),
            width: useSavedPosition ? savedSettings.width : (groupProps.width ?? defaults.width),
            height: useSavedPosition ? savedSettings.height : (groupProps.height ?? defaults.height),
            zIndex: 100,
            minimized: false,
            maximized: false,
            isActive: true,
            prevX: 0, prevY: 0, prevWidth: 0, prevHeight: 0,
            tabs: [newTab],
            activeTabId: newTab.id,
            isFlashing: false,
        };

        update(windows => {
            const updatedWindows = windows.map(w => ({ ...w, zIndex: w.zIndex - 10, isActive: false }));
            newWindowGroup.zIndex = updatedWindows.reduce((max, w) => Math.max(max, w.zIndex), 99) + 1;
            return [...updatedWindows, newWindowGroup];
        });
        return newWindowGroup.id;
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
        const group = get(windows).find(g => g.id === groupId);
        if (group) {
            removeTab(groupId, group.activeTabId);
        }
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
            const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
            return windows.map(w => {
                if (w.id === id) {
                    const newProps = w.maximized
                        ? { maximized: false, x: w.prevX, y: w.prevY, width: w.prevWidth, height: w.prevHeight }
                        : { maximized: true, prevX: w.x, prevY: w.y, prevWidth: w.width, prevHeight: w.height, x: 0, y: 0 };
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
        toggleMinimize,
        toggleMaximize,
        closeAllWindows,
        minimizeAllWindows,
        restoreAllWindows,
        cycleWindow,
        groupWindows
    };
}

export const windows = createWindowManager();


// --- Window Creation Functions ---

export function newIoskConnection() {
    windows.addWindow(IoskConsole, { title: 'IOSK Connection' });
}
export function newCalculator() {
    windows.addWindow(Calculator, { title: 'Calculator', width: 320, height: 450 });
}
export function newSettings() {
    windows.addWindow(Settings, { title: 'Settings', width: 400, height: 550 });
}
export function newIoskFileExplorer(consoleTabId, consoleTitle) {
    const title = `Files - ${consoleTitle || `Console ${consoleTabId}`}`;
    const explorerSettings = get(windowSettings)['IoskFileExplorer'];
    windows.addWindow(IoskFileExplorer, { title, consoleId: consoleTabId, initialPath: explorerSettings?.initialPath || '.', width: 400, height: 500 });
}
export function newIoskFileViewer(consoleTabId, path) {
    const title = path.split('/').pop() || path;
    windows.addWindow(IoskFileViewer, { title: `View - ${title}`, consoleId: consoleTabId, path: path, width: 700, height: 500 });
}
export function newWebBrowser() {
    const browserSettings = get(windowSettings)['WebBrowser'];
    const initialUrl = browserSettings?.defaultUrl || (typeof window !== 'undefined' ? window.location.origin : 'about:blank');
    windows.addWindow(WebBrowser, { title: 'Web Browser', initialUrl, width: 1024, height: 768 });
}
export function newIoskPrivateChat(consoleTabId, localUser, remoteUser) {
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
    windows.addWindow(IoskPrivateChat, { title: `Chat with ${title}`, consoleId: consoleTabId, localUser, remoteUser, width: 450, height: 400 });
}

export function restoreWindow(groupData) {
    const allWindows = get(windows);
    
    const tabs = groupData.tabs.map(tabData => {
        const component = componentMap[tabData.componentType];
        if (!component) return null;
        
        const { componentType, ...props } = tabData;

        if ((component === IoskFileExplorer || component === IoskFileViewer || component === IoskPrivateChat) && props.consoleConnection) {
            const compatibleConsoleTab = allWindows.flatMap(g => g.tabs).find(t => 
                t.component === IoskConsole && t.isConsoleConnected && t.consoleConnection &&
                t.consoleConnection.url === props.consoleConnection.url &&
                t.consoleConnection.user === props.consoleConnection.user
            );
            props.consoleId = compatibleConsoleTab ? compatibleConsoleTab.id : null;
        }
        
        return {
            id: ++tabIdCounter,
            component,
            ...props,
        };
    }).filter(Boolean);

    if (tabs.length === 0) return;

    const newGroup = {
        id: ++windowGroupIdCounter,
        x: groupData.x, y: groupData.y, width: groupData.width, height: groupData.height,
        minimized: false,
        maximized: groupData.maximized,
        isActive: false,
        zIndex: 100,
        prevX: groupData.x, prevY: groupData.y, prevWidth: groupData.width, prevHeight: groupData.height,
        isFlashing: false,
        tabs: tabs,
        activeTabId: groupData.activeTabId ? tabs.find(t => t.originalId === groupData.activeTabId)?.id || tabs[0].id : tabs[0].id
    };

    update(ws => [...ws, newGroup]);
}