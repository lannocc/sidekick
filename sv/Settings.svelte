<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { desktopSettings } from './desktopStore.js';

    let settings;
    const unsubscribe = desktopSettings.subscribe(value => {
        settings = value;
    });

    function handleUpdate() {
        desktopSettings.set(settings);
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
</div>