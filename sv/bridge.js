import { writable, get } from 'svelte/store';
import { desktopSettings, desktopView, windowView, TASKBAR_HEIGHT, currentBoxId, mergeWithDefaults } from './desktop.js';
import { v4 as uuidv4 } from 'uuid';

const PORT = 4210;
const URL = `ws://localhost:${PORT}`;

let socket;
let reconnectTimer;
const RECONNECT_DELAY = 3000; // 3 seconds
// REMOVED: let ignoreNextSettingsUpdateForCurrentBox = false;

export const connectionStatus = writable('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'

// Stores for different message types
export const terminalData = writable(null);
export const terminalExit = writable(null);
export const fsListResponse = writable(null);
export const fsReadResponse = writable(null);
export const fsError = writable(null);
export const fsWatchEvent = writable(null);
export const fsTailEvent = writable(null);
export const askOutput = writable(null);
export const askError = writable(null);
export const askExit = writable(null);
export const askStatsResponse = writable(null);
export const boxes = writable([]);
export const backedWindows = writable([]);

// --- ProcBox Stores ---
export const runningProcesses = writable([]);
export const ioskConfigResponse = writable(null);
export const processOutput = writable(null);


// --- Asset Resolution for local files ---
const pendingRequests = new Map();
const assetCache = new Map();

fsReadResponse.subscribe(msg => {
    if (msg && pendingRequests.has(msg.requester_id)) {
        const { resolve } = pendingRequests.get(msg.requester_id);
        resolve(msg);
        pendingRequests.delete(msg.requester_id);
    }
});

fsError.subscribe(err => {
     if (err && pendingRequests.has(err.requester_id)) {
        const { reject } = pendingRequests.get(err.requester_id);
        reject(new Error(err.error));
        pendingRequests.delete(err.requester_id);
    }
});

function readFileChunk(path, offset = 0, length = -1) {
    const requester_id = uuidv4();
    return new Promise((resolve, reject) => {
        pendingRequests.set(requester_id, { resolve, reject });
        sendMessage({ type: 'fs_read', path, offset, length, requester_id });
    });
}

export async function resolveAssetDataUrl(url) {
    if (!url || !url.startsWith('file://')) {
        return url;
    }
    if (assetCache.has(url)) {
        return assetCache.get(url);
    }

    const path = url.substring('file://'.length);
    const promise = readFileChunk(path).then(response => {
        // Simple MIME type detection
        const extension = path.split('.').pop().toLowerCase();
        let mimeType = 'application/octet-stream';
        const imageExtensions = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp',
        };
        if (imageExtensions[extension]) {
            mimeType = imageExtensions[extension];
        }
        const dataUrl = `data:${mimeType};base64,${response.content_b64}`;
        assetCache.set(url, dataUrl);
        return dataUrl;
    });

    assetCache.set(url, promise); // Cache the promise itself to handle concurrent requests
    return promise;
}

// --- Style Generation Utility ---
export function generateBgStyle(bgSettings, resolvedUrl) {
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
        const imageUrl = resolvedUrl || bgSettings.bgImage;
        return `url('${imageUrl}') ${position} / ${size} ${repeat}`;
    }
    return null;
}


// --- Stores for inspecting arbitrary boxes ---
export const shortcutListResponse = writable(null);
export const backedWindowListResponse = writable(null);
export const desktopSettingsResponse = writable(null);
export const specificSettingsResponse = writable(null); // For specific settings requests
export const allBoxSettings = writable({}); // map of box_id -> settings object

// --- Desktop Shortcuts Store ---
const { subscribe: shortcutsSubscribe, set: shortcutsSet, update: shortcutsUpdate } = writable([]);
export const desktopShortcuts = {
    subscribe: shortcutsSubscribe,
    set: shortcutsSet, // Expose set for clearing on box switch
    update: shortcutsUpdate,
    add: (shortcut) => {
        // FIX: The original implementation had a key collision on 'type'.
        // The message type ('create_shortcut') was being overwritten by the shortcut type ('dir' or 'file').
        // We now destructure the shortcut's type into a new key 'shortcut_type' to avoid this.
        const { type: shortcutType, ...rest } = shortcut;
        sendMessage({
            type: 'create_shortcut',
            shortcut_type: shortcutType,
            box_id: get(currentBoxId),
            ...rest
        });
    },
    remove: (id) => {
        sendMessage({ type: 'delete_shortcut', id });
    }
};


