import { writable } from 'svelte/store';

const PORT = 4210;
const URL = `ws://localhost:${PORT}`;

let socket;

export const connectionStatus = writable('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'

// Stores for different message types
export const terminalData = writable(null);
export const fsListResponse = writable(null);
export const fsReadResponse = writable(null);
export const fsError = writable(null);

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

export function connect() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        return;
    }

    connectionStatus.set('connecting');
    socket = new WebSocket(URL);

    socket.onopen = () => {
        connectionStatus.set('connected');
        processQueue(); // Send any messages that were queued
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
                default:
                    console.warn('Unknown message type from local agent:', msg.type);
            }
        } catch (e) {
            console.error('Error parsing message from local agent:', e);
        }
    };

    socket.onclose = () => {
        connectionStatus.set('disconnected');
        socket = null;
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        connectionStatus.set('error');
        socket = null;
    };
}
