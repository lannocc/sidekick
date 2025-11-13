import { writable, get } from 'svelte/store';
import IoskConsole from './IoskConsole.svelte';
import Calculator from './Calculator.svelte';
import Settings from './Settings.svelte';
import IoskFileExplorer from './IoskFileExplorer.svelte';
import IoskFileViewer from './IoskFileViewer.svelte';
import WebBrowser from './WebBrowser.svelte';
import IoskPrivateChat from './IoskPrivateChat.svelte';
import { desktopSettings, windowSettings } from './desktopStore.js';

let groupIdCounter = 0;
let tabIdCounter = 0;

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
        const defaults = { title: 'New Window', width: 800, height: 600 };
        const allWindowSettings = get(windowSettings);
        const componentName = Object.keys(componentMap).find(key => componentMap[key] === component) || 'Unknown';
        const savedSettings = allWindowSettings[componentName];
        const useSavedPosition = savedSettings && savedSettings.positioning === 'manual';

        const newTab = {
            id: ++tabIdCounter,
            component,
            componentName,
            isFlashing: false,
            lastFocusedElement: null,
            ...props,
        };
        
        const newGroup = {
            id: ++groupIdCounter,
            x: useSavedPosition ? savedSettings.x : 50 + (groupIdCounter % 10) * 20,
            y: useSavedPosition ? savedSettings.y : 50 + (groupIdCounter % 10) * 20,
            width: useSavedPosition ? savedSettings.width : (props.width ?? defaults.width),
            height: useSavedPosition ? savedSettings.height : (props.height ?? defaults.height),
            zIndex: 100,
            minimized: false,
            maximized: false,
            isActive: true,
            activeTabId: newTab.id,
            tabs: [newTab],
            prevX: 0, prevY: 0, prevWidth: 0, prevHeight: 0,
        };

        update(groups => {
            const updatedGroups = groups.map(g => ({ ...g, zIndex: g.zIndex - 10, isActive: false }));
            newGroup.zIndex = updatedGroups.reduce((max, w) => Math.max(max, w.zIndex), 99) + 1;
            return [...updatedGroups, newGroup];
        });
        return { tabId: newTab.id, groupId: newGroup.id };
    };
    
    const findTabAndGroup = (tabId, groups) => {
        for (const group of groups) {
            const tab = group.tabs.find(t => t.id === tabId);
            if (tab) return { tab, group };
        }
        return { tab: null, group: null };
    };

    const removeTab = (tabId) => {
        update(groups => {
            const { tab: tabToRemove, group: groupToModify } = findTabAndGroup(tabId, groups);
            if (!tabToRemove || !groupToModify) return groups;

            if (tabToRemove.component === IoskConsole && get(windows).find(g => g.id === groupToModify.id)?.tabs.find(t => t.id === tabId)?.isConsoleConnected) {
                if (!confirm("This console has an active connection. Are you sure you want to close it?")) {
                    return groups;
                }
            }

            const tabIndex = groupToModify.tabs.findIndex(t => t.id === tabId);
            groupToModify.tabs.splice(tabIndex, 1);

            if (groupToModify.tabs.length === 0) {
                return groups.filter(g => g.id !== groupToModify.id);
            }

            if (groupToModify.activeTabId === tabId) {
                groupToModify.activeTabId = groupToModify.tabs[Math.max(0, tabIndex - 1)].id;
            }
            return [...groups];
        });
    };

    const focusGroup = (groupId) => {
        update(groups => {
            const currentTopGroup = groups.reduce((top, g) => (!top || g.zIndex > top.zIndex) ? g : top, null);
            if (currentTopGroup && currentTopGroup.id === groupId && currentTopGroup.isActive) return groups;
            const maxZ = groups.reduce((max, g) => Math.max(max, g.zIndex), 99);
            return groups.map(g => ({ ...g, isActive: g.id === groupId, zIndex: g.id === groupId ? maxZ + 1 : g.zIndex }));
        });
    };

    const setActiveTab = (groupId, tabId) => {
        update(groups => groups.map(g => g.id === groupId ? { ...g, activeTabId: tabId } : g));
        focusGroup(groupId);
    };

    const updateTabProps = (tabId, newProps) => {
        update(groups => {
            for (const group of groups) {
                const tab = group.tabs.find(t => t.id === tabId);
                if (tab) {
                    Object.assign(tab, newProps);
                    break;
                }
            }
            return [...groups];
        });
    };
    
    const updateGroupProps = (groupId, newProps) => {
        update(groups => groups.map(g => g.id === groupId ? { ...g, ...newProps } : g));
    };

    const mergeTabs = (sourceTabId, targetGroupId) => {
        update(groups => {
            const { tab: sourceTab, group: sourceGroup } = findTabAndGroup(sourceTabId, groups);
            const targetGroup = groups.find(g => g.id === targetGroupId);
            if (!sourceTab || !sourceGroup || !targetGroup || sourceGroup.id === targetGroup.id) return groups;
            
            targetGroup.tabs.push(sourceTab);
            sourceGroup.tabs = sourceGroup.tabs.filter(t => t.id !== sourceTabId);

            if (sourceGroup.tabs.length === 0) {
                groups = groups.filter(g => g.id !== sourceGroup.id);
            }
            
            setActiveTab(targetGroupId, sourceTab.id);
            return groups;
        });
    };
    
    const toggleMinimize = (groupId) => {
        update(groups => {
            const groupToToggle = groups.find(g => g.id === groupId);
            if (!groupToToggle) return groups;
            if (groupToToggle.minimized) {
                focusGroup(groupId);
                return groups.map(g => g.id === groupId ? { ...g, minimized: false } : g);
            } else {
                const updated = groups.map(g => (g.id === groupId ? { ...g, minimized: true, isActive: false } : g));
                const nextGroup = updated.filter(g => !g.minimized).reduce((top, g) => (!top || g.zIndex > top.zIndex) ? g : top, null);
                if(nextGroup) focusGroup(nextGroup.id);
                return updated;
            }
        });
    };
    
    const toggleMaximize = (groupId) => {
        update(groups => groups.map(g => {
            if (g.id === groupId) {
                const newProps = g.maximized
                    ? { maximized: false, x: g.prevX, y: g.prevY, width: g.prevWidth, height: g.prevHeight }
                    : { maximized: true, prevX: g.x, prevY: g.y, prevWidth: g.width, prevHeight: g.height, x: 0, y: 0 };
                return { ...g, ...newProps };
            }
            return g;
        }));
        focusGroup(groupId);
    };

    const closeAllWindows = () => {
        update(groups => {
            const groupsToKeep = [];
            for (const group of groups) {
                const tabsToKeep = [];
                for (const tab of group.tabs) {
                    if (tab.component === IoskConsole && tab.isConsoleConnected) {
                        if (!confirm(`Console "${tab.title}" has an active connection. Close it anyway?`)) {
                           tabsToKeep.push(tab);
                        }
                    }
                }
                if (tabsToKeep.length > 0) {
                    groupsToKeep.push({ ...group, tabs: tabsToKeep });
                }
            }
            return groupsToKeep;
        });
    };

    const minimizeAllWindows = () => update(groups => groups.map(g => ({...g, minimized: true, isActive: false })));
    const restoreAllWindows = () => {
        update(groups => {
            if (!groups.some(g => g.minimized)) return groups;
            let updatedGroups = groups.map(g => ({...g, minimized: false}));
            if (!updatedGroups.some(g => g.isActive) && updatedGroups.length > 0) {
                const topGroup = updatedGroups.reduce((top, g) => (!top || g.zIndex > top.zIndex) ? g : top, null);
                if (topGroup) focusGroup(topGroup.id);
            }
            return updatedGroups;
        });
    };
    
    const cycleGroup = (forward) => {
        update(groups => {
            const openGroups = groups.filter(g => !g.minimized).sort((a, b) => b.zIndex - a.zIndex);
            if (openGroups.length < 2) return groups;
            const openZIndices = openGroups.map(g => g.zIndex).sort((a, b) => a - b);
            const newOrder = forward ? [...openGroups.slice(1), openGroups[0]] : [openGroups[openGroups.length - 1], ...openGroups.slice(0, -1)];
            const activeId = newOrder[0].id;
            const newProps = {};
            newOrder.forEach((group, index) => {
                newProps[group.id] = { zIndex: openZIndices[openZIndices.length - 1 - index], isActive: group.id === activeId };
            });
            return groups.map(g => newProps[g.id] ? { ...g, ...newProps[g.id] } : g);
        });
    };

    return {
        subscribe, addWindow, removeTab, focusGroup, setActiveTab, updateTabProps, updateGroupProps,
        toggleMinimize, toggleMaximize, closeAllWindows, minimizeAllWindows, restoreAllWindows,
        cycleGroup, mergeTabs
    };
}
export const windows = createWindowManager();

