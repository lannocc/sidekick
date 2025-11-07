import { writable } from 'svelte/store';

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
        ioskUrl: 'ws://localhost:4209', // Add this line
        ioskUsername: 'root',           // Add this line

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

// Store for managing the dashboard's active state
export const dashboardActive = writable(false);
