import { writable, get } from 'svelte/store';
import IoskConsole from './IoskConsole.svelte';
import Calculator from './Calculator.svelte';
import Settings from './Settings.svelte';
import IoskFileExplorer from './IoskFileExplorer.svelte';
import IoskFileViewer from './IoskFileViewer.svelte';
import { desktopSettings, windowSettings } from './desktopStore.js';

let windowIdCounter = 0;

// Map component type strings to actual components for restoring layouts
const componentMap = {
    'IoskConsole': IoskConsole,
    'Calculator': Calculator,
    'Settings': Settings,
    'IoskFileExplorer': IoskFileExplorer,
    'IoskFileViewer': IoskFileViewer
};

function createWindowManager() {
    const { subscribe, update } = writable([]);

    const addWindow = (component, props = {}) => {
        const defaults = {
            title: 'New Window',
            width: 800,
            height: 600,
        };

        const allWindowSettings = get(windowSettings);
        const componentName = Object.keys(componentMap).find(key => componentMap[key] === component) || 'Unknown';
        const savedSettings = allWindowSettings[componentName];
        const useSavedPosition = savedSettings && savedSettings.positioning === 'manual';

        const newWindow = {
            id: ++windowIdCounter,
            component: component,
            componentName: componentName,
            x: useSavedPosition ? savedSettings.x : 50 + (windowIdCounter % 10) * 20,
            y: useSavedPosition ? savedSettings.y : 50 + (windowIdCounter % 10) * 20,
            ...defaults,
            ...props,
            width: useSavedPosition ? savedSettings.width : (props.width ?? defaults.width),
            height: useSavedPosition ? savedSettings.height : (props.height ?? defaults.height),
            zIndex: 100,
            minimized: false,
            maximized: false,
            isActive: true, // New windows are active by default
            prevX: 0, prevY: 0, prevWidth: 0, prevHeight: 0,
            lastFocusedElement: null, // To store the last focused element within the window
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
        const allWindows = get(windows);
        const winToRemove = allWindows.find(w => w.id === id);

        if (winToRemove) {
            // Check for connected IoskConsole before closing
            if (winToRemove.component === IoskConsole && winToRemove.isConsoleConnected) {
                if (!confirm("This console has an active connection. Are you sure you want to close it?")) {
                    return; // Abort closing if user cancels
                }
            }
        }

        update(currentWindows => currentWindows.filter(w => w.id !== id));
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
        update(currentWindows => {
            const windowsToKeep = [];
            for (const win of currentWindows) {
                // For connected consoles, ask for individual confirmation
                if (win.component === IoskConsole && win.isConsoleConnected) {
                    if (confirm(`Console "${win.title}" has an active connection. Close it anyway?`)) {
                        // User confirmed, so we don't add it to the 'keep' list.
                    } else {
                        windowsToKeep.push(win); // User cancelled, so we keep this window.
                    }
                }
                // All other windows are implicitly removed as they are not added to `windowsToKeep`.
                // The initial "Close All?" confirmation covers them.
            }
            return windowsToKeep;
        });
    };

    const minimizeAllWindows = () => {
        update(currentWindows => {
            if (currentWindows.length === 0) return currentWindows;
            return currentWindows.map(w => ({...w, minimized: true, isActive: false }));
        });
    };

    const cycleWindow = (forward) => {
        update(currentWindows => {
            const openWindows = currentWindows
                .filter(w => !w.minimized)
                .sort((a, b) => b.zIndex - a.zIndex);

            if (openWindows.length < 2) {
                return currentWindows;
            }

            // The pool of z-indices used by the open windows
            const openZIndices = openWindows.map(w => w.zIndex).sort((a,b) => a - b);

            let newOrder;
            if (forward) {
                // Forward cycle: Move top window to the bottom of the stack
                // e.g., [C, B, A] -> [B, A, C]
                const top = openWindows.shift();
                openWindows.push(top);
                newOrder = openWindows;
            } else {
                // Backward cycle: Move bottom window to the top of the stack
                // e.g., [C, B, A] -> [A, C, B]
                const bottom = openWindows.pop();
                openWindows.unshift(bottom);
                newOrder = openWindows;
            }

            const newProps = {};
            const activeId = newOrder[0].id;

            // Re-assign the z-indices to the newly ordered windows
            newOrder.forEach((win, index) => {
                newProps[win.id] = {
                    zIndex: openZIndices[openZIndices.length - 1 - index],
                    isActive: win.id === activeId
                };
            });

            // Map over all windows and apply the new properties to the cycled ones
            return currentWindows.map(w => {
                if (newProps[w.id]) {
                    return { ...w, ...newProps[w.id] };
                }
                return w;
            });
        });
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
        closeAllWindows,
        minimizeAllWindows,
        cycleWindow
    };
}

export const windows = createWindowManager();


// Function to be called from other components like the Taskbar
export function newIoskConnection() {
    windows.addWindow(IoskConsole, {
        title: 'New IOSK Connection'
    });
}

export function newCalculator() {
    windows.addWindow(Calculator, { title: 'Calculator', width: 320, height: 450 });
}

export function newSettings() {
    windows.addWindow(Settings, { title: 'Settings', width: 400, height: 550 });
}

export function newIoskFileExplorer(consoleId, consoleTitle) {
    const title = `Files - ${consoleTitle || `Console ${consoleId}`}`;
    
    const allWindowSettings = get(windowSettings);
    const explorerSettings = allWindowSettings['IoskFileExplorer'];
    const initialPath = explorerSettings?.initialPath || '.';

    windows.addWindow(IoskFileExplorer, {
        title: title,
        consoleId: consoleId,
        initialPath: initialPath,
        width: 400,
        height: 500,
    });
}

export function newIoskFileViewer(consoleId, path) {
    const title = path.split('/').pop() || path;
    windows.addWindow(IoskFileViewer, {
        title: `View - ${title}`,
        consoleId: consoleId,
        path: path,
        width: 700,
        height: 500,
    });
}

export function restoreWindow(winData) {
    const component = componentMap[winData.componentType];
    if (!component) {
        console.error(`Unknown component type for restore: ${winData.componentType}`);
        return;
    }

    // Prepare props, excluding componentType which is not a direct prop for the window manager
    const { componentType, ...props } = winData;

    windows.addWindow(component, props);
}
