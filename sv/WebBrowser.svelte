<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { get } from 'svelte/store';
    import { windows } from './windows.js';
    import { windowSettings } from './desktopStore.js';

    export let id; // Window ID
    export let groupId;
    export let initialUrl = "about:blank"; // Passed from Dash restore or new window creation
    export let componentName;
    export let x, y, width, height;

    let currentUrl = initialUrl;
    let inputUrl = initialUrl;
    let iframeEl;
    let history = [initialUrl];
    let historyIndex = 0;
    let isLoading = false;

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsModel = { defaultUrl: '' };
    let windowSettingsForModal = { positioning: 'auto', x: 0, y: 0, width: 0, height: 0 };

    // Update the central window store for Dash saving
    $: if (id !== undefined && groupId !== undefined) {
        // This property `currentUrl` will be saved by Dash as `initialUrl` for restoration.
        windows.updateTabProps(groupId, id, { currentUrl: currentUrl });
    }

    function navigate() {
        let urlToLoad = inputUrl.trim();
        if (!urlToLoad) return;
        
        // Basic protocol check
        if (!/^(https?:\/\/|file:\/\/|about:)/i.test(urlToLoad)) {
            // A simple search query? For now, let's just default to https.
            urlToLoad = 'https://' + urlToLoad;
        }

        if (urlToLoad === currentUrl) {
            reload();
            return;
        }
        
        isLoading = true;
        currentUrl = urlToLoad;
        inputUrl = urlToLoad;

        // Add to history, clearing any "forward" history
        if (historyIndex < history.length - 1) {
            history = history.slice(0, historyIndex + 1);
        }
        history.push(currentUrl);
        historyIndex = history.length - 1;
    }

    function goBack() {
        if (historyIndex > 0) {
            isLoading = true;
            historyIndex--;
            currentUrl = history[historyIndex];
            inputUrl = currentUrl;
        }
    }

    function goForward() {
        if (historyIndex < history.length - 1) {
            isLoading = true;
            historyIndex++;
            currentUrl = history[historyIndex];
            inputUrl = currentUrl;
        }
    }

    function reload() {
        if (iframeEl) {
            isLoading = true;
            iframeEl.src = currentUrl; // Re-assigning src reloads the iframe
        }
    }

    function handleIframeLoad() {
        isLoading = false;
        // Due to same-origin policy, we cannot reliably get the iframe's current location
        // if it navigates internally (e.g., user clicks a link).
        // The address bar will show the last URL we explicitly set. This is a limitation.
    }

    // --- Settings Logic ---
    export function showSettingsDialog() {
        const allSettings = get(windowSettings);
        const currentWindowSettings = allSettings[componentName] || { positioning: 'auto' };

        // Use the saved default URL if it exists, otherwise fall back to the current URL of this instance.
        settingsModel = {
            defaultUrl: currentWindowSettings.defaultUrl || currentUrl
        };

        // Populate window settings for the modal
        windowSettingsForModal = {
            positioning: currentWindowSettings.positioning || 'auto',
            x: currentWindowSettings.x ?? x,
            y: currentWindowSettings.y ?? y,
            width: currentWindowSettings.width ?? width,
            height: currentWindowSettings.height ?? height,
            defaultZoom: currentWindowSettings.defaultZoom ?? 1.0,
        };

        showSettings = true;
    }


    function handleSaveSettings() {
        const componentSettings = {
            defaultUrl: settingsModel.defaultUrl.trim() || "about:blank"
        };
        windowSettings.update(all => {
            // Get existing settings for this component to avoid overwriting unrelated properties.
            const existingSettings = all[componentName] || {};
            return {
                ...all,
                [componentName]: {
                    ...existingSettings,
                    ...windowSettingsForModal,
                    ...componentSettings
                }
            };
        });
        showSettings = false;
    }

    function handleCancelSettings() {
        showSettings = false;
    }

</script>

