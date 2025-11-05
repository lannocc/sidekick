import { writable } from 'svelte/store';

// Function to load settings from localStorage, or return defaults
function loadSettings() {
    try {
        if (typeof localStorage !== 'undefined') {
            const saved = localStorage.getItem('sidekickDesktopSettings');
            if (saved) {
                return JSON.parse(saved);
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
        bgImage: ''
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

