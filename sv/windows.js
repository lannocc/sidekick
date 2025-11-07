import { writable, get } from 'svelte/store';
import IoskConsole from './IoskConsole.svelte';
import Calculator from './Calculator.svelte';
import Settings from './Settings.svelte';
import { desktopSettings } from './desktopStore.js';

let windowIdCounter = 0;

function createWindowManager() {
    const { subscribe, update } = writable([]);

    const addWindow = (component, props = {}) => {
        const defaults = {
            title: 'New Window',
            width: 800,
            height: 600,
        };

        const newWindow = {
            id: ++windowIdCounter,
            component: component,
            x: 50 + (windowIdCounter % 10) * 20,
            y: 50 + (windowIdCounter % 10) * 20,
            ...defaults,
            ...props,
            zIndex: 100,
            minimized: false,
            maximized: false,
            isActive: true, // New windows are active by default
            prevX: 0, prevY: 0, prevWidth: 0, prevHeight: 0,
        };

        update(windows => {
            // Set all other windows to inactive and a lower z-index
            const updatedWindows = windows.map(w => ({ ...w, zIndex: w.zIndex - 10, isActive: false }));
            newWindow.zIndex = updatedWindows.reduce((max, w) => Math.max(max, w.zIndex), 99) + 1;
            return [...updatedWindows, newWindow];
        });
        return newWindow.id;
    };

    const removeWindow = (id) => {
        update(windows => windows.filter(w => w.id !== id));
    };

    const setActiveWindow = (id) => {
        update(windows => {
            // Avoid re-rendering if the window is already active
            const targetWindow = windows.find(w => w.id === id);
            if (targetWindow && targetWindow.isActive) return windows;

            return windows.map(w => ({
                ...w,
                isActive: w.id === id
            }));
        });
    };

    const focusWindow = (id) => {
        update(windows => {
            const currentTopWindow = windows.reduce((top, w) => (!top || w.zIndex > top.zIndex) ? w : top, null);

            // If the target window is already the active top window, do nothing.
            if (currentTopWindow && currentTopWindow.id === id && currentTopWindow.isActive) {
                return windows;
            }

            const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
            return windows.map(w => {
                if (w.id === id) {
                    return { ...w, zIndex: maxZ + 1, isActive: true };
                }
                // Set others to inactive, but preserve their z-index relative to each other.
                return { ...w, isActive: false };
            });
        });
    };

    const updateWindowProps = (id, newProps) => {
        update(windows => windows.map(w => w.id === id ? { ...w, ...newProps } : w));
    };

    const toggleMinimize = (id) => {
        update(windows => {
            const winToToggle = windows.find(w => w.id === id);
            if (!winToToggle) return windows;

            // If the window is currently minimized, we are restoring it.
            if (winToToggle.minimized) {
                const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
                return windows.map(w => {
                    if (w.id === id) {
                        return { ...w, minimized: false, zIndex: maxZ + 1, isActive: true };
                    }
                    return { ...w, isActive: false };
                });
            } else { // Window is being minimized.
                 // Deactivate window when minimizing
                const updated = windows.map(w => (w.id === id ? { ...w, minimized: true, isActive: false } : w));
                // Focus the next highest window if available
                const nextWindow = updated.filter(w => !w.minimized).reduce((top, w) => (!top || w.zIndex > top.zIndex) ? w : top, null);
                if(nextWindow) focusWindow(nextWindow.id);
                return updated;
            }
        });
    };

    const toggleMaximize = (id) => {
        update(windows => {
            const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
            return windows.map(w => {
                if (w.id === id) {
                    const newProps = w.maximized
                        ? { // Restore
                            maximized: false,
                            x: w.prevX, y: w.prevY,
                            width: w.prevWidth, height: w.prevHeight,
                          }
                        : { // Maximize
                            maximized: true,
                            prevX: w.x, prevY: w.y,
                            prevWidth: w.width, prevHeight: w.height,
                            x: 0, y: 0,
                          };
                    return { ...w, ...newProps, zIndex: maxZ + 1, isActive: true };
                }
                return { ...w, isActive: false };
            });
        });
    };

    const closeAllWindows = () => {
        update(() => []);
    };

    return {
        subscribe,
        addWindow,
        removeWindow,
        focusWindow,
        setActiveWindow,
        updateWindowProps,
        toggleMinimize,
        toggleMaximize,
        closeAllWindows
    };
}

export const windows = createWindowManager();

// Function to be called from other components like the Taskbar
export function newIoskConnection() {
    const settings = get(desktopSettings);
    windows.addWindow(IoskConsole, {
        title: 'New IOSK Connection',
        username: settings.defaultIoskUsername || 'root'
    });
}

export function newCalculator() {
    windows.addWindow(Calculator, { title: 'Calculator', width: 320, height: 450 });
}

export function newSettings() {
    windows.addWindow(Settings, { title: 'Settings', width: 400, height: 550 });
}