<style>
    .browser-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        background-color: var(--window-bg);
    }
    .toolbar {
        display: flex;
        gap: 5px;
        padding: 5px;
        background-color: var(--title-bar-bg);
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
        align-items: center;
    }
    .nav-button {
        background: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--taskbar-text);
        border-radius: 3px;
        cursor: pointer;
        width: 30px;
        height: 30px;
        font-family: monospace;
        font-size: 1.2em;
        line-height: 1;
        flex-shrink: 0;
    }
    .nav-button:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .nav-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .address-bar {
        flex-grow: 1;
        background-color: var(--console-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 5px 8px;
        border-radius: 3px;
        font-family: monospace;
        height: 30px;
        box-sizing: border-box;
    }
    .content {
        flex-grow: 1;
        position: relative;
    }
    iframe {
        width: 100%;
        height: 100%;
        border: none;
        background-color: white; /* Show a white background while loading */
    }
    .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
        font-size: 1.2em;
        pointer-events: none;
    }

    /* Styles for settings modal (borrowed from IoskConsole/Explorer) */
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .modal-content label { display: flex; flex-direction: column; gap: 5px; }
    .modal-content input[type="text"] { background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 8px; border-radius: 3px; font-family: monospace; width: 100%; box-sizing: border-box; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding-left: 20px; }
    .form-grid label { display: flex; align-items: center; gap: 5px; flex-direction: row; }
    .form-grid input { width: 80px; }
    .radio-group label { display: inline-flex; align-items: center; gap: 5px; margin-right: 15px; flex-direction: row;}
</style>

<div class="browser-container">
    <div class="toolbar">
        <button class="nav-button" on:click={goBack} disabled={historyIndex === 0} title="Back">←</button>
        <button class="nav-button" on:click={goForward} disabled={historyIndex >= history.length - 1} title="Forward">→</button>
        <button class="nav-button" on:click={reload} title="Reload">↻</button>
        <form on:submit|preventDefault={navigate} style="flex-grow: 1; display: flex;">
            <input class="address-bar" type="text" bind:value={inputUrl} spellcheck="false" placeholder="Enter URL and press Enter">
        </form>
    </div>
    <div class="content">
        <iframe 
            bind:this={iframeEl} 
            src={currentUrl} 
            sandbox="allow-forms allow-modals allow-popups allow-presentation allow-same-origin allow-scripts"
            on:load={handleIframeLoad}
        ></iframe>
        {#if isLoading}
            <div class="loading-overlay">Loading...</div>
        {/if}
    </div>

    <!-- Settings Modal Markup -->
    {#if showSettings}
        <div class="modal-overlay" on:click|self={handleCancelSettings}>
            <div class="modal-content" on:keydown|stopPropagation on:keyup|stopPropagation on:keypress|stopPropagation>
                <h3>Web Browser Settings</h3>
                <fieldset>
                    <legend>Default URL</legend>
                    <label>
                        <span>Initial Page when opening a new browser</span>
                        <input type="text" bind:value={settingsModel.defaultUrl} placeholder="e.g., about:blank">
                    </label>
                </fieldset>

                <fieldset>
                    <legend>Default Window Position & Size</legend>
                    <div class="radio-group">
                        <label><input type="radio" bind:group={windowSettingsForModal.positioning} value="auto"> Auto</label>
                        <label><input type="radio" bind:group={windowSettingsForModal.positioning} value="manual"> Manual</label>
                    </div>
                    {#if windowSettingsForModal.positioning === 'manual'}
                        <div class="form-grid">
                            <label>X: <input type="number" bind:value={windowSettingsForModal.x}></label>
                            <label>Y: <input type="number" bind:value={windowSettingsForModal.y}></label>
                            <label>Width: <input type="number" bind:value={windowSettingsForModal.width}></label>
                            <label>Height: <input type="number" bind:value={windowSettingsForModal.height}></label>
                        </div>
                    {/if}
                </fieldset>

                <fieldset>
                    <legend>Appearance</legend>
                    <div class="form-grid">
                        <label style="grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; flex-direction: row;">
                            <span>Default Zoom</span>
                            <input type="number" bind:value={windowSettingsForModal.defaultZoom} min="0.5" max="3" step="0.1" style="width: 80px;">
                        </label>
                    </div>
                </fieldset>

                <div class="buttons">
                    <button on:click={handleCancelSettings}>Cancel</button>
                    <button class="save-button" on:click={handleSaveSettings}>Save Default</button>
                </div>
            </div>
        </div>
    {/if}
</div>