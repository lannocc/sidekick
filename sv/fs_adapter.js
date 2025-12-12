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
    fsError,
    fsWatchEvent,
    fsTailEvent
} from './bridge.js';

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
                    listResponse.set({ path: msg.data.path, entries: msg.data.listing, error: msg.data.error, requester_id: msg.data.requester_id });
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
                // Normalize to the common format, but keep requester_id
                listResponse.set({ path: msg.path, entries: msg.entries, error: null, requester_id: msg.requester_id });
            }
        }));

        unsubscribers.push(fsReadResponse.subscribe(msg => {
            if (msg) {
                // The skybridge response now matches the detailed format, so just pass it through.
                readResponse.set(msg);
            }
        }));

        unsubscribers.push(fsError.subscribe(err => {
            if (err) {
                // Bridge provides a single error stream. We update both responses.
                // The component can filter by the path property to see if it's relevant.
                listResponse.set({ path: err.path, error: err.error, entries: [], requester_id: err.requester_id });
                readResponse.set({ path: err.path, error: err.error, requester_id: err.requester_id });
            }
        }));

        unsubscribers.push(fsWatchEvent.subscribe(event => {
            if (event) {
                watchEvent.set({
                    path: event.path,
                    type: event.event_type,
                    entry: {
                        name: event.entry_name,
                        type: event.is_dir ? 'dir' : 'file',
                        size: -1 // Size info not provided by bridge watcher
                    }
                });
            }
        }));

        unsubscribers.push(fsTailEvent.subscribe(event => {
            if (event) {
                tailEvent.set(event);
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
                sendMessage({ type: 'fs_list', path, recursive, requester_id: requesterId });
            }
        },

        readFile: (path, offset = 0, length = -1) => {
            if (connectionType === 'iosk') {
                const command = { type: 'fs_read', path, offset, length };
                fileSystemRequests.set({ consoleId, requesterId, command, timestamp: Date.now() });
            } else {
                sendMessage({ type: 'fs_read', path, offset, length, requester_id: requesterId });
            }
        },

        watch: (path) => {
            if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_watch_start', path }, timestamp: Date.now() });
            } else {
                sendMessage({ type: 'fs_watch_start', path });
            }
        },
        unwatch: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_watch_stop', path }, timestamp: Date.now() });
            } else {
                sendMessage({ type: 'fs_watch_stop', path });
            }
        },

        tail: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_tail_start', path }, timestamp: Date.now() });
            } else {
                sendMessage({ type: 'fs_tail_start', path });
            }
        },
        untail: (path) => {
             if (connectionType === 'iosk') {
                fileSystemRequests.set({ consoleId, command: { type: 'fs_tail_stop', path }, timestamp: Date.now() });
            } else {
                sendMessage({ type: 'fs_tail_stop', path });
            }
        },

        destroy: () => {
            unsubscribers.forEach(unsub => unsub());
        }
    };
}