<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { get } from 'svelte/store';
    import { desktopSettings, windowSettings } from './desktop.js';
    import { windows } from './windows.js';
    import WindowSettingsModal from './popup/WindowSettingsModal.svelte';

    export let id;
    export let groupId;

    let settings;
    const unsubscribe = desktopSettings.subscribe(value => {
        settings = value;
    });

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
    <h2>Desktop Settings</h2>
    <fieldset>
        <legend>Background</legend>
        <div>
            <label><input type="radio" bind:group={settings.bgType} value="gradient" on:change={handleUpdate}> Gradient</label>
            {#if settings.bgType === 'gradient'}
            <div class="options-group">
                <label class="color-picker-label">
                    <span>Start Color</span>
                    <input type="color" bind:value={settings.bgGradientStart} on:input={handleUpdate}>
                </label>
                <label class="color-picker-label">
                    <span>End Color</span>
                    <input type="color" bind:value={settings.bgGradientEnd} on:input={handleUpdate}>
                </label>
            </div>
            {/if}
        </div>
        <div>
             <label><input type="radio" bind:group={settings.bgType} value="color" on:change={handleUpdate}> Solid Color</label>
            {#if settings.bgType === 'color'}
            <div class="options-group">
                 <label class="color-picker-label">
                    <span>Color</span>
                    <input type="color" bind:value={settings.bgColor} on:input={handleUpdate}>
                </label>
            </div>
            {/if}
        </div>
         <div>
            <label><input type="radio" bind:group={settings.bgType} value="image" on:change={handleUpdate}> Image</label>
            {#if settings.bgType === 'image'}
            <div class="options-group">
                <label>
                    <input class="text-input" type="text" bind:value={settings.bgImage} on:input={handleUpdate} placeholder="Enter Image URL...">
                </label>
                <label class="color-picker-label">
                    <span>Display Mode</span>
                    <select class="select-input" bind:value={settings.bgImageDisplayMode} on:change={handleUpdate}>
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
</div>

<WindowSettingsModal
    bind:show={showSettings}
    title="Settings Window"
    {componentName}
    {x} {y} {width} {height}
/>