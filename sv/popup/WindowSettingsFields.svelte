<!-- sv/popup/WindowSettingsFields.svelte -->
<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    // This component encapsulates the form fields for window geometry settings.
    // It is designed to be embedded within a parent component's modal.
    // The parent is responsible for the modal container, buttons, and save logic.
    export let settings; // Bound object, e.g., { positioning, x, y, width, height, defaultZoom }
</script>

<fieldset>
    <legend>Default Window Position & Size</legend>
    <div class="radio-group">
        <label><input type="radio" bind:group={settings.positioning} value="auto"> Auto</label>
        <label><input type="radio" bind:group={settings.positioning} value="manual"> Manual</label>
    </div>
    {#if settings.positioning === 'manual'}
        <div class="form-grid">
            <label>X: <input type="number" bind:value={settings.x}></label>
            <label>Y: <input type="number" bind:value={settings.y}></label>
            <label>Width: <input type="number" bind:value={settings.width}></label>
            <label>Height: <input type="number" bind:value={settings.height}></label>
        </div>
    {/if}
</fieldset>

<fieldset>
    <legend>Appearance</legend>
    <div class="form-grid" style="grid-template-columns: 1fr;">
         <label style="grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center;">
            <span>Default Zoom</span>
            <input type="number" bind:value={settings.defaultZoom} min="0.5" max="3" step="0.1" style="width: 80px;">
        </label>
    </div>
</fieldset>

<style>
    /* Styles are inherited from the parent modal's context */
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; margin-top: 15px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding-left: 20px; }
    .form-grid label { display: flex; align-items: center; gap: 5px; }
    .form-grid input { width: 80px; background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 5px; border-radius: 3px;}
    .radio-group label { display: inline-flex; align-items: center; gap: 5px; margin-right: 15px; }
</style>

