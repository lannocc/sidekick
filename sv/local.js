import { writable, get } from 'svelte/store';
import { desktopView } from './desktop.js';

const PORT = 4210;
const URL = `ws://localhost:${PORT}`;

let socket;
let reconnectTimer;
const RECONNECT_DELAY = 3000; // 3 seconds

export const connectionStatus = writable('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'

// Stores for different message types
export const terminalData = writable(null);
export const terminalExit = writable(null);
export const fsListResponse = writable(null);
export const fsReadResponse = writable(null);
export const fsError = writable(null);
export const askOutput = writable(null);
export const askError = writable(null);
export const askExit = writable(null);
export const askStatsResponse = writable(null);
export const boxes = writable([]);

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

export function createBox(name, box_type, context) {
    sendMessage({ type: 'create_box', name, box_type, context });
}
export function updateBox(id, name) {
    sendMessage({ type: 'update_box', id, name });
}
export function deleteBox(id) {
    sendMessage({ type: 'delete_box', id });
}
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
export function updateDesktopSettings(settings) {
    sendMessage({ type: 'update_desktop_settings', settings });
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
                    desktopView.set(msg.settings || { panX: 0, panY: 0, zoom: 1.0 });
                    break;
                case 'box_list':
                    const newBoxesFromBackend = msg.boxes;
                    boxes.update(currentBoxes => {
                        const currentBoxMap = new Map(currentBoxes.map(b => [b.id, b]));
                        const updatedBoxes = newBoxesFromBackend.map(b => {
                            const existingBox = currentBoxMap.get(b.id);
                            return {
                                ...b, // name, type, context, x, y, scale, cover_panel_location from backend
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