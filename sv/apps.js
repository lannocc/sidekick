import { get, readable } from 'svelte/store';
import IoskConsole from './board/IoskConsole.svelte';
import Calculator from './board/Calculator.svelte';
import Settings from './board/Settings.svelte';
import FileExplorer from './board/FileExplorer.svelte';
import FileViewer from './board/FileViewer.svelte';
import WebBrowser from './board/WebBrowser.svelte';
import Camera from './board/Camera.svelte';
import IoskPrivateChat from './board/IoskPrivateChat.svelte';
import LocalTerminal from './board/LocalTerminal.svelte';
import Ask from './board/Ask.svelte';
import IoskWatch from './board/IoskWatch.svelte';
import IoskUserInspector from './board/IoskUserInspector.svelte';
import NotificationCenter from './board/NotificationCenter.svelte';
import Boxes from './board/Boxes.svelte';
import Processes from './board/Processes.svelte';
import { TASKBAR_HEIGHT, desktopSettings, windowSettings, desktopView } from './desktop.js';
import { createBox, boxes, desktopShortcuts, backedWindows, requestedBoxId, requestedPid, allIoskConfigs, runningProcesses } from './bridge.js';
import { windows } from './windows.js';
// --- MODIFICATION START: Import the central connections store ---
import { activeIoskConnections } from './iosk.js';
// --- MODIFICATION END ---


// --- App Definitions ---
// This centralizes app metadata for use in menus.
export const appList = [
    {
        id: 'settings',
        name: 'Settings',
        icon: '⚙️',
        launcher: newSettings,
        requiresConnection: false,
        menuPosition: { row: 0, col: 0 },
    },
    {
        id: 'calculator',
        name: 'Calculator',
        icon: '🧮',
        launcher: newCalculator,
        requiresConnection: false,
        menuPosition: { row: 0, col: 1 },
    },
    {
        id: 'camera',
        name: 'Camera',
        icon: '📸',
        launcher: newCamera,
        requiresConnection: false,
        menuPosition: { row: 0, col: 2 },
    },
    {
        id: 'web_browser',
        name: 'Web Browser',
        icon: '🌐',
        launcher: newWebBrowser,
        requiresConnection: false,
        menuPosition: { row: 0, col: 3 },
    },
    {
        id: 'iosk_connection',
        name: 'IOSK Console',
        icon: '🖥️',
        launcher: newIoskConsole,
        requiresConnection: false,
        menuPosition: { row: 0, col: 4 },
        badge: '/iosk.png',
    },
    {
        id: 'ask',
        name: 'Ask',
        icon: '?',
        launcher: newAskWindow,
        requiresConnection: true,
        menuPosition: { row: 1, col: 0 },
    },
    {
        id: 'processes',
        name: 'Processes',
        icon: '🛠️',
        launcher: newProcessesWindow,
        requiresConnection: true,
        menuPosition: { row: 1, col: 1 },
    },
    {
        id: 'boxes',
        name: 'Boxes',
        icon: '📦',
        launcher: newBoxesWindow,
        requiresConnection: true,
        menuPosition: { row: 1, col: 2 },
    },
    {
        id: 'files',
        name: 'Files',
        icon: '📁',
        launcher: newLocalFileExplorer,
        requiresConnection: true,
        menuPosition: { row: 1, col: 3 },
        getProps: (stores) => {
            const box = get(stores.currentBox);
            if (box && box.id !== 0) {
                return {
                    initialPath: box.context,
                    title: `Files - ${box.name}`,
                };
            }
            return {};
        }
    },
    {
        id: 'terminal',
        name: 'Terminal',
        icon: '>_',
        launcher: newLocalTerminal,
        requiresConnection: true,
        menuPosition: { row: 1, col: 4 },
        getProps: (stores) => {
            const box = get(stores.currentBox);
            if (box && box.id !== 0) {
                return {
                    initialPath: box.context,
                    title: `Terminal - ${box.name}`,
                };
            }
            return {};
        }
    },
];


// --- Window Creation Functions ---

export function newIoskConsole(props = {}) {
    const allWindowSettings = get(windowSettings);
    const componentSettings = allWindowSettings['IoskConsole'];
    const globalSettings = get(desktopSettings);

    windows.addWindow(IoskConsole, {
        title: 'IOSK Console',
        wsUrl: componentSettings?.defaultUrl ?? globalSettings.ioskUrl,
        username: componentSettings?.defaultUsername ?? globalSettings.ioskUsername,
        ...props,
    });
}
export function newCalculator(props = {}) {
    windows.addWindow(Calculator, { title: 'Calculator', width: 320, height: 450, ...props });
}
export function newCamera(props = {}) {
    windows.addWindow(Camera, { title: 'Camera', width: 640, height: 480, ...props });
}
export function newSettings(props = {}) {
    windows.addWindow(Settings, { title: 'Settings', width: 640, height: 711, ...props });
}
export function newNotificationCenter(props = {}) {
    const allWindows = get(windows);
    const existingNCTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'NotificationCenter');
    if (existingNCTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingNCTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingNCTab.id);
        return;
    }
    windows.addWindow(NotificationCenter, { title: 'Notifications', width: 475, height: 475, ...props });
}
export function newBoxesWindow(props = {}) {
    const allWindows = get(windows);
    const existingBoxesTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'Boxes');
    if (existingBoxesTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingBoxesTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingBoxesTab.id);
        return;
    }
    windows.addWindow(Boxes, { title: 'Boxes', width: 800, height: 800, ...props });
}