let messageQueue = [];

function processQueue() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        while (messageQueue.length > 0) {
            const message = messageQueue.shift();
            socket.send(JSON.stringify(message));
        }
    }
}

export function sendMessage(message) {
    messageQueue.push(message);
    processQueue();
}

export function switchToBox(boxId) {
    console.log(`Switching to box ${boxId}`);
    currentBoxId.set(boxId);

    // Clear out old content to avoid flicker/stale data
    desktopShortcuts.set([]);
    backedWindows.set([]);

    // Request new content for the new virtual desktop
    sendMessage({ type: 'get_desktop_settings', box_id: boxId });
    sendMessage({ type: 'get_shortcut_list', box_id: boxId });
    sendMessage({ type: 'get_backed_window_list', box_id: boxId });
}

export function clearSettingsForBox(targetBoxId) {
    sendMessage({ type: 'clear_box_settings', box_id: targetBoxId });
    // The backend will now broadcast the updated (empty) specific settings for this box,
    // which keeps our local `allBoxSettings` cache in sync automatically.
}


export function createBox(name, box_type, context, { aspectRatio, screenX, screenY, parent_box_id } = {}) {
    let finalAspectRatio = aspectRatio;
    if (finalAspectRatio == null) { // Checks for both null and undefined
        const desktopHeight = window.innerHeight - TASKBAR_HEIGHT;
        finalAspectRatio = (desktopHeight > 0 && window.innerWidth > 0) ? desktopHeight / window.innerWidth : 0;
    }

    let worldX, worldY;
    const { panX, panY, zoom } = get(desktopView);
    const BASE_BOX_WIDTH = 180;
    const boxWidth = BASE_BOX_WIDTH;
    const boxHeight = boxWidth * finalAspectRatio;

    if (screenX != null && screenY != null) {
        // Convert screen coordinates to world coordinates for top-left of the box
        worldX = (screenX - panX) / zoom;
        worldY = (screenY - TASKBAR_HEIGHT - panY) / zoom;
    } else {
        // Default to center of the current view
        worldX = ((window.innerWidth / 2) - panX) / zoom - (boxWidth / 2);
        worldY = (((window.innerHeight - TASKBAR_HEIGHT) / 2) - panY) / zoom - (boxHeight / 2);
    }

    sendMessage({ type: 'create_box', name, box_type, context, aspect_ratio: finalAspectRatio, x: worldX, y: worldY, parent_box_id });
}
export function updateBox(id, name) {
    sendMessage({ type: 'update_box', id, name });
}
export function deleteBox(id) {
    sendMessage({ type: 'delete_box', id });
}

// --- ProcBox Functions ---
export function promoteToIosk(box_id) {
    sendMessage({ type: 'promote_to_iosk', box_id });
}

export function getIoskConfig(box_id) {
    sendMessage({ type: 'get_iosk_config', box_id });
}

export function updateIoskConfig(box_id, config) {
    sendMessage({ type: 'update_iosk_config', box_id, config });
}

export function startIosk(box_id) {
    sendMessage({ type: 'start_iosk', box_id });
}

export function stopProcess(pid) {
    sendMessage({ type: 'stop_process', pid });
}

export function listRunningProcesses() {
    sendMessage({ type: 'list_running_processes' });
}

export function pauseProcess(pid) {
    sendMessage({ type: 'pause_process', pid });
}

export function resumeProcess(pid) {
    sendMessage({ type: 'resume_process', pid });
}

export function killProcess(pid) {
    sendMessage({ type: 'kill_process', pid });
}

export function sendProcessStdin(pid, data) {
    sendMessage({ type: 'process_stdin', pid, data });
}
// --- End ProcBox Functions ---


