<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { get } from 'svelte/store';
    import { desktopSettings, windowSettings } from './desktop.js';
    import { windows } from './windows.js';
    import WindowSettingsModal from './popup/WindowSettingsModal.svelte';
    import { onDestroy } from 'svelte';

    export let id;
    export let groupId;

    let settings;
    const unsubscribe = desktopSettings.subscribe(value => {
        // Deep copy to avoid mutating the store directly before handleUpdate
        settings = JSON.parse(JSON.stringify(value));
    });

    onDestroy(() => {
        if (unsubscribe) unsubscribe();
    });

    let activeTab = 'general';
    let activeWindowsSubTab = 'normal';
    let activeNormalWindowDetailTab = 'scene';
    let inactiveTransparency, activeTransparency;
    let normalWindowTransparency = {};
    let inactiveBackWindowTransparency, activeBackWindowTransparency;


    $: if (settings && settings.boxes) {
        inactiveTransparency = Math.round((1 - (settings.boxes.inactiveOpacity ?? 0.8)) * 100);
        activeTransparency = Math.round((1 - (settings.boxes.activeOpacity ?? 1.0)) * 100);
    }

    // Ensure the settings object has the required structure for normal windows
    $: if (settings && settings.windows?.normal) {
        const normal = settings.windows.normal;
        for (const part of ['scene', 'frame', 'cover']) {
            if (typeof normal[part] !== 'object' || normal[part] === null) normal[part] = {};
            if (typeof normal[part].active !== 'object' || normal[part].active === null) normal[part].active = {};
            if (typeof normal[part].inactive !== 'object' || normal[part].inactive === null) normal[part].inactive = {};
        }
    }
    
    $: if (settings && settings.windows?.normal) {
        const normal = settings.windows.normal;
        normalWindowTransparency = {
            scene: {
                inactive: Math.round((1 - (normal.scene?.inactive?.opacity ?? 1.0)) * 100),
                active: Math.round((1 - (normal.scene?.active?.opacity ?? 1.0)) * 100),
            },
            frame: {
                inactive: Math.round((1 - (normal.frame?.inactive?.opacity ?? 1.0)) * 100),
                active: Math.round((1 - (normal.frame?.active?.opacity ?? 1.0)) * 100),
            },
            cover: {
                inactive: Math.round((1 - (normal.cover?.inactive?.opacity ?? 1.0)) * 100),
                active: Math.round((1 - (normal.cover?.active?.opacity ?? 1.0)) * 100),
            }
        };
    }

    $: if (settings && settings.windows?.back) {
        inactiveBackWindowTransparency = Math.round((1 - (settings.windows.back.inactiveOpacity ?? 0.8)) * 100);
        activeBackWindowTransparency = Math.round((1 - (settings.windows.back.activeOpacity ?? 1.0)) * 100);
    }

    const chimeSounds = [
        { value: 'beep.wav', name: 'Beep' },
        { value: 'ding.wav', name: 'Ding' },
        { value: 'good_bell.wav', name: 'Good Bell' },
        { value: 'key.wav', name: 'Key' },
        { value: 'short_beep.wav', name: 'Short Beep' },
        { value: 'three_tones.wav', name: 'Three Tones' },
        { value: 'none', name: 'None' },
        { value: 'custom', name: 'Custom URL' }
    ];

    const noticeSounds = [
        { value: 'ding.wav', name: 'Ding' },
        { value: 'beep.wav', name: 'Beep' },
        { value: 'good_bell.wav', name: 'Good Bell' },
        { value: 'key.wav', name: 'Key' },
        { value: 'short_beep.wav', name: 'Short Beep' },
        { value: 'three_tones.wav', name: 'Three Tones' },
        { value: 'none', name: 'None' },
        { value: 'custom', name: 'Custom URL' },
    ];

    function handleUpdate() {
        desktopSettings.set(settings);
    }

    function handleInactiveTransparency(e) {
        const value = Number(e.target.value);
        inactiveTransparency = value;
        settings.boxes.inactiveOpacity = 1 - (value / 100);
        handleUpdate();
    }

    function handleActiveTransparency(e) {
        const value = Number(e.target.value);
        activeTransparency = value;
        settings.boxes.activeOpacity = 1 - (value / 100);
        handleUpdate();
    }
    
    function handleNormalWindowTransparency(e, part, state) {
        const value = Number(e.target.value);
        normalWindowTransparency[part][state] = value;
        settings.windows.normal[part][state].opacity = 1 - (value / 100);
        handleUpdate();
    }

    function handleInactiveBackWindowTransparency(e) {
        const value = Number(e.target.value);
        inactiveBackWindowTransparency = value;
        settings.windows.back.inactiveOpacity = 1 - (value / 100);
        handleUpdate();
    }

    function handleActiveBackWindowTransparency(e) {
        const value = Number(e.target.value);
        activeBackWindowTransparency = value;
        settings.windows.back.activeOpacity = 1 - (value / 100);
        handleUpdate();
    }

    function testChime() {
        if (!settings.chimeType || settings.chimeType === 'none') return;
        let src = settings.chimeType === 'custom' ? settings.chimeUrl : `/assets/${settings.chimeType}`;
        if (src) {
            try {
                new Audio(src).play().catch(e => console.error("Audio play failed:", e));
            } catch (e) { alert("Could not play audio. Check URL or console for errors."); }
        }
     }

    function testNoticeSound() {
        const audioSettings = settings.noticeDefaults.audio;
        if (!audioSettings.sound || audioSettings.sound === 'none') return;
        let src = audioSettings.sound === 'custom' ? audioSettings.url : `/assets/${audioSettings.sound}`;
        if (src) {
            try {
                new Audio(src).play().catch(e => console.error("Audio play failed:", e));
            } catch (e) { alert("Could not play audio. Check URL or console for errors."); }
        }
    }

    // --- Settings Modal Logic ---
    export let componentName;
    export let x, y, width, height;

    let showSettings = false;

    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { isSettingsModalOpen: showSettings });
    }

    export function showSettingsDialog() {
        showSettings = true;
    }