export function newProcessesWindow(props = {}) {
    const allWindows = get(windows);
    const existingProcessesTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'Processes');
    if (existingProcessesTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingProcessesTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingProcessesTab.id);
        return;
    }
    windows.addWindow(Processes, { title: 'Processes', width: 900, height: 600, ...props });
}

/**
 * Opens the Processes window (or focuses it if already open) and selects a specific process.
 * @param {number} pid - The process ID to select.
 */
export function showProcessesAndSelect(pid) {
    if (pid == null) return;

    const allWindows = get(windows);
    const existingProcessesTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'Processes');

    if (existingProcessesTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingProcessesTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingProcessesTab.id);
        
        // Signal the existing window to update its selection
        requestedPid.set(pid);
    } else {
        // Create a new window with the pid pre-selected
        windows.addWindow(Processes, { 
            title: 'Processes', 
            width: 900, 
            height: 600, 
            initialSelectedPid: pid 
        });
    }
}

/**
 * Opens the Boxes window (or focuses it if already open) and selects a specific box.
 * @param {number} boxId - The box ID to select.
 */
export function showBoxesAndSelect(boxId) {
    if (boxId == null) return;

    const allWindows = get(windows);
    const existingBoxesTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'Boxes');

    if (existingBoxesTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingBoxesTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingBoxesTab.id);

        // Signal existing window to update selection
        requestedBoxId.set(boxId);
    } else {
        // Create new window with the box pre-selected
        windows.addWindow(Boxes, {
            title: 'Boxes',
            width: 800,
            height: 800,
            initialSelectedBoxId: boxId
        });
    }
}

// --- UNIFIED FILE EXPLORER / VIEWER FUNCTIONS ---

// --- MODIFICATION START: Update to use connectionId and provide it as a title fallback ---
export function newFileExplorer(props = {}) {
    const { connectionType, connectionId, consoleTitle } = props;
    const title = connectionType === 'iosk' ? `Files - ${consoleTitle || connectionId}` : 'Local Files';
    const defaultProps = { title, width: 500, height: 600 };
    windows.addWindow(FileExplorer, { ...defaultProps, ...props });
}
// --- MODIFICATION END ---

export function newFileViewer(props = {}) {
    const title = (props.path || '').split('/').pop() || props.path;
    const defaultProps = { title: `View - ${title}`, width: 700, height: 500 };
    windows.addWindow(FileViewer, { ...defaultProps, ...props });
}

// --- LEGACY/SPECIFIC FUNCTIONS (Now call the unified functions) ---

// --- MODIFICATION START: Update function signature and logic to use connectionId ---
export function newIoskFileExplorer(props = {}) {
    const { connectionId } = props;
    if (!connectionId) return;

    const allWindows = get(windows);
    const consoleTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'IoskConsole' && t.connectionId === connectionId);
    const consoleTitle = consoleTab?.title;

    const explorerSettings = get(windowSettings)['IoskFileExplorer'];
    newFileExplorer({ 
        connectionType: 'iosk',
        connectionId,
        consoleTitle,
        initialPath: explorerSettings?.initialPath || '.',
        ...props 
    });
}
export function newIoskFileViewer(props = {}) {
    const { connectionId, path } = props;
    if (!connectionId || !path) return;
    newFileViewer({
        connectionType: 'iosk',
        connectionId,
        path,
        ...props
    });
}
// --- MODIFICATION END ---
export function newLocalFileExplorer(props = {}) {
    newFileExplorer({ connectionType: 'skybridge', ...props });
}
export function newLocalFileViewer(props = {}) {
    newFileViewer({ connectionType: 'skybridge', ...props });
}

// --- Other window creation functions ---

