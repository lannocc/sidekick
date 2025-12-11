import { writable } from 'svelte/store';
import { fileSystemRequests, fileSystemResponses, fileSystemWatchEvents, fileSystemTailEvents } from './iosk.js';
import { sendMessage, fsListResponse, fsReadResponse, fsError } from '../bridge.js';

export function createFsAdapter({ connectionType, consoleId, requesterId }) {
    // Stores for the component to subscribe to.
    const listResponse = writable(null);
    const readResponse = writable(null);
    const watchEvent = writable(null);
    const tailEvent = writable(null);
    const errorResponse = writable(null);

    let unsubscribeIoskResponses, unsubscribeIoskWatch, unsubscribeIoskTail;
    let unsubscribeBridgeList, unsubscribeBridgeRead, unsubscribeBridgeError;

    if (connectionType === 'iosk') {
        unsubscribeIoskResponses = fileSystemResponses.subscribe(msg => {
            if (msg && msg.requesterId === requesterId) {
                if (msg.data.type === 'fs_list_response') {
                    // Normalize the iosk response structure to match the local one.
                    listResponse.set({
                        path: msg.data.path,
                        entries: msg.data.listing,
                        error: msg.data.error,
                    });
                } else if (msg.data.type === 'fs_read_response') {
                    readResponse.set(msg.data);
                }
            }
        });
        unsubscribeIoskWatch = fileSystemWatchEvents.subscribe(msg => {
            if (msg && msg.consoleId === consoleId) {
                watchEvent.set(msg.data);
            }
        });
        unsubscribeIoskTail = fileSystemTailEvents.subscribe(msg => {
            if (msg && msg.consoleId === consoleId) {
                tailEvent.set(msg.data);
            }
        });
    } else { // 'skybridge'
        unsubscribeBridgeList = fsListResponse.subscribe(msg => listResponse.set(msg));
        unsubscribeBridgeRead = fsReadResponse.subscribe(msg => {
            // Normalize the simple skybridge response to the richer iosk format.
            if (msg) {
                try {
                    const content_b64 = btoa(unescape(encodeURIComponent(msg.content || '')));
                    readResponse.set({
                        path: msg.path,
                        content_b64: content_b64,
                        is_binary: false, // skybridge does not yet support binary files.
                        total_size: content_b64.length,
                        length: content_b64.length,
                        error: null,
                    });
                } catch (e) {
                     errorResponse.set({ path: msg.path, error: 'Failed to decode file content.' });
                }
            }
        });
        unsubscribeBridgeError = fsError.subscribe(msg => {
            // Forward errors to both readResponse (for viewer) and the general error store.
             if (msg) {
                readResponse.set({ error: msg.error, path: msg.path });
                errorResponse.set(msg);
             }
        });
    }

    // Return the public API for the component to use.
    return {
        // Response stores
        listResponse,
        readResponse,
        watchEvent,
        tailEvent,
        errorResponse,

        // Action methods
        requestPath: (path, recursive, honor_skignore) => {
            if (connectionType === 'iosk') {
                fileSystemRequests.set({
                    consoleId,
                    requesterId,
                    command: { type: 'fs_list', path, recursive, honor_skignore }
                });
            } else {
                // skybridge doesn't support recursive yet, so ignore the flag.
                sendMessage({ type: 'fs_list', path });
            }
        },

        readFile: (path, offset = 0, length = -1) => {
            if (connectionType === 'iosk') {
                fileSystemRequests.set({
                    consoleId,
                    requesterId,
                    command: { type: 'fs_read', path, offset, length }
                });
            } else {
                // skybridge doesn't support offset/length yet.
                sendMessage({ type: 'fs_read', path });
            }
        },

        watch: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_watch_start', path } });
            }
        },

        unwatch: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_watch_stop', path } });
            }
        },
        
        tail: (path) => {
            if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_tail_start', path } });
            }
        },

        untail: (path) => {
            if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_tail_stop', path } });
            }
        },

        // Cleanup function for Svelte's onDestroy hook.
        destroy: () => {
            if (unsubscribeIoskResponses) unsubscribeIoskResponses();
            if (unsubscribeIoskWatch) unsubscribeIoskWatch();
            if (unsubscribeIoskTail) unsubscribeIoskTail();
            if (unsubscribeBridgeList) unsubscribeBridgeList();
            if (unsubscribeBridgeRead) unsubscribeBridgeRead();
            if (unsubscribeBridgeError) unsubscribeBridgeError();
        }
    };
}