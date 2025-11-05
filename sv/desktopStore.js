import { writable } from 'svelte/store';

// Function to load settings from localStorage, or return defaults
function loadSettings() {
    try {
        if (typeof localStorage !== 'undefined') {
            const saved = localStorage.getItem('sidekickDesktopSettings');
            if (saved) {
                const parsed = JSON.parse(saved);
                // Ensure new settings have default values if not present in localStorage
                return {
                    focusFollowsMouse: false,
                    focusDelay: 420,
                    ...parsed
                };
            }
        }
    } catch (e) {
        console.error("Could not load settings from localStorage", e);
    }
    // Default settings
    return {
        bgType: 'gradient', // 'gradient', 'color', 'image'
        bgColor: '#34495e',
        bgGradientStart: '#2c3e50',
        bgGradientEnd: '#46627f',
        bgImage: '',
        focusFollowsMouse: false,
        focusDelay: 420
    };
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