export function getBoxConfig(id) {
    sendMessage({ type: 'get_box_config', id });
}
export function savePanelConfig(box_id, loc_x, loc_y, board_type, board_config, parent) {
    const message = { type: 'set_panel_config', box_id, loc_x, loc_y, board_type, board_config };
    if (parent && parent.x != null && parent.y != null) {
        message.parent_loc_x = parent.x;
        message.parent_loc_y = parent.y;
    } else if (loc_x === 0 && loc_y === 0) {
        message.parent_loc_x = null;
        message.parent_loc_y = null;
    }
    sendMessage(message);
}
export function updateBoxTransform(id, x, y, scale) {
    sendMessage({ type: 'update_box_transform', id, x, y, scale });
}
export function setBoxCover(box_id, location) {
    sendMessage({ type: 'set_box_cover', box_id, location });
}

function updateViewSettings(viewSettings) {
    sendMessage({ type: 'update_view_settings', settings: viewSettings, box_id: get(currentBoxId) });
}


export function updateDesktopSettings(partialSettings) {
    const newSettings = { ...get(desktopSettings), ...partialSettings };
    desktopSettings.set(newSettings); // Update the store, which will trigger saves

    const { panX, panY, zoom, windowPanX, windowPanY, windowZoom, ...themeSettings } = newSettings;
    sendMessage({ type: 'update_desktop_settings', settings: themeSettings, box_id: get(currentBoxId) });
}
export function saveSettingsToBox(targetBoxId) {
    const fullSettings = get(desktopSettings);
    const { panX, panY, zoom, windowPanX, windowPanY, windowZoom, ...themeSettings } = fullSettings;
    sendMessage({ type: 'update_desktop_settings', settings: themeSettings, box_id: targetBoxId });
}
export function updateShortcutTransform(id, x, y, scale) {
    sendMessage({ type: 'update_shortcut_transform', id, x, y, scale });
}

export function createBackedWindow(config, x, y, width, height, scale = 1.0, originalGroupId) {
    sendMessage({ type: 'create_backed_window', config, x, y, width, height, scale, original_group_id: originalGroupId, box_id: get(currentBoxId) });
}
export function updateBackedWindowTransform(id, x, y, scale, config) {
    const message = { type: 'update_backed_window_transform', id, x, y, scale };
    if (config) {
        message.config = JSON.stringify(config);
    }
    sendMessage(message);
}
export function deleteBackedWindow(id) {
    sendMessage({ type: 'delete_backed_window', id });
}

// --- Getters for inspecting arbitrary boxes ---
export function getShortcuts(box_id) {
    sendMessage({ type: 'get_shortcut_list', box_id });
}
export function getBackedWindows(box_id) {
    sendMessage({ type: 'get_backed_window_list', box_id });
}
export function getDesktopSettings(box_id) {
    sendMessage({ type: 'get_desktop_settings', box_id });
}
export function getBoxSpecificSettings(box_id) {
    sendMessage({ type: 'get_box_specific_settings', box_id });
}

function setupViewSettingsPersistence() {
    let debounceTimer;
    const saveViewSettings = () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const dv = get(desktopView);
            const wv = get(windowView);
            const viewSettings = {
                panX: dv.panX, panY: dv.panY, zoom: dv.zoom,
                windowPanX: wv.panX, windowPanY: wv.panY, windowZoom: wv.zoom,
            };
            updateViewSettings(viewSettings);
        }, 500); // Debounce updates by 500ms
    };

    desktopView.subscribe(saveViewSettings);
    windowView.subscribe(saveViewSettings);
}