</script>

<style>
    .settings-container {
        padding: 10px;
        display: flex;
        flex-direction: column;
        gap: 20px;
        user-select: none;
    }
    .tabs, .sub-tabs, .detail-tabs {
        display: flex;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 15px;
    }
    .sub-tabs {
        margin-left: 20px;
    }
    .detail-tabs {
        margin-left: 40px;
    }
    .tab-button {
        padding: 8px 16px;
        cursor: pointer;
        background: none;
        border: none;
        color: var(--taskbar-text);
        border-bottom: 2px solid transparent;
        margin-bottom: -1px; /* To overlap with container border */
        font-size: 14px;
    }
    .sub-tab-button {
        padding: 6px 12px;
        cursor: pointer;
        background: none;
        border: none;
        color: var(--taskbar-text);
        border-bottom: 2px solid transparent;
        margin-bottom: -1px;
        font-size: 13px;
        opacity: 0.8;
    }
    .tab-button.active, .sub-tab-button.active {
        border-bottom-color: #3498db;
        color: #3498db;
        opacity: 1;
    }
    h2 {
        margin: 0 0 10px 0;
        color: var(--title-bar-text);
        font-weight: 500;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 5px;
    }
    fieldset {
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    legend {
        color: var(--title-bar-text);
        padding: 0 5px;
    }
    label {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
    }
    .options-group {
        padding-left: 10px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .text-input {
        background-color: var(--console-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 5px;
        border-radius: 3px;
        width: 100%;
        box-sizing: border-box;
    }
    .select-input {
        background-color: var(--console-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 5px;
        border-radius: 3px;
    }
    .color-picker-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }
    input[type="color"] {
        -webkit-appearance: none;
        appearance: none;
        border: none;
        width: 32px;
        height: 32px;
        background: none;
        cursor: pointer;
        padding: 0;
    }
    input[type="color"]::-webkit-color-swatch-wrapper {
        padding: 0;
    }
    input[type="color"]::-webkit-color-swatch {
        border: 1px solid var(--border-color);
        border-radius: 4px;
    }
    .test-button {
        background: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--taskbar-text);
        padding: 5px 10px;
        border-radius: 3px;
        cursor: pointer;
        margin-left: 10px;
    }
    .test-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }

    .two-column-layout {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .column {
        flex: 1;
        min-width: 250px;
        display: flex;
        flex-direction: column;
        gap: 15px;
    }
    .column h3 {
        margin: 0;
        font-weight: 500;
        font-size: 15px;
        color: var(--title-bar-text);
        padding-bottom: 5px;
        border-bottom: 1px solid var(--border-color);
    }


    /* Modal Styles */
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
</style>

<div class="settings-container">
    <div class="tabs">
        <button class="tab-button" class:active={activeTab === 'sky'} on:click={() => activeTab = 'sky'}>Sky</button>
        <button class="tab-button" class:active={activeTab === 'boxes'} on:click={() => activeTab = 'boxes'}>Boxes</button>
        <button class="tab-button" class:active={activeTab === 'windows'} on:click={() => activeTab = 'windows'}>Windows</button>
        <button class="tab-button" class:active={activeTab === 'taskbar'} on:click={() => activeTab = 'taskbar'}>Taskbar</button>
        <button class="tab-button" class:active={activeTab === 'general'} on:click={() => activeTab = 'general'}>General</button>
    </div>

    {#if settings}
        {#if activeTab === 'sky'}
            <h2>Sky Appearance</h2>
            <fieldset>
                <legend>Scene</legend>
                <div>
                    <label><input type="radio" bind:group={settings.background.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                    {#if settings.background.bgType === 'gradient'}
                    <div class="options-group">
                        <label class="color-picker-label">
                            <span>Start Color</span>
                            <input type="color" bind:value={settings.background.bgGradientStart} on:input={handleUpdate}>
                        </label>
                        <label class="color-picker-label">
                            <span>End Color</span>
                            <input type="color" bind:value={settings.background.bgGradientEnd} on:input={handleUpdate}>
                        </label>
                    </div>
                    {/if}
                </div>
                <div>
                     <label><input type="radio" bind:group={settings.background.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                    {#if settings.background.bgType === 'color'}
                    <div class="options-group">
                         <label class="color-picker-label">
                            <span>Color</span>
                            <input type="color" bind:value={settings.background.bgColor} on:input={handleUpdate}>
                        </label>
                    </div>
                    {/if}
                </div>
                 <div>
                    <label><input type="radio" bind:group={settings.background.bgType} value="image" on:change={handleUpdate}> Image</label>
                    {#if settings.background.bgType === 'image'}
                    <div class="options-group">
                        <label>
                            <input class="text-input" type="text" bind:value={settings.background.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                        </label>
                        <label class="color-picker-label">
                            <span>Display Mode</span>
                            <select class="select-input" bind:value={settings.background.bgImageDisplayMode} on:change={handleUpdate}>
                                <option value="cover">Cover</option>
                                <option value="contain">Fit</option>
                                <option value="stretch">Stretch</option>
                                <option value="tile">Tile</option>
                            </select>
                        </label>
                    </div>
                    {/if}
                </div>
            </fieldset>
        {/if}
        {#if activeTab === 'boxes'}
            <h2>Boxes Appearance</h2>
             <fieldset>
                <legend>Scene</legend>
                <div>
                    <label><input type="radio" bind:group={settings.boxes.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                    {#if settings.boxes.bgType === 'gradient'}
                    <div class="options-group">
                        <label class="color-picker-label">
                            <span>Start Color</span>
                            <input type="color" bind:value={settings.boxes.bgGradientStart} on:input={handleUpdate}>
                        </label>
                        <label class="color-picker-label">
                            <span>End Color</span>
                            <input type="color" bind:value={settings.boxes.bgGradientEnd} on:input={handleUpdate}>
                        </label>
                    </div>
                    {/if}
                </div>
                <div>
                     <label><input type="radio" bind:group={settings.boxes.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                    {#if settings.boxes.bgType === 'color'}
                    <div class="options-group">
                         <label class="color-picker-label">
                            <span>Color</span>
                            <input type="color" bind:value={settings.boxes.bgColor} on:input={handleUpdate}>
                        </label>
                    </div>
                    {/if}
                </div>
                 <div>
                    <label><input type="radio" bind:group={settings.boxes.bgType} value="image" on:change={handleUpdate}> Image</label>
                    {#if settings.boxes.bgType === 'image'}
                    <div class="options-group">
                        <label>
                            <input class="text-input" type="text" bind:value={settings.boxes.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                        </label>
                        <label class="color-picker-label">
                            <span>Display Mode</span>
                            <select class="select-input" bind:value={settings.boxes.bgImageDisplayMode} on:change={handleUpdate}>
                                <option value="cover">Cover</option>
                                <option value="contain">Fit</option>
                                <option value="stretch">Stretch</option>
                                <option value="tile">Tile</option>
                            </select>
                        </label>
                    </div>
                    {/if}
                </div>
            </fieldset>
            <fieldset>
                <legend>Transparency</legend>
                <label class="color-picker-label">
                    <span>Inactive ({inactiveTransparency}%)</span>
                    <input type="range" min="0" max="100" step="1" value={inactiveTransparency} on:input={handleInactiveTransparency}>
                </label>
                <label class="color-picker-label">
                    <span>Active ({activeTransparency}%)</span>
                    <input type="range" min="0" max="100" step="1" value={activeTransparency} on:input={handleActiveTransparency}>
                </label>
            </fieldset>
        {/if}
        {#if activeTab === 'windows' && settings.windows}
            <div class="sub-tabs">
                <button class="sub-tab-button" class:active={activeWindowsSubTab === 'back'} on:click={() => activeWindowsSubTab = 'back'}>Back Windows</button>
                <button class="sub-tab-button" class:active={activeWindowsSubTab === 'normal'} on:click={() => activeWindowsSubTab = 'normal'}>Normal Windows</button>
            </div>
            {#if activeWindowsSubTab === 'normal'}
                <div class="detail-tabs">
                    <button class="sub-tab-button" class:active={activeNormalWindowDetailTab === 'scene'} on:click={() => activeNormalWindowDetailTab = 'scene'}>Scene</button>
                    <button class="sub-tab-button" class:active={activeNormalWindowDetailTab === 'frame'} on:click={() => activeNormalWindowDetailTab = 'frame'}>Frame</button>
                    <button class="sub-tab-button" class:active={activeNormalWindowDetailTab === 'cover'} on:click={() => activeNormalWindowDetailTab = 'cover'}>Cover</button>
                </div>

                {#each ['scene', 'frame', 'cover'] as part}
                    {#if activeNormalWindowDetailTab === part}
                        <h2>Normal Windows: {part.charAt(0).toUpperCase() + part.slice(1)} Appearance</h2>
                        <div class="two-column-layout">
                            {#each ['inactive', 'active'] as state}
                                <div class="column">
                                    <h3>{state.charAt(0).toUpperCase() + state.slice(1)} State</h3>
                                    <fieldset>
                                        <legend>Background</legend>
                                        <div>
                                            <label><input type="radio" bind:group={settings.windows.normal[part][state].bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                                            {#if settings.windows.normal[part][state].bgType === 'gradient'}
                                            <div class="options-group">
                                                <label class="color-picker-label"><span>Start Color</span><input type="color" bind:value={settings.windows.normal[part][state].bgGradientStart} on:input={handleUpdate}></label>
                                                <label class="color-picker-label"><span>End Color</span><input type="color" bind:value={settings.windows.normal[part][state].bgGradientEnd} on:input={handleUpdate}></label>
                                            </div>
                                            {/if}
                                        </div>
                                        <div>
                                            <label><input type="radio" bind:group={settings.windows.normal[part][state].bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                                            {#if settings.windows.normal[part][state].bgType === 'color'}
                                            <div class="options-group">
                                                <label class="color-picker-label"><span>Color</span><input type="color" bind:value={settings.windows.normal[part][state].bgColor} on:input={handleUpdate}></label>
                                            </div>
                                            {/if}
                                        </div>
                                        <div>
                                            <label><input type="radio" bind:group={settings.windows.normal[part][state].bgType} value="image" on:change={handleUpdate}> Image</label>
                                            {#if settings.windows.normal[part][state].bgType === 'image'}
                                            <div class="options-group">
                                                <label><input class="text-input" type="text" bind:value={settings.windows.normal[part][state].bgImage} on:input={handleUpdate} placeholder="Enter Image URL..."></label>
                                                <label class="color-picker-label">
                                                    <span>Display Mode</span>
                                                    <select class="select-input" bind:value={settings.windows.normal[part][state].bgImageDisplayMode} on:change={handleUpdate}>
                                                        <option value="cover">Cover</option><option value="contain">Fit</option><option value="stretch">Stretch</option><option value="tile">Tile</option>
                                                    </select>
                                                </label>
                                            </div>
                                            {/if}
                                        </div>
                                    </fieldset>
                                    <fieldset>
                                        <legend>Transparency</legend>
                                        <label class="color-picker-label">
                                            <span>Transparency ({normalWindowTransparency[part]?.[state] ?? 0}%)</span>
                                            <input type="range" min="0" max="100" step="1" value={normalWindowTransparency[part]?.[state] ?? 0} on:input={(e) => handleNormalWindowTransparency(e, part, state)}>
                                        </label>
                                    </fieldset>
                                </div>
                            {/each}
                        </div>
                    {/if}
                {/each}
            {/if}
            {#if activeWindowsSubTab === 'back'}
                <h2>Back Windows Appearance</h2>
                <fieldset>
                    <legend>Scene</legend>
                    <div>
                        <label><input type="radio" bind:group={settings.windows.back.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                        {#if settings.windows.back.bgType === 'gradient'}
                        <div class="options-group">
                            <label class="color-picker-label">
                                <span>Start Color</span>
                                <input type="color" bind:value={settings.windows.back.bgGradientStart} on:input={handleUpdate}>
                            </label>
                            <label class="color-picker-label">
                                <span>End Color</span>
                                <input type="color" bind:value={settings.windows.back.bgGradientEnd} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                    <div>
                        <label><input type="radio" bind:group={settings.windows.back.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                        {#if settings.windows.back.bgType === 'color'}
                        <div class="options-group">
                            <label class="color-picker-label">
                                <span>Color</span>
                                <input type="color" bind:value={settings.windows.back.bgColor} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                    <div>
                        <label><input type="radio" bind:group={settings.windows.back.bgType} value="image" on:change={handleUpdate}> Image</label>
                        {#if settings.windows.back.bgType === 'image'}
                        <div class="options-group">
                            <label>
                                <input class="text-input" type="text" bind:value={settings.windows.back.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                            </label>
                            <label class="color-picker-label">
                                <span>Display Mode</span>
                                <select class="select-input" bind:value={settings.windows.back.bgImageDisplayMode} on:change={handleUpdate}>
                                    <option value="cover">Cover</option>
                                    <option value="contain">Fit</option>
                                    <option value="stretch">Stretch</option>
                                    <option value="tile">Tile</option>
                                </select>
                            </label>
                        </div>
                        {/if}
                    </div>
                </fieldset>
                <fieldset>
                    <legend>Transparency</legend>
                    <label class="color-picker-label">
                        <span>Inactive ({inactiveBackWindowTransparency}%)</span>
                        <input type="range" min="0" max="100" step="1" value={inactiveBackWindowTransparency} on:input={handleInactiveBackWindowTransparency}>
                    </label>
                    <label class="color-picker-label">
                        <span>Active ({activeBackWindowTransparency}%)</span>
                        <input type="range" min="0" max="100" step="1" value={activeBackWindowTransparency} on:input={handleActiveBackWindowTransparency}>
                    </label>
                </fieldset>
            {/if}
        {/if}
        {#if activeTab === 'taskbar'}
            <h2>Taskbar Appearance</h2>
             <fieldset>
                <legend>Scene</legend>
                <div>
                    <label><input type="radio" bind:group={settings.taskbar.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                    {#if settings.taskbar.bgType === 'gradient'}
                    <div class="options-group">
                        <label class="color-picker-label">
                            <span>Start Color</span>
                            <input type="color" bind:value={settings.taskbar.bgGradientStart} on:input={handleUpdate}>
                        </label>
                        <label class="color-picker-label">
                            <span>End Color</span>
                            <input type="color" bind:value={settings.taskbar.bgGradientEnd} on:input={handleUpdate}>
                        </label>
                    </div>
                    {/if}
                </div>
                <div>
                     <label><input type="radio" bind:group={settings.taskbar.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                    {#if settings.taskbar.bgType === 'color'}
                    <div class="options-group">
                         <label class="color-picker-label">
                            <span>Color</span>
                            <input type="color" bind:value={settings.taskbar.bgColor} on:input={handleUpdate}>
                        </label>
                    </div>
                    {/if}
                </div>
                 <div>
                    <label><input type="radio" bind:group={settings.taskbar.bgType} value="image" on:change={handleUpdate}> Image</label>
                    {#if settings.taskbar.bgType === 'image'}
                    <div class="options-group">
                        <label>
                            <input class="text-input" type="text" bind:value={settings.taskbar.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                        </label>
                        <label class="color-picker-label">
                            <span>Display Mode</span>
                            <select class="select-input" bind:value={settings.taskbar.bgImageDisplayMode} on:change={handleUpdate}>
                                <option value="cover">Cover</option>
                                <option value="contain">Fit</option>
                                <option value="stretch">Stretch</option>
                                <option value="tile">Tile</option>
                            </select>
                        </label>
                    </div>
                    {/if}
                </div>
            </fieldset>
        {/if}

        {#if activeTab === 'general'}
            <h2>General Settings</h2>
             <fieldset>
                <legend>Sound Effects</legend>
                <label class="color-picker-label">
                    <span>Chime Sound</span>
                    <div>
                        <select class="select-input" bind:value={settings.chimeType} on:change={handleUpdate}>
                            {#each chimeSounds as sound}
                                <option value={sound.value}>{sound.name}</option>
                            {/each}
                        </select>
                        <button class="test-button" on:click={testChime} title="Test Sound" disabled={settings.chimeType === 'none'}>▶</button>
                    </div>
                </label>
                {#if settings.chimeType === 'custom'}
                    <div class="options-group">
                        <label>
                            <input class="text-input" type="text" bind:value={settings.chimeUrl} on:input={handleUpdate} placeholder="Enter Sound URL...">
                        </label>
                    </div>
                {/if}
            </fieldset>

            <fieldset>
                <legend>Focus</legend>
                <label>
                    <input type="checkbox" bind:checked={settings.focusFollowsMouse} on:change={handleUpdate}>
                    Focus follows mouse
                </label>
                {#if settings.focusFollowsMouse}
                <div class="options-group">
                    <label class="color-picker-label">
                        <span>Focus Delay (ms)</span>
                        <input class="text-input" type="number" bind:value={settings.focusDelay} on:input={handleUpdate} min="0" step="10" style="width: 80px;">
                    </label>
                </div>
                {/if}
            </fieldset>

            <fieldset>
                <legend>Activity Notice Defaults</legend>
                <label>
                    <input type="checkbox" bind:checked={settings.noticeDefaults.enabled} on:change={handleUpdate}>
                    Enable Notices Globally
                </label>
                {#if settings.noticeDefaults.enabled}
                <div class="options-group">
                    <label class="color-picker-label">
                        <span>Flash Color</span>
                        <input type="color" bind:value={settings.noticeDefaults.visual.color} on:input={handleUpdate}>
                    </label>
                    <label class="color-picker-label">
                        <span>Notice Sound</span>
                        <div>
                            <select class="select-input" bind:value={settings.noticeDefaults.audio.sound} on:change={handleUpdate}>
                                {#each noticeSounds as sound}
                                    <option value={sound.value}>{sound.name}</option>
                                {/each}
                            </select>
                            <button class="test-button" on:click={testNoticeSound} title="Test Sound" disabled={settings.noticeDefaults.audio.sound === 'none'}>▶</button>
                        </div>
                    </label>
                    {#if settings.noticeDefaults.audio.sound === 'custom'}
                        <div class="options-group">
                            <label>
                                <input class="text-input" type="text" bind:value={settings.noticeDefaults.audio.url} on:input={handleUpdate} placeholder="Enter Sound URL...">
                            </label>
                        </div>
                    {/if}
                </div>
                {/if}
            </fieldset>
        {/if}
    {/if}
</div>

<WindowSettingsModal
    bind:show={showSettings}
    title="Settings Window"
    {componentName}
    {x} {y} {width} {height}
/>