// --- Window Creation Functions ---

export function newIoskConnection() { windows.addWindow(IoskConsole, { title: 'IOSK Connection' }); }
export function newCalculator() { windows.addWindow(Calculator, { title: 'Calculator', width: 320, height: 450 }); }
export function newSettings() { windows.addWindow(Settings, { title: 'Settings', width: 400, height: 550 }); }

export function newIoskFileExplorer(consoleId, consoleTitle) {
    const title = `Files - ${consoleTitle || `Console ${consoleId}`}`;
    const explorerSettings = get(windowSettings)['IoskFileExplorer'];
    windows.addWindow(IoskFileExplorer, { title, consoleId, initialPath: explorerSettings?.initialPath || '.', width: 400, height: 500 });
}

export function newIoskFileViewer(consoleId, path) {
    const title = path.split('/').pop() || path;
    windows.addWindow(IoskFileViewer, { title: `View - ${title}`, consoleId, path, width: 700, height: 500 });
}

export function newWebBrowser() {
    const browserSettings = get(windowSettings)['WebBrowser'];
    const initialUrl = browserSettings?.defaultUrl || (typeof window !== 'undefined' ? window.location.origin : 'about:blank');
    windows.addWindow(WebBrowser, { title: 'Web Browser', initialUrl, width: 1024, height: 768 });
}