function attemptConnection() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        return;
    }

    connectionStatus.set('connecting');
    socket = new WebSocket(URL);

    socket.onopen = () => {
        connectionStatus.set('connected');
        sendMessage({ type: 'list_boxes' });
        sendMessage({ type: 'list_running_processes' });
        switchToBox(0); // Load the main desktop content
        setupViewSettingsPersistence(); // Persist pan/zoom changes
        processQueue(); // Send any messages that were were queued
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            switch (msg.type) {
                case 'term_data':
                    terminalData.set(msg);
                    break;
                case 'term_exit':
                    terminalExit.set(msg);
                    break;
                case 'fs_list_response':
                    fsListResponse.set(msg);
                    break;
                case 'fs_read_response':
                    fsReadResponse.set(msg);
                    break;
                case 'fs_error':
                    fsError.set(msg);
                    break;
                case 'fs_watch_event':
                    fsWatchEvent.set({ ...msg, timestamp: Date.now() });
                    break;
                case 'fs_tail_event':
                    fsTailEvent.set({ ...msg, timestamp: Date.now() });
                    break;
                case 'ask_output':
                    askOutput.set({ ...msg, timestamp: Date.now() });
                    break;
                case 'ask_error':
                    askError.set({ ...msg, timestamp: Date.now() });
                    break;
                case 'ask_exit':
                    askExit.set({ ...msg, timestamp: Date.now() });
                    break;
                case 'ask_stats_response':
                    askStatsResponse.set({ ...msg, timestamp: Date.now() });
                    break;
                case 'desktop_settings':
                    desktopSettingsResponse.set(msg);
                    // Do NOT update allBoxSettings here. It holds specific settings, not resolved ones.
                    if (msg.box_id === get(currentBoxId)) {
                        if (msg.settings && Object.keys(msg.settings).length > 0) {
                            // This will set the entire theme and also trigger the derived
                            // stores (desktopView, windowView) to update.
                            const fullSettings = mergeWithDefaults(msg.settings);
                            desktopSettings.set(fullSettings);
                        } else {
                             // Fallback if backend sends empty settings for some reason
                            desktopView.set({ panX: 0, panY: 0, zoom: 1.0 });
                        }
                    }
                    break;
                case 'box_specific_settings_response':
                    specificSettingsResponse.set(msg);
                    if (msg.settings) {
                        allBoxSettings.update(s => ({...s, [msg.box_id]: msg.settings}));
                    }
                    break;
                case 'shortcut_list':
                    shortcutListResponse.set(msg);
                    if (msg.box_id === get(currentBoxId)) {
                        shortcutsSet(msg.shortcuts || []);
                    }
                    break;
                case 'backed_window_list':
                    const windows = (msg.windows || []).map(w => ({
                        ...w,
                        config: JSON.parse(w.config)
                    }));
                    backedWindowListResponse.set({ ...msg, windows: windows });
                    if (msg.box_id === get(currentBoxId)) {
                        backedWindows.set(windows);
                    }
                    break;
                case 'box_list':
                    const newBoxesFromBackend = msg.boxes;
                    boxes.update(currentBoxes => {
                        const currentBoxMap = new Map(currentBoxes.map(b => [b.id, b]));
                        const updatedBoxes = newBoxesFromBackend.map(b => {
                            const existingBox = currentBoxMap.get(b.id);
                            return {
                                ...b, // name, type, context, x, y, scale, cover_panel_location, has_custom_settings from backend
                                panels: existingBox ? existingBox.panels : {} // preserve panels
                            };
                        });
                        // Fetch configs for any box that doesn't have them yet.
                        updatedBoxes.forEach(b => {
                            if (b.panels && Object.keys(b.panels).length === 0) {
                                getBoxConfig(b.id);
                            }
                        });
                        return updatedBoxes;
                    });
                    break;
                case 'box_config_response':
                    boxes.update(allBoxes => {
                        return allBoxes.map(box => {
                            if (box.id === msg.box_id) {
                                const panelMap = msg.panels.reduce((acc, panel) => {
                                    acc[`${panel.loc_x}_${panel.loc_y}`] = panel;
                                    return acc;
                                }, {});
                                return { ...box, panels: panelMap }; // Return new object for reactivity
                            }
                            return box;
                        });
                    });
                    break;
                // --- ProcBox Handlers ---
                case 'running_processes_list':
                    runningProcesses.set(msg.processes || []);
                    break;
                case 'iosk_config_response':
                    ioskConfigResponse.set(msg);
                    break;
                case 'process_output':
                    processOutput.set({ ...msg, timestamp: Date.now() });
                    break;
                default:
                    console.warn('Unknown message type from local backend:', msg.type);
            }
        } catch (e) {
            console.error('Error parsing message from local backend:', e);
        }
    };

    socket.onclose = () => {
        connectionStatus.set('disconnected');
        socket = null;
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
                // The timer has fired. Clear the handle so a new one can be set on the next failure.
                reconnectTimer = null;
                attemptConnection();
            }, RECONNECT_DELAY);
        }
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        connectionStatus.set('error');
        socket = null; // onclose will be called which handles reconnect
    };
}

// Single entry point to start and manage the connection.
export function initializeLocalConnection() {
    attemptConnection();
}