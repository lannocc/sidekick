<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, tick, createEventDispatcher } from 'svelte';
    import { get } from 'svelte/store';
    import { windowSettings, desktopSettings } from '../desktop.js';

    export let show = false;
    export let componentName;
    export let title;
    // Current geometry to use as defaults for manual positioning
    export let x, y, width, height;

    // Prop to control if the "Activity Notice" section is shown
    export let showNoticeSettings = false;

    let modalSettings = {};
    let firstInput; // Can be bound by parent through the slot

    const dispatch = createEventDispatcher();

    // When the modal is shown, initialize its internal state from the store and props
    $: if (show) {
        const allSettings = get(windowSettings);
        const currentSettings = allSettings[componentName] || {};
        const noticeDefaults = get(desktopSettings).noticeDefaults;

        modalSettings = {
            positioning: currentSettings.positioning || 'auto',
            x: currentSettings.x ?? x,
            y: currentSettings.y ?? y,
            width: currentSettings.width ?? width,
            height: currentSettings.height ?? height,
            defaultZoom: currentSettings.defaultZoom ?? 1.0,
            notice: {
                mode: currentSettings.notice?.mode || 'global',
                color: currentSettings.notice?.color || noticeDefaults.visual.color,
                sound: currentSettings.notice?.sound || noticeDefaults.audio.sound,
            }
        };
        tick().then(() => {
            const focusable = document.querySelector('.modal-content slot > * input, .modal-content slot > * select');
            focusable?.focus();
        });
    }

    function handleSave() {
        // Dispatch event for parent to save its specific settings
        dispatch('save');

        // Save common window settings
        windowSettings.update(all => {
            const existing = all[componentName] || {};
            const { positioning, x, y, width, height, defaultZoom, notice } = modalSettings;

            const newNoticeSettings = showNoticeSettings ? { notice } : {};

            return {
                ...all,
                [componentName]: {
                    ...existing,
                    positioning, x, y, width, height, defaultZoom,
                    ...newNoticeSettings
                }
            };
        });

        show = false; // This will close the modal via bind:show
        dispatch('close');
    }

    function handleCancel() {
        show = false;
        dispatch('close');
    }

    function handleKeydown(e) {
        if (e.key === 'Escape') handleCancel();
        // Allow Enter to save, unless focus is on a button (which has its own click handler)
        else if (e.key === 'Enter' && e.target.tagName !== 'BUTTON') {
             e.preventDefault();
             handleSave();
        }
    }

</script>

<style>
    .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 200; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding-left: 20px; }
    .form-grid label, .radio-group label { display: flex; align-items: center; gap: 5px; }
    .form-grid input { width: 80px; background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 5px; border-radius: 3px; }
    .radio-group { display: flex; gap: 15px; }
    .notice-grid { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 8px 12px; padding-left: 0; }
    .notice-grid > label { grid-column: 1; }
    .notice-grid > input, .notice-grid > select { grid-column: 2; }
    .notice-grid select { padding: 5px; background-color: var(--console-bg); color: var(--title-bar-text); border: 1px solid var(--border-color); }
</style>

{#if show}
<div class="modal-overlay" on:click|self={handleCancel} on:keydown={handleKeydown}>
    <div class="modal-content" on:click|stopPropagation>
        <h3>{title}</h3>

        <slot />

        <fieldset>
            <legend>Default Window Position & Size</legend>
            <div class="radio-group">
                <label><input type="radio" bind:group={modalSettings.positioning} value="auto"> Auto</label>
                <label><input type="radio" bind:group={modalSettings.positioning} value="manual"> Manual</label>
            </div>
            {#if modalSettings.positioning === 'manual'}
                <div class="form-grid">
                    <label>X: <input type="number" bind:value={modalSettings.x}></label>
                    <label>Y: <input type="number" bind:value={modalSettings.y}></label>
                    <label>Width: <input type="number" bind:value={modalSettings.width}></label>
                    <label>Height: <input type="number" bind:value={modalSettings.height}></label>
                </div>
            {/if}
        </fieldset>

        <fieldset>
            <legend>Appearance</legend>
            <div class="form-grid" style="grid-template-columns: 1fr; padding-left: 0;">
                <label style="display: flex; justify-content: space-between; align-items: center;">
                    <span>Default Zoom</span>
                    <input type="number" bind:value={modalSettings.defaultZoom} min="0.5" max="3" step="0.1" style="width: 80px;">
                </label>
            </div>
        </fieldset>

        {#if showNoticeSettings}
        <fieldset>
            <legend>Activity Notice</legend>
            <div class="radio-group">
                <label><input type="radio" bind:group={modalSettings.notice.mode} value="global"> Global Default</label>
                <label><input type="radio" bind:group={modalSettings.notice.mode} value="enabled"> Override</label>
                <label><input type="radio" bind:group={modalSettings.notice.mode} value="disabled"> Disabled</label>
            </div>
            {#if modalSettings.notice.mode === 'enabled'}
                <div class="notice-grid">
                    <label>Flash Color</label>
                    <input type="color" bind:value={modalSettings.notice.color} style="width: 100px; height: 30px;">

                    <label>Notice Sound</label>
                    <select bind:value={modalSettings.notice.sound}>
                        <option value="">System Default</option>
                        <option value="ding.wav">Ding</option>
                        <option value="alert.wav">Alert</option>
                        <option value="none">None</option>
                    </select>
                </div>
            {/if}
        </fieldset>
        {/if}

        <div class="buttons">
            <button on:click={handleCancel}>Cancel</button>
            <button class="save-button" on:click|preventDefault={handleSave}>Save Defaults</button>
        </div>
    </div>
</div>
{/if}