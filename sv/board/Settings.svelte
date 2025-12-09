<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { get } from 'svelte/store';
    import { desktopSettings, windowSettings } from '../desktop.js';
    import { windows } from '../windows.js';
    import WindowSettingsModal from '../popup/WindowSettingsModal.svelte';
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
    let activeSkySubTab = 'scene';
    let activeWindowDetailTab = 'scene';
    let activeBackBoardDetailTab = 'scene';
    let activeBoxDetailTab = 'scene';
    let normalWindowPresence = {};
    let backWindowPresence = {};
    let boxPresence = {};
    let skyScenePresence, skyFramePresence, skyCloakPresence;


    // Ensure the settings object has the required structure for boxes
    $: if (settings && settings.boxes) {
        const boxes = settings.boxes;
        for (const part of ['scene', 'frame', 'cloak']) {
            if (typeof boxes[part] !== 'object' || boxes[part] === null) boxes[part] = {};
            if (typeof boxes[part].active !== 'object' || boxes[part].active === null) boxes[part].active = {};
            if (typeof boxes[part].inactive !== 'object' || boxes[part].inactive === null) boxes[part].inactive = {};
        }
    }

    $: if (settings && settings.boxes) {
        const boxes = settings.boxes;
        boxPresence = {
            scene: {
                inactive: Math.round((boxes.scene?.inactive?.opacity ?? 0.8) * 100),
                active: Math.round((boxes.scene?.active?.opacity ?? 1.0) * 100),
            },
            frame: {
                inactive: Math.round((boxes.frame?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((boxes.frame?.active?.opacity ?? 1.0) * 100),
            },
            cloak: {
                inactive: Math.round((boxes.cloak?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((boxes.cloak?.active?.opacity ?? 1.0) * 100),
            }
        };
    }

    // Ensure the settings object has the required structure for sky
    $: if (settings && settings.sky) {
        const sky = settings.sky;
        for (const part of ['scene', 'frame', 'cloak']) {
            if (typeof sky[part] !== 'object' || sky[part] === null) sky[part] = {};
        }
        skyScenePresence = Math.round((settings.sky.scene.opacity ?? 1.0) * 100);
        skyFramePresence = Math.round((settings.sky.frame.opacity ?? 1.0) * 100);
        skyCloakPresence = Math.round((settings.sky.cloak.opacity ?? 0.0) * 100);
    }

    // Ensure the settings object has the required structure for normal windows
    $: if (settings && settings.windows?.normal) {
        const normal = settings.windows.normal;
        for (const part of ['scene', 'frame', 'cloak']) {
            if (typeof normal[part] !== 'object' || normal[part] === null) normal[part] = {};
            if (typeof normal[part].active !== 'object' || normal[part].active === null) normal[part].active = {};
            if (typeof normal[part].inactive !== 'object' || normal[part].inactive === null) normal[part].inactive = {};
        }
    }

    $: if (settings && settings.windows?.normal) {
        const normal = settings.windows.normal;
        normalWindowPresence = {
            scene: {
                inactive: Math.round((normal.scene?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((normal.scene?.active?.opacity ?? 1.0) * 100),
            },
            frame: {
                inactive: Math.round((normal.frame?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((normal.frame?.active?.opacity ?? 1.0) * 100),
            },
            cloak: {
                inactive: Math.round((normal.cloak?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((normal.cloak?.active?.opacity ?? 1.0) * 100),
            }
        };
    }

    // Ensure the settings object has the required structure for back windows
    $: if (settings && settings.windows?.back) {
        const back = settings.windows.back;
        for (const part of ['scene', 'frame', 'cloak']) {
            if (typeof back[part] !== 'object' || back[part] === null) back[part] = {};
            if (typeof back[part].active !== 'object' || back[part].active === null) back[part].active = {};
            if (typeof back[part].inactive !== 'object' || back[part].inactive === null) back[part].inactive = {};
        }
    }

    $: if (settings && settings.windows?.back) {
        const back = settings.windows.back;
        backWindowPresence = {
            scene: {
                inactive: Math.round((back.scene?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((back.scene?.active?.opacity ?? 1.0) * 100),
            },
            frame: {
                inactive: Math.round((back.frame?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((back.frame?.active?.opacity ?? 1.0) * 100),
            },
            cloak: {
                inactive: Math.round((back.cloak?.inactive?.opacity ?? 1.0) * 100),
                active: Math.round((back.cloak?.active?.opacity ?? 1.0) * 100),
            }
        };
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

    function handleBoxPresence(e, part, state) {
        const value = Number(e.target.value);
        boxPresence[part][state] = value;
        settings.boxes[part][state].opacity = value / 100;
        handleUpdate();
    }

    function handleSkyScenePresence(e) {
        const value = Number(e.target.value);
        skyScenePresence = value;
        settings.sky.scene.opacity = value / 100;
        handleUpdate();
    }

    function handleSkyFramePresence(e) {
        const value = Number(e.target.value);
        skyFramePresence = value;
        settings.sky.frame.opacity = value / 100;
        handleUpdate();
    }

    function handleSkyCloakPresence(e) {
        const value = Number(e.target.value);
        skyCloakPresence = value;
        settings.sky.cloak.opacity = value / 100;
        handleUpdate();
    }

    function handleNormalWindowPresence(e, part, state) {
        const value = Number(e.target.value);
        normalWindowPresence[part][state] = value;
        settings.windows.normal[part][state].opacity = value / 100;
        handleUpdate();
    }

    function handleBackWindowPresence(e, part, state) {
        const value = Number(e.target.value);
        backWindowPresence[part][state] = value;
        settings.windows.back[part][state].opacity = value / 100;
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
    .borderless-fieldset {
        border: none;
        padding: 0;
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
        <button class="tab-button" class:active={activeTab === 'boxes'} on:click={() => activeTab = 'boxes'}>Box</button>
        <button class="tab-button" class:active={activeTab === 'backBoard'} on:click={() => activeTab = 'backBoard'}>Back Board</button>
        <button class="tab-button" class:active={activeTab === 'window'} on:click={() => activeTab = 'window'}>Window</button>
        <button class="tab-button" class:active={activeTab === 'general'} on:click={() => activeTab = 'general'}>General</button>
    </div>

    {#if settings}
        {#if activeTab === 'sky' && settings.sky}
            <div class="sub-tabs">
                <button class="sub-tab-button" class:active={activeSkySubTab === 'scene'} on:click={() => activeSkySubTab = 'scene'}>Scene</button>
                <button class="sub-tab-button" class:active={activeSkySubTab === 'frame'} on:click={() => activeSkySubTab = 'frame'}>Frame</button>
                <button class="sub-tab-button" class:active={activeSkySubTab === 'cloak'} on:click={() => activeSkySubTab = 'cloak'}>Cloak</button>
            </div>

            {#if activeSkySubTab === 'scene'}
                <h2>Sky Scene Appearance</h2>
                <label class="color-picker-label">
                    <span>Presence ({skyScenePresence}%)</span>
                    <input type="range" min="0" max="100" step="1" value={skyScenePresence} on:input={handleSkyScenePresence}>
                </label>
                <fieldset class="borderless-fieldset" disabled={skyScenePresence === 0}>
                    <div>
                        <label><input type="radio" bind:group={settings.sky.scene.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                        {#if settings.sky.scene.bgType === 'gradient'}
                        <div class="options-group">
                            <label class="color-picker-label">
                                <span>Start Color</span>
                                <input type="color" bind:value={settings.sky.scene.bgGradientStart} on:input={handleUpdate}>
                            </label>
                            <label class="color-picker-label">
                                <span>End Color</span>
                                <input type="color" bind:value={settings.sky.scene.bgGradientEnd} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                    <div>
                         <label><input type="radio" bind:group={settings.sky.scene.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                        {#if settings.sky.scene.bgType === 'color'}
                        <div class="options-group">
                             <label class="color-picker-label">
                                <span>Color</span>
                                <input type="color" bind:value={settings.sky.scene.bgColor} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                     <div>
                        <label><input type="radio" bind:group={settings.sky.scene.bgType} value="image" on:change={handleUpdate}> Image</label>
                        {#if settings.sky.scene.bgType === 'image'}
                        <div class="options-group">
                            <label>
                                <input class="text-input" type="text" bind:value={settings.sky.scene.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                            </label>
                            <label class="color-picker-label">
                                <span>Display Mode</span>
                                <select class="select-input" bind:value={settings.sky.scene.bgImageDisplayMode} on:change={handleUpdate}>
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
            {#if activeSkySubTab === 'frame'}
                <h2>Sky Frame Appearance</h2>
                <label class="color-picker-label">
                    <span>Presence ({skyFramePresence}%)</span>
                    <input type="range" min="0" max="100" step="1" value={skyFramePresence} on:input={handleSkyFramePresence}>
                </label>
                <label class="color-picker-label">
                    <span>Height (px)</span>
                    <input class="text-input" type="number" bind:value={settings.sky.frame.height} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                </label>
                <label class="color-picker-label">
                    <span>Width (px)</span>
                    <input class="text-input" type="number" bind:value={settings.sky.frame.width} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                </label>
                 <fieldset class="borderless-fieldset" disabled={skyFramePresence === 0}>
                    <div>
                        <label><input type="radio" bind:group={settings.sky.frame.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                        {#if settings.sky.frame.bgType === 'gradient'}
                        <div class="options-group">
                            <label class="color-picker-label">
                                <span>Start Color</span>
                                <input type="color" bind:value={settings.sky.frame.bgGradientStart} on:input={handleUpdate}>
                            </label>
                            <label class="color-picker-label">
                                <span>End Color</span>
                                <input type="color" bind:value={settings.sky.frame.bgGradientEnd} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                    <div>
                         <label><input type="radio" bind:group={settings.sky.frame.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                        {#if settings.sky.frame.bgType === 'color'}
                        <div class="options-group">
                             <label class="color-picker-label">
                                <span>Color</span>
                                <input type="color" bind:value={settings.sky.frame.bgColor} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                     <div>
                        <label><input type="radio" bind:group={settings.sky.frame.bgType} value="image" on:change={handleUpdate}> Image</label>
                        {#if settings.sky.frame.bgType === 'image'}
                        <div class="options-group">
                            <label>
                                <input class="text-input" type="text" bind:value={settings.sky.frame.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                            </label>
                            <label class="color-picker-label">
                                <span>Display Mode</span>
                                <select class="select-input" bind:value={settings.sky.frame.bgImageDisplayMode} on:change={handleUpdate}>
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
            {#if activeSkySubTab === 'cloak'}
                <h2>Sky Cloak Appearance</h2>
                <label class="color-picker-label">
                    <span>Presence ({skyCloakPresence}%)</span>
                    <input type="range" min="0" max="100" step="1" value={skyCloakPresence} on:input={handleSkyCloakPresence}>
                </label>
                 <fieldset class="borderless-fieldset" disabled={skyCloakPresence === 0}>
                    <div>
                        <label><input type="radio" bind:group={settings.sky.cloak.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                        {#if settings.sky.cloak.bgType === 'gradient'}
                        <div class="options-group">
                            <label class="color-picker-label">
                                <span>Start Color</span>
                                <input type="color" bind:value={settings.sky.cloak.bgGradientStart} on:input={handleUpdate}>
                            </label>
                            <label class="color-picker-label">
                                <span>End Color</span>
                                <input type="color" bind:value={settings.sky.cloak.bgGradientEnd} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                    <div>
                         <label><input type="radio" bind:group={settings.sky.cloak.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                        {#if settings.sky.cloak.bgType === 'color'}
                        <div class="options-group">
                             <label class="color-picker-label">
                                <span>Color</span>
                                <input type="color" bind:value={settings.sky.cloak.bgColor} on:input={handleUpdate}>
                            </label>
                        </div>
                        {/if}
                    </div>
                     <div>
                        <label><input type="radio" bind:group={settings.sky.cloak.bgType} value="image" on:change={handleUpdate}> Image</label>
                        {#if settings.sky.cloak.bgType === 'image'}
                        <div class="options-group">
                            <label>
                                <input class="text-input" type="text" bind:value={settings.sky.cloak.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                            </label>
                            <label class="color-picker-label">
                                <span>Display Mode</span>
                                <select class="select-input" bind:value={settings.sky.cloak.bgImageDisplayMode} on:change={handleUpdate}>
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
        {/if}
        {#if activeTab === 'boxes' && settings.boxes}
            <div class="sub-tabs">
                <button class="sub-tab-button" class:active={activeBoxDetailTab === 'scene'} on:click={() => activeBoxDetailTab = 'scene'}>Scene</button>
                <button class="sub-tab-button" class:active={activeBoxDetailTab === 'frame'} on:click={() => activeBoxDetailTab = 'frame'}>Frame</button>
                <button class="sub-tab-button" class:active={activeBoxDetailTab === 'cloak'} on:click={() => activeBoxDetailTab = 'cloak'}>Cloak</button>
            </div>

            {#each ['scene', 'frame', 'cloak'] as part}
                {#if activeBoxDetailTab === part}
                    <h2>Box: {part.charAt(0).toUpperCase() + part.slice(1)} Appearance</h2>
                    <div class="two-column-layout">
                        {#each ['inactive', 'active'] as state}
                            <div class="column">
                                <h3>{state.charAt(0).toUpperCase() + state.slice(1)} State</h3>

                                <label class="color-picker-label">
                                    <span>Presence ({boxPresence[part]?.[state] ?? 100}%)</span>
                                    <input type="range" min="0" max="100" step="1" value={boxPresence[part]?.[state] ?? 100} on:input={(e) => handleBoxPresence(e, part, state)}>
                                </label>

                                {#if part === 'frame'}
                                    <label class="color-picker-label">
                                        <span>Width (px)</span>
                                        <input class="text-input" type="number" bind:value={settings.boxes[part][state].width} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                    </label>
                                {/if}

                                <fieldset class="borderless-fieldset" disabled={boxPresence[part]?.[state] === 0}>
                                    <div>
                                        <label><input type="radio" bind:group={settings.boxes[part][state].bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                                        {#if settings.boxes[part][state].bgType === 'gradient'}
                                        <div class="options-group">
                                            <label class="color-picker-label"><span>Start Color</span><input type="color" bind:value={settings.boxes[part][state].bgGradientStart} on:input={handleUpdate}></label>
                                            <label class="color-picker-label"><span>End Color</span><input type="color" bind:value={settings.boxes[part][state].bgGradientEnd} on:input={handleUpdate}></label>
                                        </div>
                                        {/if}
                                    </div>
                                    <div>
                                        <label><input type="radio" bind:group={settings.boxes[part][state].bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                                        {#if settings.boxes[part][state].bgType === 'color'}
                                        <div class="options-group">
                                            <label class="color-picker-label"><span>Color</span><input type="color" bind:value={settings.boxes[part][state].bgColor} on:input={handleUpdate}></label>
                                        </div>
                                        {/if}
                                    </div>
                                    <div>
                                        <label><input type="radio" bind:group={settings.boxes[part][state].bgType} value="image" on:change={handleUpdate}> Image</label>
                                        {#if settings.boxes[part][state].bgType === 'image'}
                                        <div class="options-group">
                                            <label><input class="text-input" type="text" bind:value={settings.boxes[part][state].bgImage} on:input={handleUpdate} placeholder="Enter Image URL..."></label>
                                            <label class="color-picker-label">
                                                <span>Display Mode</span>
                                                <select class="select-input" bind:value={settings.boxes[part][state].bgImageDisplayMode} on:change={handleUpdate}>
                                                    <option value="cover">Cover</option><option value="contain">Fit</option><option value="stretch">Stretch</option><option value="tile">Tile</option>
                                                </select>
                                            </label>
                                        </div>
                                        {/if}
                                    </div>
                                </fieldset>
                                
                                {#if part === 'frame'}
                                    <fieldset>
                                        <legend>Shadow / Glow</legend>
                                        <label>
                                            <input type="checkbox" bind:checked={settings.boxes.frame[state].shadowEnabled} on:change={handleUpdate}>
                                            Enable Shadow
                                        </label>
                                        <fieldset class="borderless-fieldset" disabled={!settings.boxes.frame[state].shadowEnabled}>
                                            <label class="color-picker-label">
                                                <span>Color</span>
                                                <input type="color" bind:value={settings.boxes.frame[state].shadowColor} on:input={handleUpdate}>
                                            </label>
                                            <label class="color-picker-label">
                                                <span>X Offset (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.boxes.frame[state].shadowX} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Y Offset (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.boxes.frame[state].shadowY} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Blur (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.boxes.frame[state].shadowBlur} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Spread (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.boxes.frame[state].shadowSpread} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label>
                                                <input type="checkbox" bind:checked={settings.boxes.frame[state].shadowInset} on:change={handleUpdate}>
                                                Inset Shadow
                                            </label>
                                        </fieldset>
                                    </fieldset>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
            {/each}
        {/if}
        {#if activeTab === 'backBoard' && settings.windows}
            <div class="sub-tabs">
                <button class="sub-tab-button" class:active={activeBackBoardDetailTab === 'scene'} on:click={() => activeBackBoardDetailTab = 'scene'}>Scene</button>
                <button class="sub-tab-button" class:active={activeBackBoardDetailTab === 'frame'} on:click={() => activeBackBoardDetailTab = 'frame'}>Frame</button>
                <button class="sub-tab-button" class:active={activeBackBoardDetailTab === 'cloak'} on:click={() => activeBackBoardDetailTab = 'cloak'}>Cloak</button>
            </div>

            {#each ['scene', 'frame', 'cloak'] as part}
                {#if activeBackBoardDetailTab === part}
                    <h2>Back Board: {part.charAt(0).toUpperCase() + part.slice(1)} Appearance</h2>
                    <div class="two-column-layout">
                        {#each ['inactive', 'active'] as state}
                            <div class="column">
                                <h3>{state.charAt(0).toUpperCase() + state.slice(1)} State</h3>

                                <label class="color-picker-label">
                                    <span>Presence ({backWindowPresence[part]?.[state] ?? 100}%)</span>
                                    <input type="range" min="0" max="100" step="1" value={backWindowPresence[part]?.[state] ?? 100} on:input={(e) => handleBackWindowPresence(e, part, state)}>
                                </label>

                                {#if part === 'frame'}
                                    <label class="color-picker-label">
                                        <span>Height (px)</span>
                                        <input class="text-input" type="number" bind:value={settings.windows.back[part][state].height} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                    </label>
                                    <label class="color-picker-label">
                                        <span>Width (px)</span>
                                        <input class="text-input" type="number" bind:value={settings.windows.back[part][state].width} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                    </label>
                                {/if}

                                <fieldset class="borderless-fieldset" disabled={backWindowPresence[part]?.[state] === 0}>
                                    <div>
                                        <label><input type="radio" bind:group={settings.windows.back[part][state].bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
                                        {#if settings.windows.back[part][state].bgType === 'gradient'}
                                        <div class="options-group">
                                            <label class="color-picker-label"><span>Start Color</span><input type="color" bind:value={settings.windows.back[part][state].bgGradientStart} on:input={handleUpdate}></label>
                                            <label class="color-picker-label"><span>End Color</span><input type="color" bind:value={settings.windows.back[part][state].bgGradientEnd} on:input={handleUpdate}></label>
                                        </div>
                                        {/if}
                                    </div>
                                    <div>
                                        <label><input type="radio" bind:group={settings.windows.back[part][state].bgType} value="color" on:change={handleUpdate}> Solid Color</label>
                                        {#if settings.windows.back[part][state].bgType === 'color'}
                                        <div class="options-group">
                                            <label class="color-picker-label"><span>Color</span><input type="color" bind:value={settings.windows.back[part][state].bgColor} on:input={handleUpdate}></label>
                                        </div>
                                        {/if}
                                    </div>
                                    <div>
                                        <label><input type="radio" bind:group={settings.windows.back[part][state].bgType} value="image" on:change={handleUpdate}> Image</label>
                                        {#if settings.windows.back[part][state].bgType === 'image'}
                                        <div class="options-group">
                                            <label><input class="text-input" type="text" bind:value={settings.windows.back[part][state].bgImage} on:input={handleUpdate} placeholder="Enter Image URL..."></label>
                                            <label class="color-picker-label">
                                                <span>Display Mode</span>
                                                <select class="select-input" bind:value={settings.windows.back[part][state].bgImageDisplayMode} on:change={handleUpdate}>
                                                    <option value="cover">Cover</option><option value="contain">Fit</option><option value="stretch">Stretch</option><option value="tile">Tile</option>
                                                </select>
                                            </label>
                                        </div>
                                        {/if}
                                    </div>
                                </fieldset>
                                
                                {#if part === 'frame'}
                                    <fieldset>
                                        <legend>Shadow / Glow</legend>
                                        <label>
                                            <input type="checkbox" bind:checked={settings.windows.back.frame[state].shadowEnabled} on:change={handleUpdate}>
                                            Enable Shadow
                                        </label>
                                        <fieldset class="borderless-fieldset" disabled={!settings.windows.back.frame[state].shadowEnabled}>
                                            <label class="color-picker-label">
                                                <span>Color</span>
                                                <input type="color" bind:value={settings.windows.back.frame[state].shadowColor} on:input={handleUpdate}>
                                            </label>
                                            <label class="color-picker-label">
                                                <span>X Offset (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.back.frame[state].shadowX} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Y Offset (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.back.frame[state].shadowY} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Blur (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.back.frame[state].shadowBlur} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Spread (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.back.frame[state].shadowSpread} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label>
                                                <input type="checkbox" bind:checked={settings.windows.back.frame[state].shadowInset} on:change={handleUpdate}>
                                                Inset Shadow
                                            </label>
                                        </fieldset>
                                    </fieldset>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
            {/each}
        {/if}
        {#if activeTab === 'window' && settings.windows}
            <div class="sub-tabs">
                <button class="sub-tab-button" class:active={activeWindowDetailTab === 'scene'} on:click={() => activeWindowDetailTab = 'scene'}>Scene</button>
                <button class="sub-tab-button" class:active={activeWindowDetailTab === 'frame'} on:click={() => activeWindowDetailTab = 'frame'}>Frame</button>
                <button class="sub-tab-button" class:active={activeWindowDetailTab === 'cloak'} on:click={() => activeWindowDetailTab = 'cloak'}>Cloak</button>
            </div>

            {#each ['scene', 'frame', 'cloak'] as part}
                {#if activeWindowDetailTab === part}
                    <h2>Window: {part.charAt(0).toUpperCase() + part.slice(1)} Appearance</h2>
                    <div class="two-column-layout">
                        {#each ['inactive', 'active'] as state}
                            <div class="column">
                                <h3>{state.charAt(0).toUpperCase() + state.slice(1)} State</h3>

                                <label class="color-picker-label">
                                    <span>Presence ({normalWindowPresence[part]?.[state] ?? 100}%)</span>
                                    <input type="range" min="0" max="100" step="1" value={normalWindowPresence[part]?.[state] ?? 100} on:input={(e) => handleNormalWindowPresence(e, part, state)}>
                                </label>

                                {#if part === 'frame'}
                                    <label class="color-picker-label">
                                        <span>Height (px)</span>
                                        <input class="text-input" type="number" bind:value={settings.windows.normal[part][state].height} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                    </label>
                                    <label class="color-picker-label">
                                        <span>Width (px)</span>
                                        <input class="text-input" type="number" bind:value={settings.windows.normal[part][state].width} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                    </label>
                                {/if}

                                <fieldset class="borderless-fieldset" disabled={normalWindowPresence[part]?.[state] === 0}>
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
                                
                                {#if part === 'frame'}
                                    <fieldset>
                                        <legend>Shadow / Glow</legend>
                                        <label>
                                            <input type="checkbox" bind:checked={settings.windows.normal.frame[state].shadowEnabled} on:change={handleUpdate}>
                                            Enable Shadow
                                        </label>
                                        <fieldset class="borderless-fieldset" disabled={!settings.windows.normal.frame[state].shadowEnabled}>
                                            <label class="color-picker-label">
                                                <span>Color</span>
                                                <input type="color" bind:value={settings.windows.normal.frame[state].shadowColor} on:input={handleUpdate}>
                                            </label>
                                            <label class="color-picker-label">
                                                <span>X Offset (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.normal.frame[state].shadowX} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Y Offset (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.normal.frame[state].shadowY} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Blur (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.normal.frame[state].shadowBlur} on:input={handleUpdate} min="0" step="1" style="width: 80px;">
                                            </label>
                                            <label class="color-picker-label">
                                                <span>Spread (px)</span>
                                                <input class="text-input" type="number" bind:value={settings.windows.normal.frame[state].shadowSpread} on:input={handleUpdate} step="1" style="width: 80px;">
                                            </label>
                                            <label>
                                                <input type="checkbox" bind:checked={settings.windows.normal.frame[state].shadowInset} on:change={handleUpdate}>
                                                Inset Shadow
                                            </label>
                                        </fieldset>
                                    </fieldset>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
            {/each}
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
                            <input class="text-input"ype="text" bind:value={settings.chimeUrl} on:input={handleUpdate} placeholder="Enter Sound URL...">
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
