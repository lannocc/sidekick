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
import { TASKBAR_HEIGHT, desktopSettings, windowSettings, desktopView } from './desktop.js';
import { createBox, boxes, desktopShortcuts, backedWindows } from './bridge.js';
import { windows } from './windows.js';


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
export function newCamera(props = {}) {
    windows.addWindow(Camera, { title: 'Camera', width: 640, height: 480, ...props });
}
export function newSettings(props = {}) {
    windows.addWindow(Settings, { title: 'Settings', width: 640, height: 711, ...props });
}
export function newNotificationCenter(props = {}) {
    const allWindows = get(windows);
    const existingNCTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'NotificationCenter' || t.componentName === 'NotificationCenter');
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
    const existingBoxesTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'Boxes' || t.componentName === 'Boxes');
    if (existingBoxesTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingBoxesTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingBoxesTab.id);
        return;
    }
    windows.addWindow(Boxes, { title: 'Boxes', width: 760, height: 600, ...props });
}

// --- UNIFIED FILE EXPLORER / VIEWER FUNCTIONS ---

export function newFileExplorer(props = {}) {
    const { connectionType, consoleId, consoleTitle } = props;
    const title = connectionType === 'iosk' ? `Files - ${consoleTitle || `Console ${consoleId}`}` : 'Local Files';
    const defaultProps = { title, width: 500, height: 600 };
    windows.addWindow(FileExplorer, { ...defaultProps, ...props });
}

export function newFileViewer(props = {}) {
    const title = (props.path || '').split('/').pop() || props.path;
    const defaultProps = { title: `View - ${title}`, width: 700, height: 500 };
    windows.addWindow(FileViewer, { ...defaultProps, ...props });
}

// --- LEGACY/SPECIFIC FUNCTIONS (Now call the unified functions) ---

export function newIoskFileExplorer(consoleTabId, consoleTitle, props = {}) {
    const explorerSettings = get(windowSettings)['IoskFileExplorer'];
    newFileExplorer({ 
        connectionType: 'iosk',
        consoleId: consoleTabId,
        consoleTitle,
        initialPath: explorerSettings?.initialPath || '.',
        ...props 
    });
}
export function newIoskFileViewer(consoleTabId, path, props = {}) {
    newFileViewer({
        connectionType: 'iosk',
        consoleId: consoleTabId,
        path,
        ...props
    });
}
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
export function newIoskPrivateChat(consoleTabId, localUser, remoteUser, props = {}) {
    const allWindows = get(windows);
    const existingChatTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'IoskPrivateChat' && t.consoleId === consoleTabId && t.remoteUser === remoteUser);
    if (existingChatTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingChatTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingChatTab.id);
        return;
    }
    const title = remoteUser.split('.')[0];
    windows.addWindow(IoskPrivateChat, { title: `Chat with ${title}`, consoleId: consoleTabId, localUser, remoteUser, width: 450, height: 400, ...props });
}
export function newLocalTerminal(props = {}) {
    windows.addWindow(LocalTerminal, { title: 'Local Terminal', width: 800, height: 500, ...props });
}
export function newAskWindow(props = {}) {
    windows.addWindow(Ask, { title: 'Ask', initialFiles: [], width: 900, height: 600, ...props });
}
export function newIoskWatch(consoleTabId, pwd, props = {}) {
    const allWindows = get(windows);
    const consoleTab = allWindows.flatMap(g => g.tabs).find(t => t.id === consoleTabId);
    if (!consoleTab || !consoleTab.isConsoleConnected) {
        alert("Cannot open Watch window. The selected console is not connected.");
        return;
    }
    windows.addWindow(IoskWatch, { title: 'Watch', consoleId: consoleTabId, consoleConnection: consoleTab.consoleConnection, initialPwd: pwd, width: 700, height: 400, ...props });
}
export function newIoskUserInspector(consoleTabId, targetUser, consoleWs, props = {}) {
    const allWindows = get(windows);
    const existingInspectorTab = allWindows.flatMap(g => g.tabs).find(t => t.componentName === 'IoskUserInspector' && !t.isDetached && t.consoleId === consoleTabId && t.targetUser === targetUser);
    if (existingInspectorTab) {
        const group = allWindows.find(g => g.tabs.some(t => t.id === existingInspectorTab.id));
        if (group.minimized) windows.toggleMinimize(group.id); else windows.focusWindow(group.id);
        windows.setActiveTab(group.id, existingInspectorTab.id);
        return;
    }
    const consoleTab = allWindows.flatMap(g => g.tabs).find(t => t.id === consoleTabId);
    if (!consoleTab || !consoleTab.isConsoleConnected) {
        alert("Cannot inspect context. The selected console is not connected.");
        return;
    }
    const title = `Inspector - ${targetUser}`;
    windows.addWindow(IoskUserInspector, { title, consoleId: consoleTabId, targetUser: targetUser, consoleWs: consoleWs, consoleConnection: consoleTab.consoleConnection, width: 700, height: 700, ...props });
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