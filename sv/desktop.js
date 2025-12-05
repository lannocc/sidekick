import { writable, get } from 'svelte/store';

export const TASKBAR_HEIGHT = 40; // Height of the taskbar in pixels

// Function to load settings from localStorage, or return defaults
function loadSettings() {
    const defaults = {
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
                bgColor: '#2c3e50',
                bgGradientStart: '#2c3e50',
                bgGradientEnd: '#46627f',
                bgImage: '',
                bgImageDisplayMode: 'cover',
                opacity: 1.0,
                height: 40,
                width: 0,
            },
            cloak: {
                bgType: 'color',
                bgColor: '#000000',
                bgGradientStart: '#000000',
                bgGradientEnd: '#222222',
                bgImage: '',
                bgImageDisplayMode: 'cover',
                opacity: 0.0,
            }
        },
        boxes: {
            bgType: 'color',
            bgColor: '#3b4252',
            bgGradientStart: '#3b4252',
            bgGradientEnd: '#4c566a',
            bgImage: '',
            bgImageDisplayMode: 'cover',
            inactiveOpacity: 0.8,
            activeOpacity: 1.0,
        },
        windows: {
            normal: {
                scene: {
                    active: {
                        bgType: 'color', bgColor: '#2d3436', bgGradientStart: '#2d3436', bgGradientEnd: '#454e50', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0,
                    },
                    inactive: {
                        bgType: 'color', bgColor: '#2d3436', bgGradientStart: '#2d3436', bgGradientEnd: '#454e50', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0,
                    },
                },
                frame: {
                    active: {
                        bgType: 'color', bgColor: '#2c3e50', bgGradientStart: '#2c3e50', bgGradientEnd: '#46627f', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, height: 30, width: 0,
                    },
                    inactive: {
                        bgType: 'color', bgColor: '#2c3e50', bgGradientStart: '#2c3e50', bgGradientEnd: '#46627f', bgImage: '', bgImageDisplayMode: 'cover', opacity: 1.0, height: 30, width: 0,
                    },
                },
                cloak: {
                    active: {
                        bgType: 'color', bgColor: '#000000', bgGradientStart: '#000000', bgGradientEnd: '#222222', bgImage: '', bgImageDisplayMode: 'cover', opacity: 0.8,
                    },
                    inactive: {
                        bgType: 'color', bgColor: '#000000', bgGradientStart: '#000000', bgGradientEnd: '#222222', bgImage: '', bgImageDisplayMode: 'cover', opacity: 0.8,
                    },
                },
            },
            back: {
                bgType: 'color',
                bgColor: '#3b4252',
                bgGradientStart: '#3b4252',
                bgGradientEnd: '#4c566a',
                bgImage: '',
                bgImageDisplayMode: 'cover',
                inactiveOpacity: 0.8,
                activeOpacity: 1.0,
            }
        },
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

                // Migration for old background/taskbar settings into new sky object
                if (parsed.background || parsed.taskbar || parsed.bgType) {
                    if (!parsed.sky) parsed.sky = {};
                    if (!parsed.sky.scene) {
                        if (parsed.background) {
                            parsed.sky.scene = parsed.background;
                        } else if (parsed.bgType) { // Handle very old flat structure
                            parsed.sky.scene = {
                                bgType: parsed.bgType,
                                bgColor: parsed.bgColor,
                                bgGradientStart: parsed.bgGradientStart,
                                bgGradientEnd: parsed.bgGradientEnd,
                                bgImage: parsed.bgImage,
                                bgImageDisplayMode: parsed.bgImageDisplayMode,
                            };
                        }
                    }
                    if (!parsed.sky.frame && parsed.taskbar) {
                        parsed.sky.frame = parsed.taskbar;
                    }
                    delete parsed.background;
                    delete parsed.taskbar;
                    ['bgType', 'bgColor', 'bgGradientStart', 'bgGradientEnd', 'bgImage', 'bgImageDisplayMode'].forEach(k => delete parsed[k]);
                }

                // Migration for windows.normal settings
                if (parsed.windows?.normal?.cover) {
                    if (!parsed.windows.normal.frame) parsed.windows.normal.frame = {};
                    const coverSettings = { ...parsed.windows.normal.cover };
                    parsed.windows.normal.frame.active = { ...coverSettings, opacity: coverSettings.activeOpacity ?? 1.0 };
                    parsed.windows.normal.frame.inactive = { ...coverSettings, opacity: coverSettings.inactiveOpacity ?? 1.0 };
                    delete parsed.windows.normal.frame.active.activeOpacity;
                    delete parsed.windows.normal.frame.active.inactiveOpacity;
                    delete parsed.windows.normal.frame.inactive.activeOpacity;
                    delete parsed.windows.normal.frame.inactive.inactiveOpacity;
                    delete parsed.windows.normal.cover;
                }
                if (parsed.windows?.normal?.scene && !parsed.windows.normal.scene.active) {
                    const oldScene = parsed.windows.normal.scene;
                    parsed.windows.normal.scene = {
                        active: { ...oldScene, opacity: 1.0 },
                        inactive: { ...oldScene, opacity: 1.0 }
                    };
                }


                // Merge with defaults, handling nested objects
                const settings = { ...defaults, ...parsed };
                settings.sky = {
                    scene: { ...defaults.sky.scene, ...(parsed.sky?.scene || {}) },
                    frame: { ...defaults.sky.frame, ...(parsed.sky?.frame || {}) },
                    cloak: { ...defaults.sky.cloak, ...(parsed.sky?.cloak || {}) },
                };
                settings.boxes = { ...defaults.boxes, ...(parsed.boxes || {}) };
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
                    back: { ...defaults.windows.back, ...(parsed.windows?.back || {}) }
                };
                settings.noticeDefaults = {
                    ...defaults.noticeDefaults,
                    ...(parsed.noticeDefaults || {}),
                    visual: { ...defaults.noticeDefaults.visual, ...(parsed.noticeDefaults?.visual || {}) },
                    audio: { ...defaults.noticeDefaults.audio, ...(parsed.noticeDefaults?.audio || {}) },
                };
                return settings;
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

// Store to track if a mouse-down-based interaction (drag, pan, select) has been initiated.
// This is used to immediately disable pointer events on other layers to prevent unintended hover/focus effects.
export const desktopInteraction = writable(false);


// New stores for Notification Center
export const notificationHistory = writable([]);
export const unreadNoticeCount = writable(0);