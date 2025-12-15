import { writable, get, derived } from 'svelte/store';
import { boxes } from './bridge.js';

export const TASKBAR_HEIGHT = 40; // Height of the taskbar in pixels

export const componentIconMap = {
    'Settings': '⚙️',
    'Calculator': '🧮',
    'WebBrowser': '🌐',
    'IoskConsole': '🖥️',
    'Ask': '?',
    'Boxes': '📦',
    'LocalFileExplorer': '📁',
    'LocalTerminal': '>_',
    'IoskFileExplorer': '📁',
    'IoskPrivateChat': '💬',
    'LocalFileViewer': '📄',
    'IoskFileViewer': '📄',
    'IoskWatch': '👀',
    'IoskUserInspector': '🕵️',
    'NotificationCenter': '🔔',
    'Camera': '📸',
    'default': '🗔'
};

// Define defaults as a standalone object
const defaultSettings = {
    sky: {
        scene: {
            bgType: 'gradient', // 'gradient', 'color', 'image'
            bgColor: '#34495e',
            bgGradientStart: '#2c3e50',
            bgGradientEnd: '#46627f',
            bgImage: '',
            bgImageDisplayMode: 'cover', // 'cover', 'contain', 'stretch', 'tile'
            opacity: 1.0,
        },
        frame: {
            bgType: 'color',
            bgColor: '#283645',
            bgGradientStart: '#283645',
            bgGradientEnd: '#415a74',
            bgImage: '',
            bgImageDisplayMode: 'cover',
            opacity: 1.0,
            height: 40,
            width: 0,
        },
        cloak: {
            bgType: 'image',
            bgColor: '#101010',
            bgGradientStart: '#111111',
            bgGradientEnd: '#222222',
            bgImage: '/skyboards.png',
            bgImageDisplayMode: 'stretch',
            opacity: 1,
        }
    },
    boxes: {
        scene: {
            active: {
                bgType: 'color', bgColor: '#4a5468', bgGradientStart: '', bgGradientEnd: '', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0,
            },
            inactive: {
                bgType: 'color', bgColor: '#434C5E', bgGradientStart: '', bgGradientEnd: '', bgImage: '', bgImageDisplayMode: 'cover', opacity: 0.9,
            }
        },
        frame: {
            active: {
                bgType: 'gradient', bgColor: '', bgGradientStart: '#88C0D0', bgGradientEnd: '#81A1C1', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, width: 2,
                shadowEnabled: true, shadowX: 0, shadowY: 0, shadowBlur: 8, shadowSpread: 1, shadowColor: '#88C0D090', shadowInset: false,
            },
            inactive: {
                bgType: 'color', bgColor: '#4C566A', bgGradientStart: '', bgGradientEnd: '', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, width: 2,
                shadowEnabled: false, shadowX: 0, shadowY: 0, shadowBlur: 0, shadowSpread: 0, shadowColor: 'rgba(0,0,0,0)', shadowInset: false,
            }
        },
        cloak: {
            inactive: {
                bgType: 'image', bgColor: '#121212', bgGradientStart: '#131313', bgGradientEnd: '#232323', bgImage: '/skybox.png', bgImageDisplayMode: 'cover', opacity: 1.0,
            }
        }
    },
    windows: {
        normal: {
            scene: {
                active: {
                    bgType: 'color', bgColor: '#333b3d', bgGradientStart: '#333b3d', bgGradientEnd: '#454e50', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0,
                },
                inactive: {
                    bgType: 'color', bgColor: '#2d3436', bgGradientStart: '#2d3436', bgGradientEnd: '#444d4f', bgImage: '', bgImageDisplayMode: 'cover', opacity: 0.95,
                },
            },
            frame: {
                active: {
                    bgType: 'color', bgColor: '#35485f', bgGradientStart: '#35485f', bgGradientEnd: '#506d8b', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, height: 30, width: 0,
                    shadowEnabled: true, shadowX: 0, shadowY: 5, shadowBlur: 15, shadowSpread: 0, shadowColor: 'rgba(0,0,0,0.3)', shadowInset: false,
                },
                inactive: {
                    bgType: 'color', bgColor: '#2b3d4f', bgGradientStart: '#2b3d4f', bgGradientEnd: '#45617e', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, height: 30, width: 0,
                    shadowEnabled: true, shadowX: 0, shadowY: 2, shadowBlur: 8, shadowSpread: 0, shadowColor: 'rgba(0,0,0,0.2)', shadowInset: false,
                },
            },
            cloak: {
                active: {
                    bgType: 'image', bgColor: '#141414', bgGradientStart: '#151515', bgGradientEnd: '#242424', bgImage: '/skyboard.png', bgImageDisplayMode: 'stretch', opacity: 1.0,
                },
                inactive: {
                    bgType: 'image', bgColor: '#161616', bgGradientStart: '#171717', bgGradientEnd: '#252525', bgImage: '/skyboard.png', bgImageDisplayMode: 'stretch', opacity: 0.77,
                },
            },
        },
        back: {
            scene: {
                active: {
                    bgType: 'color', bgColor: '#414859', bgGradientStart: '#414859', bgGradientEnd: '#4c566a', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0,
                },
                inactive: {
                    bgType: 'color', bgColor: '#3b4252', bgGradientStart: '#3b4252', bgGradientEnd: '#4b5569', bgImage: '', bgImageDisplayMode: 'cover', opacity: 0.8,
                },
            },
            frame: {
                active: {
                    bgType: 'color', bgColor: '#3a506a', bgGradientStart: '#3a506a', bgGradientEnd: '#4a637f', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, height: 0, width: 0,
                    shadowEnabled: true, shadowX: 0, shadowY: 5, shadowBlur: 15, shadowSpread: 0, shadowColor: 'rgba(0,0,0,0.35)', shadowInset: false,
                },
                inactive: {
                    bgType: 'color', bgColor: '#32475c', bgGradientStart: '#32475c', bgGradientEnd: '#49627e', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, height: 0, width: 0,
                    shadowEnabled: false, shadowX: 0, shadowY: 2, shadowBlur: 8, shadowSpread: 0, shadowColor: 'rgba(0,0,0,0.15)', shadowInset: false,
                },
            },
            cloak: {
                active: {
                    bgType: 'color', bgColor: '#181818', bgGradientStart: '#181818', bgGradientEnd: '#262626', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0,
                },
                inactive: {
                    bgType: 'color', bgColor: '#1a1a1a', bgGradientStart: '#1a1a1a', bgGradientEnd: '#272727', bgImage: '', bgImageDisplayMode: 'cover', opacity: 0.8,
                },
            },
        }
    },
    focusFollowsMouse: true,
    focusDelay: 420,
    ioskUrl: 'ws://localhost:4209',
    ioskUsername: 'root',
    chimeType: 'three_tones.wav', // filename from assets, 'none', or 'custom'
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

// Function to merge a partial settings object with the defaults to ensure a complete object.
export function mergeWithDefaults(parsed) {
    if (!parsed) return { ...defaultSettings };
    const defaults = defaultSettings;

    // Merge with defaults, handling nested objects
    const settings = { ...defaults, ...parsed };
    settings.sky = {
        scene: { ...defaults.sky.scene, ...(parsed.sky?.scene || {}) },
        frame: { ...defaults.sky.frame, ...(parsed.sky?.frame || {}) },
        cloak: { ...defaults.sky.cloak, ...(parsed.sky?.cloak || {}) },
    };
    settings.boxes = {
        scene: {
            active: { ...defaults.boxes.scene.active, ...(parsed.boxes?.scene?.active || {}) },
            inactive: { ...defaults.boxes.scene.inactive, ...(parsed.boxes?.scene?.inactive || {}) }
        },
        frame: {
            active: { ...defaults.boxes.frame.active, ...(parsed.boxes?.frame?.active || {}) },
            inactive: { ...defaults.boxes.frame.inactive, ...(parsed.boxes?.frame?.inactive || {}) }
        },
        cloak: {
            inactive: { ...defaults.boxes.cloak.inactive, ...(parsed.boxes?.cloak?.inactive || {}) }
        },
    };
    settings.windows = {
        normal: {
            scene: {
                active: { ...defaults.windows.normal.scene.active, ...(parsed.windows?.normal?.scene?.active || {}) },
                inactive: { ...defaults.windows.normal.scene.inactive, ...(parsed.windows?.normal?.scene?.inactive || {}) }
            },
            frame: {
                active: { ...defaults.windows.normal.frame.active, ...(parsed.windows?.normal?.frame?.active || {}) },
                inactive: { ...defaults.windows.normal.frame.inactive, ...(parsed.windows?.normal?.frame?.inactive || {}) }
            },
            cloak: {
                active: { ...defaults.windows.normal.cloak.active, ...(parsed.windows?.normal?.cloak?.active || {}) },
                inactive: { ...defaults.windows.normal.cloak.inactive, ...(parsed.windows?.normal?.cloak?.inactive || {}) }
            },
        },
        back: {
            scene: {
                active: { ...defaults.windows.back.scene.active, ...(parsed.windows?.back?.scene?.active || {}) },
                inactive: { ...defaults.windows.back.scene.inactive, ...(parsed.windows?.back?.scene?.inactive || {}) }
            },
            frame: {
                active: { ...defaults.windows.back.frame.active, ...(parsed.windows?.back?.frame?.active || {}) },
                inactive: { ...defaults.windows.back.frame.inactive, ...(parsed.windows?.back?.frame?.inactive || {}) }
            },
            cloak: {
                active: { ...defaults.windows.back.cloak.active, ...(parsed.windows?.back?.cloak?.active || {}) },
                inactive: { ...defaults.windows.back.cloak.inactive, ...(parsed.windows?.back?.cloak?.inactive || {}) }
            },
        }
    };
    settings.noticeDefaults = {
        ...defaults.noticeDefaults,
        ...(parsed.noticeDefaults || {}),
        visual: { ...defaults.noticeDefaults.visual, ...(parsed.noticeDefaults?.visual || {}) },
        audio: { ...defaults.noticeDefaults.audio, ...(parsed.noticeDefaults?.audio || {}) },
    };
    return settings;
}

// Function to load settings from localStorage, or return defaults
function loadSettings() {
    try {
        if (typeof localStorage !== 'undefined') {
            const saved = localStorage.getItem('sidekickDesktopSettings');
            if (saved) {
                const parsed = JSON.parse(saved);
                // The sky.cloak.enabled state is now managed by a separate store and not persisted.
                // We ensure it's removed from any loaded settings.
                if (parsed.sky && parsed.sky.cloak) {
                    delete parsed.sky.cloak.enabled;
                }
                return mergeWithDefaults(parsed);
            }
        }
    } catch (e) {
        console.error("Could not load settings from localStorage", e);
    }
    // Return defaults if nothing is saved or an error occurs
    return { ...defaultSettings };
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

// Initialize view stores from the main settings store and set up two-way binding.
const initialSettings = get(desktopSettings);

desktopView.set({
    panX: initialSettings.panX || 0,
    panY: initialSettings.panY || 0,
    zoom: initialSettings.zoom || 1.0
});
desktopView.subscribe(value => {
    desktopSettings.update(settings => ({
        ...settings,
        panX: value.panX,
        panY: value.panY,
        zoom: value.zoom
    }));
});

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

// Store to track if a mouse-down-based interaction (drag, pan, select) has been initiated.
// This is used to immediately disable pointer events on other layers to prevent unintended hover/focus effects.
export const desktopInteraction = writable(false);

// Store to track if a box is unfolded/expanded to manage global z-index contexts.
export const activeBoxId = writable(null);

// State for sky cloak. Not persisted in settings. Defaults to true on reload.
export const skyCloakEnabled = writable(true);

// --- Virtual Desktop / Nested Box State ---
export const currentBoxId = writable(0);
export const currentBox = derived(
    [currentBoxId, boxes],
    ([$currentBoxId, $boxes]) => $boxes.find(b => b.id === $currentBoxId) || null
);

// New stores for Notification Center
export const notificationHistory = writable([]);
export const unreadNoticeCount = writable(0);

/**
 * Calculates the correct screen position for a context menu, ensuring it doesn't render off-screen.
 * @param {MouseEvent} event The mouse event that triggered the menu.
 * @param {object} [menuDimensions={width: 150, height: 200}] The estimated dimensions of the menu.
 * @returns {{x: number, y: number}} The top-left coordinates for the menu.
 */
export function calculateContextMenuPosition(event, menuDimensions = { width: 150, height: 200 }) {
    let x = event.clientX;
    let y = event.clientY;

    // Ensure we have window dimensions. This should be safe in a browser context.
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;

    // Adjust if the menu would go off the right edge of the screen
    if (x + menuDimensions.width > screenWidth) {
        x = screenWidth - menuDimensions.width - 5; // subtract 5 for padding
    }

    // Adjust if the menu would go off the bottom edge of the screen
    if (y + menuDimensions.height > screenHeight) {
        y = screenHeight - menuDimensions.height - 5; // subtract 5 for padding
    }

    return { x, y };
}

/**
 * Calculates the correct screen position for a context menu inside a transformed window layer,
 * ensuring it doesn't render off-screen.
 * @param {MouseEvent} event The mouse event that triggered the menu.
 * @param {object} [menuDimensions={width: 150, height: 200}] The estimated dimensions of the menu.
 * @returns {{x: number, y: number}} The top-left coordinates for the menu, relative to the window layer.
 */
export function calculateWindowContextMenuPosition(event, menuDimensions = { width: 150, height: 200 }) {
    const { panX, panY, zoom } = get(windowView);

    // The menu is inside the transformed layer, so its perceived size on screen is scaled by zoom.
    const menuScreenWidth = menuDimensions.width * zoom;
    const menuScreenHeight = menuDimensions.height * zoom;

    let finalViewportX = event.clientX;
    let finalViewportY = event.clientY;

    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;

    // Adjust if the menu would go off the right edge of the screen
    if (finalViewportX + menuScreenWidth > screenWidth) {
        finalViewportX = screenWidth - menuScreenWidth - 5; // subtract 5 for padding
    }

    // Adjust if the menu would go off the bottom edge of the screen
    if (finalViewportY + menuScreenHeight > screenHeight) {
        finalViewportY = screenHeight - menuScreenHeight - 5; // subtract 5 for padding
    }

    // Convert the final, adjusted viewport coordinates into coordinates relative to the transformed layer.
    const layerX = (finalViewportX - panX) / zoom;
    const layerY = (finalViewportY - panY) / zoom;

    return { x: layerX, y: layerY };
}

