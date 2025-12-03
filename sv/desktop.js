import { writable, get } from 'svelte/store';

export const TASKBAR_HEIGHT = 40; // Height of the taskbar in pixels

// Function to load settings from localStorage, or return defaults
function loadSettings() {
    const defaults = {
        bgType: 'gradient', // 'gradient', 'color', 'image'
        bgColor: '#34495e',
        bgGradientStart: '#2c3e50',
        bgGradientEnd: '#46627f',
        bgImage: '',
        bgImageDisplayMode: 'cover', // 'cover', 'contain', 'stretch', 'tile'
        focusFollowsMouse: false,
        focusDelay: 420,
        ioskUrl: 'ws://localhost:4209',
        ioskUsername: 'root',
        chimeType: 'beep.wav', // filename from assets, 'none', or 'custom'
        chimeUrl: '',          // URL for custom chime
        noticeDefaults: {
            enabled: true,
            visual: {
                enabled: true,
                color: '#f39c12', // Default: Orange
                duration: 1200,   // ms
            },
            audio: {
                enabled: true,
                sound: 'ding.wav', // Default: Ding
                url: '',
            }
        },
        panX: 0,
        panY: 0,
        zoom: 1.0,
        // Add settings for the front (window) layer view
        windowPanX: 0,
        windowPanY: 0,
        windowZoom: 1.0
    };

    try {
        if (typeof localStorage !== 'undefined') {
            const saved = localStorage.getItem('sidekickDesktopSettings');
            if (saved) {
                const parsed = JSON.parse(saved);
                // Merge saved settings with defaults to ensure new properties are added
                return { ...defaults, ...parsed };
            }
        }
    } catch (e) {
        console.error("Could not load settings from localStorage", e);
    }
    // Return defaults if nothing is saved or an error occurs
    return defaults;
}

// Function to load dash layouts from localStorage
function loadDashLayouts() {
    const defaults = []; // No saved layouts by default
    try {
        if (typeof localStorage !== 'undefined') {
            const saved = localStorage.getItem('sidekickDashLayouts');
            if (saved) {
                return JSON.parse(saved);
            }
        }
    } catch (e) {
        console.error("Could not load dash layouts from localStorage", e);
    }
    return defaults;
}

// Function to load window settings from localStorage
function loadWindowSettings() {
    const defaults = {};
    try {
        if (typeof localStorage !== 'undefined') {
            const saved = localStorage.getItem('sidekickWindowSettings');
            if (saved) {
                return JSON.parse(saved);
            }
        }
    } catch (e) {
        console.error("Could not load window settings from localStorage", e);
    }
    return defaults;
}

export const desktopSettings = writable(loadSettings());

// Subscribe to changes and save them to localStorage
desktopSettings.subscribe(value => {
    try {
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('sidekickDesktopSettings', JSON.stringify(value));
        }
    } catch (e) {
        console.error("Could not save settings to localStorage", e);
    }
});

// Store for managing the dash mode's active state
export const dashActive = writable(false);

// Store for saved dash layouts
export const dashLayouts = writable(loadDashLayouts());

// Subscribe to changes and save layouts to localStorage
dashLayouts.subscribe(value => {
    try {
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('sidekickDashLayouts', JSON.stringify(value));
        }
    } catch (e) {
        console.error("Could not save dash layouts to localStorage", e);
    }
});

// Store for cycling through dash layouts via keyboard
export const dashCycleIndex = writable(-1);

// Store for window default settings
export const windowSettings = writable(loadWindowSettings());

// Subscribe to changes and save window settings to localStorage
windowSettings.subscribe(value => {
    try {
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('sidekickWindowSettings', JSON.stringify(value));
        }
    } catch (e) {
        console.error("Could not save window settings to localStorage", e);
    }
});

// Store for BACK layer pan and zoom. Synced with backend.
export const desktopView = writable({ panX: 0, panY: 0, zoom: 1.0 });

// New store for FRONT layer (windows) pan and zoom. Synced with localStorage.
export const windowView = writable({ panX: 0, panY: 0, zoom: 1.0 });

// Initialize windowView from localStorage and subscribe to save its changes.
const initialSettings = get(desktopSettings);
windowView.set({
    panX: initialSettings.windowPanX || 0,
    panY: initialSettings.windowPanY || 0,
    zoom: initialSettings.windowZoom || 1.0
});
windowView.subscribe(value => {
    desktopSettings.update(settings => ({
        ...settings,
        windowPanX: value.panX,
        windowPanY: value.panY,
        windowZoom: value.zoom
    }));
});


// New store for selected desktop items
export const selectedItems = writable(new Set());

// New store to track dragging state to suppress clicks
export const wasDraggingItems = writable(false);


// New stores for Notification Center
export const notificationHistory = writable([]);
export const unreadNoticeCount = writable(0);