export function newIoskPrivateChat(consoleId, localUser, remoteUser) {
    const allGroups = get(windows);
    const existingChatTab = allGroups.flatMap(g => g.tabs).find(t =>
        t.componentName === 'IoskPrivateChat' && t.consoleId === consoleId && t.remoteUser === remoteUser
    );

    if (existingChatTab) {
        const group = allGroups.find(g => g.tabs.some(t => t.id === existingChatTab.id));
        if (group.minimized) toggleMinimize(group.id);
        else setActiveTab(group.id, existingChatTab.id);
        return;
    }

    const title = remoteUser.includes('.') ? remoteUser.split('.')[0] : remoteUser;
    windows.addWindow(IoskPrivateChat, { title: `Chat with ${title}`, consoleId, localUser, remoteUser, width: 450, height: 400 });
}

export function restoreWindow(groupData) {
    let groupId;
    let firstTab = true;

    for (const tabData of groupData.tabs) {
        const component = componentMap[tabData.componentType];
        if (!component) {
            console.error(`Unknown component type for restore: ${tabData.componentType}`);
            continue;
        }
        
        const { componentType, ...props } = tabData;

        if (firstTab) {
            const result = windows.addWindow(component, props);
            groupId = result.groupId;
            windows.updateGroupProps(groupId, { ...groupData, tabs: undefined });
            firstTab = false;
        } else {
             update(groups => {
                const group = groups.find(g => g.id === groupId);
                if (group) {
                    const newTab = { id: ++tabIdCounter, component, componentName: tabData.componentType, ...props };
                    group.tabs.push(newTab);
                }
                return groups;
            });
        }
    }
    if (groupId) {
        windows.updateGroupProps(groupId, { activeTabId: groupData.activeTabId });
    }
}