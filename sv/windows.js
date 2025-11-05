import { writable } from 'svelte/store';
import IoskConsole from './IoskConsole.svelte';

let windowIdCounter = 0;

function createWindowManager() {
    const { subscribe, update } = writable([]);

    const addWindow = (component, props = {}) => {
        const newWindow = {
            id: ++windowIdCounter,
            component: component,
            title: props.title || 'New Window',
            x: 50 + (windowIdCounter % 10) * 20,
            y: 50 + (windowIdCounter % 10) * 20,
            width: 800,
            height: 600,
            zIndex: 100, // Initial z-index, will be managed by focusWindow
            minimized: false,
        };

        update(windows => {
            // Set all other windows to a lower z-index
            const focusedWindows = windows.map(w => ({ ...w, zIndex: w.zIndex - 10 }));
            newWindow.zIndex = focusedWindows.reduce((max, w) => Math.max(max, w.zIndex), 99) + 1;
            return [...focusedWindows, newWindow];
        });
        return newWindow.id;
    };

    const removeWindow = (id) => {
        update(windows => windows.filter(w => w.id !== id));
    };

    const focusWindow = (id) => {
        update(windows => {
            const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
            const targetWindow = windows.find(w => w.id === id);

            // Only reshuffle if the target window is not already on top
            if (targetWindow && targetWindow.zIndex <= maxZ) {
                return windows.map(w => {
                    if (w.id === id) {
                        return { ...w, zIndex: maxZ + 1 };
                    }
                    return w;
                });
            }
            return windows;
        });
    };

    const updateWindowProps = (id, newProps) => {
        update(windows => windows.map(w => w.id === id ? { ...w, ...newProps } : w));
    };

    const toggleMinimize = (id) => {
        update(windows => windows.map(w => {
            if (w.id === id) {
                const isMinimized = !w.minimized;
                if (!isMinimized) {
                    // When un-minimizing, bring to front
                    const maxZ = windows.reduce((max, w) => Math.max(max, w.zIndex), 99);
                    return { ...w, minimized: false, zIndex: maxZ + 1};
                }
                return { ...w, minimized: true };
            }
            return w;
        }));
    };

    return {
        subscribe,
        addWindow,
        removeWindow,
        focusWindow,
        updateWindowProps,
        toggleMinimize
    };
}

export const windows = createWindowManager();

// Function to be called from other components like the Taskbar
export function newIoskConnection() {
    windows.addWindow(IoskConsole, { title: 'New IOSK Connection' });
}

