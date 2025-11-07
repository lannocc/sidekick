import { writable } from 'svelte/store';

// Used for Explorer -> Console communication to request a directory listing
export const fileSystemRequests = writable(null);

// Used for Console -> Explorer communication to provide a directory listing
export const fileSystemResponses = writable(null);

