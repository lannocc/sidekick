import { writable } from 'svelte/store';
import { 
    fileSystemRequests, 
    fileSystemResponses, 
    fileSystemWatchEvents, 
    fileSystemTailEvents 
} from './iosk.js';
import { 
    sendMessage, 
    fsListResponse, 
    fsReadResponse, 
    fsError 
} from '../bridge.js';

export function createFsAdapter({ connectionType, consoleId, requesterId }) {
    // Public stores for components to subscribe to
    const listResponse = writable(null);
    const readResponse = writable(null);
    const watchEvent = writable(null);
    const tailEvent = writable(null);

    // Internal list of unsubscribe functions for cleanup
    let unsubscribers = [];

    if (connectionType === 'iosk') {
        unsubscribers.push(fileSystemResponses.subscribe(msg => {
            if (msg && msg.requesterId === requesterId) {
                if (msg.data.type === 'fs_list_response') {
                    listResponse.set({ path: msg.data.path, entries: msg.data.listing, error: msg.data.error });
                } else if (msg.data.type === 'fs_read_response') {
                    readResponse.set(msg.data); // Forward the whole data object
                }
            }
        }));

        unsubscribers.push(fileSystemWatchEvents.subscribe(event => {
            if (event && event.consoleId === consoleId) {
                watchEvent.set(event.data);
            }
        }));

        unsubscribers.push(fileSystemTailEvents.subscribe(event => {
            if (event && event.consoleId === consoleId) {
                tailEvent.set(event.data);
            }
        }));

    } else { // 'skybridge'
        unsubscribers.push(fsListResponse.subscribe(msg => {
            if (msg) {
                // Normalize to the common format
                listResponse.set({ path: msg.path, entries: msg.entries, error: null });
            }
        }));

        unsubscribers.push(fsReadResponse.subscribe(msg => {
            if (msg) {
                // Normalize the skybridge response to match the more detailed iosk format
                try {
                    const content_b64 = btoa(unescape(encodeURIComponent(msg.content))); // UTF-8 safe btoa
                    readResponse.set({
                        path: msg.path,
                        content_b64,
                        is_binary: false, // skybridge backend doesn't detect this; assume text.
                        total_size: msg.content.length,
                        offset: 0,
                        length: -1, // Indicates full file content was sent
                        error: null,
                    });
                } catch (e) {
                    console.error(`Encoding failed for path ${msg.path}:`, e);
                    readResponse.set({
                        path: msg.path,
                        error: "Could not encode file content for display."
                    });
                }
            }
        }));

        unsubscribers.push(fsError.subscribe(err => {
            if (err) {
                // Bridge provides a single error stream. We update both responses.
                // The component can filter by the path property to see if it's relevant.
                listResponse.set({ path: err.path, error: err.error, entries: [] });
                readResponse.set({ path: err.path, error: err.error });
            }
        }));
    }

    // Return the public API for the component to use
    return {
        listResponse,
        readResponse,
        watchEvent,
        tailEvent,

        requestPath: (path, recursive = false, honor_skignore = false) => {
            if (connectionType === 'iosk') {
                const command = { type: 'fs_list', path, recursive, honor_skignore };
                fileSystemRequests.set({ consoleId, requesterId, command, timestamp: Date.now() });
            } else {
                sendMessage({ type: 'fs_list', path });
            }
        },

        readFile: (path, offset = 0, length = -1) => {
            if (connectionType === 'iosk') {
                const command = { type: 'fs_read', path, offset, length };
                fileSystemRequests.set({ consoleId, requesterId, command, timestamp: Date.now() });
            } else {
                // skybridge doesn't support chunking; always request the whole file.
                sendMessage({ type: 'fs_read', path });
            }
        },

        watch: (path) => {
            if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_watch_start', path }, timestamp: Date.now() });
            }
        },
        unwatch: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_watch_stop', path }, timestamp: Date.now() });
            }
        },

        tail: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_tail_start', path }, timestamp: Date.now() });
            }
        },
        untail: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_tail_stop', path }, timestamp: Date.now() });
            }
        },

        destroy: () => {
            unsubscribers.forEach(unsub => unsub());
        }
    };
}