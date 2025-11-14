import { writable } from 'svelte/store';

// Used for Explorer -> Console communication to request a directory listing
export const fileSystemRequests = writable(null);

// Used for Console -> Explorer communication to provide a directory listing
export const fileSystemResponses = writable(null);

// --- ADDED for filesystem events proposal ---
// Used for Console -> Components to broadcast live filesystem events
export const fileSystemWatchEvents = writable(null);
export const fileSystemTailEvents = writable(null);
// --- END ADDED ---

// Used for Private Chat -> Console to send a command/message
export const consoleCommands = writable(null);

// Used for Console -> Private Chat to deliver a received message
export const privateMessages = writable(null);

// Used for file picker communication
export const fileSelection = writable(null);