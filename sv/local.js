import { writable } from 'svelte/store';

const PORT = 4210;
const URL = `ws://localhost:${PORT}`;

let socket;
let reconnectTimer;
const RECONNECT_DELAY = 3000; // 3 seconds

export const connectionStatus = writable('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'

// Stores for different message types
export const terminalData = writable(null);
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
                case 'box_list':
                    boxes.set(msg.boxes);
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
            reconnectTimer = setTimeout(attemptConnection, RECONNECT_DELAY);
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