export function newWebBrowser(props = {}) {
    const browserSettings = get(windowSettings)['WebBrowser'];
    const initialUrl = browserSettings?.defaultUrl || (typeof window !== 'undefined' ? window.location.origin : 'about:blank');
    windows.addWindow(WebBrowser, { title: 'Web Browser', initialUrl, width: 1024, height: 768, ...props });
}
// --- MODIFICATION START: Update function signature and logic to use connectionId ---
export function newIoskPrivateChat(props = {}) {
    const { connectionId, localUser, remoteUser } = props;
    if (!connectionId || !localUser || !remoteUser) return;

    const allWindows = get(windows);
    const existingChatTab = allWindows.flatMap(g => g.tabs).find(t =>
        t.componentName === 'IoskPrivateChat' &&
        t.connectionId === connectionId &&
        t.remoteUser === remoteUser
    );

    if (existingChatTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingChatTab.id));
        if (group) {
            if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
            windows.setActiveTab(group.id, existingChatTab.id);
        }
        return;
    }
    const title = remoteUser.split('.')[0];
    windows.addWindow(IoskPrivateChat, {
        title: `Chat with ${title}`,
        connectionId,
        localUser,
        remoteUser,
        width: 450,
        height: 400,
        ...props
    });
}
// --- MODIFICATION END ---
export function newLocalTerminal(props = {}) {
    windows.addWindow(LocalTerminal, { title: 'Local Terminal', width: 800, height: 500, ...props });
}
export function newAskWindow(props = {}) {
    windows.addWindow(Ask, { title: 'Ask', initialFiles: [], width: 900, height: 600, ...props });
}
// --- MODIFICATION START: Update function signature and logic to use connectionId ---
export function newIoskWatch(props = {}) {
    const { connectionId, path } = props;
    if (!connectionId) return;

    const connectionState = get(activeIoskConnections).get(connectionId);
    if (!connectionState || connectionState.status !== 'connected') {
        alert("Cannot open Watch window. The selected console is not connected.");
        return;
    }
    windows.addWindow(IoskWatch, {
        title: 'Watch',
        connectionId,
        initialPwd: path,
        width: 700,
        height: 400,
        ...props
    });
}
export function newIoskUserInspector(props = {}) {
    const { connectionId, targetUser } = props;
    if (!connectionId || !targetUser) return;

    const allWindows = get(windows);
    const existingInspectorTab = allWindows.flatMap(g => g.tabs).find(t =>
        t.componentName === 'IoskUserInspector' &&
        !t.isDetached &&
        t.connectionId === connectionId &&
        t.targetUser === targetUser
    );

    if (existingInspectorTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingInspectorTab.id));
        if (group) {
            if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
            windows.setActiveTab(group.id, existingInspectorTab.id);
        }
        return;
    }

    const connectionState = get(activeIoskConnections).get(connectionId);
    if (!connectionState || connectionState.status !== 'connected') {
        alert("Cannot inspect context. The selected console is not connected.");
        return;
    }

    const title = `Inspector - ${targetUser}`;
    windows.addWindow(IoskUserInspector, {
        title,
        connectionId,
        targetUser,
        width: 700,
        height: 700,
        ...props
    });
}
// --- MODIFICATION END ---

export function newIoskConsoleForBox(box) {
    if (box.type !== 'iosk') return;

    const process = get(runningProcesses).find(p => p.box_id === box.id && p.status === 'running' && p.port);
    if (!process) {
        alert(`IOSK process for "${box.name}" is not running or has no network port.`);
        return;
    }

    const config = get(allIoskConfigs)[box.id];
    const username = config?.default_username || 'root';
    const wsUrl = `ws://localhost:${process.port}`;

    newIoskConsole({
        title: `IOSK - ${box.name}`,
        wsUrl,
        username
    });
}

export function newIoskFileExplorerForBox(box) {
    if (box.type !== 'iosk') return;

    const process = get(runningProcesses).find(p => p.box_id === box.id && p.status === 'running' && p.port);
     if (!process) {
        alert(`IOSK process for "${box.name}" is not running or has no network port.`);
        return;
    }

    const config = get(allIoskConfigs)[box.id];
    const username = config?.default_username || 'root';
    const wsUrl = `ws://localhost:${process.port}`;
    const connectionId = `${username}@${wsUrl}`;

    const connection = get(activeIoskConnections).get(connectionId);
    if (!connection || connection.status !== 'connected') {
        alert(`Not connected to IOSK process for "${box.name}". Please open an IOSK Console first to establish a connection.`);
        return;
    }

    newIoskFileExplorer({ connectionId });
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
    
    createBox(name, 'local', context, { aspectRatio, screenX: candidatePos.x * zoom + panX, screenY: candidatePos.y * zoom + panY + TASKBAR_HEIGHT });
}

// --- MODIFICATION START: Update the store to use connectionId ---
export const activeConsoles = readable(new Map(), set => {
    const unsubscribe = windows.subscribe(allWindows => {
        const newActiveConsoles = new Map();
        for (const group of allWindows) {
            for (const tab of group.tabs) {
                // --- MODIFICATION: Remove obsolete property check ---
                if (tab.componentName === 'IoskConsole' && tab.connectionId) {
                    const key = tab.connectionId;
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
// --- MODIFICATION END ---
