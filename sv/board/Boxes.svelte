<!-- sv/board/Boxes.svelte -->
<script>
    import { onMount } from 'svelte';
    import { boxes, updateBox, deleteBox } from '../bridge.js';
    import { newBox as createNewBoxEntity } from '../windows.js';

    let selectedBoxId = null;
    let selectedBox = null;
    let nameInput = '';

    // When boxes store updates, if we have a selected id, find the full object.
    $: if ($boxes && selectedBoxId !== null) {
        selectedBox = $boxes.find(b => b.id === selectedBoxId);
        if (selectedBox) {
            nameInput = selectedBox.name;
        } else {
            // The selected box was deleted, select another one (defaulting to main desktop).
            selectedBoxId = $boxes.find(b => b.id === 0) ? 0 : ($boxes.length > 0 ? $boxes[0].id : null);
        }
    }

    // Initialize selection on mount, defaulting to the main desktop (id=0).
    onMount(() => {
        if ($boxes.length > 0 && selectedBoxId === null) {
            selectedBoxId = 0;
        }
    });

    function handleSelectBox(id) {
        selectedBoxId = id;
    }

    function handleNameUpdate() {
        if (selectedBox && nameInput && nameInput.trim() !== selectedBox.name) {
            updateBox(selectedBox.id, nameInput.trim());
        }
    }

    function handleDeleteBox(id, name) {
        if (id === 0) return; // Should be prevented by UI anyway
        if (confirm(`Are you sure you want to delete the box "${name}"? This cannot be undone.`)) {
            deleteBox(id);
        }
    }

    function handleNewBox(event) {
        const name = prompt("Enter a name for the new Box:", "My Project Box");
        if (!name) return;

        const context = prompt("Enter the local filesystem path for the Box:", "/home/user/project");
        if (!context) return;
        
        // This function from windows.js does the geometry calculation and calls the bridge
        createNewBoxEntity({ name, context, sourceEvent: event });
    }
</script>

<style>
    .boxes-container {
        display: flex;
        height: 100%;
        background-color: var(--window-bg);
        color: var(--text-color);
        position: relative;
    }
    .left-panel {
        width: 200px;
        min-width: 150px;
        border-right: 1px solid var(--border-color);
        display: flex;
        flex-direction: column;
        overflow-y: auto;
    }
    .box-list-item {
        display: flex;
        align-items: center;
        padding: 8px;
        cursor: pointer;
        border-bottom: 1px solid var(--border-color-light);
        gap: 8px;
    }
    .box-list-item:hover {
        background-color: var(--item-hover-bg);
    }
    .box-list-item.selected {
        background-color: var(--item-selected-bg);
        font-weight: bold;
    }
    .box-icon {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
    }
    .box-name {
        flex-grow: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .delete-btn {
        background: none;
        border: none;
        color: #e74c3c;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
        padding: 0 4px;
        visibility: hidden; /* Hide by default */
        border-radius: 50%;
    }
    .box-list-item:hover .delete-btn {
        visibility: visible; /* Show on hover */
    }
    .delete-btn:hover {
        color: white;
        background-color: #c0392b;
    }
    .right-panel {
        flex-grow: 1;
        padding: 16px;
        padding-top: 48px; /* Space for the absolute positioned button */
        display: flex;
        flex-direction: column;
        gap: 16px;
        overflow-y: auto;
    }
    .details-group {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .details-group label {
        font-size: 0.9em;
        color: var(--text-color-light);
    }
    .details-group input, .details-group span {
        padding: 8px;
        background-color: var(--input-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        color: var(--text-color);
        font-size: 1em;
    }
    .details-group span {
        font-family: monospace;
        word-break: break-all;
    }
    .new-box-btn {
        position: absolute;
        top: 8px;
        right: 8px;
        padding: 6px 12px;
        background-color: var(--button-bg);
        border: 1px solid var(--button-border-color);
        color: var(--button-text-color);
        border-radius: 4px;
        cursor: pointer;
        z-index: 10;
    }
    .new-box-btn:hover {
        background-color: var(--button-hover-bg);
    }
    .no-selection {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: var(--text-color-light);
        font-style: italic;
    }
</style>

<div class="boxes-container">
    <button class="new-box-btn" on:click={handleNewBox}>New Box</button>
    
    <div class="left-panel">
        {#each $boxes.sort((a, b) => a.id - b.id) as box (box.id)}
            <div 
                class="box-list-item" 
                class:selected={box.id === selectedBoxId}
                on:click={() => handleSelectBox(box.id)}
                title={box.name}
            >
                <img src="/skybox.png" alt="Box" class="box-icon" />
                <span class="box-name">{box.name}</span>
                {#if box.id !== 0}
                    <button class="delete-btn" title="Delete Box" on:click|stopPropagation={() => handleDeleteBox(box.id, box.name)}>
                        ✕
                    </button>
                {/if}
            </div>
        {/each}
    </div>

    <div class="right-panel">
        {#if selectedBox}
            <div class="details-group">
                <label for="box-name-input">Name</label>
                <input id="box-name-input" type="text" bind:value={nameInput} on:blur={handleNameUpdate} />
            </div>
            <div class="details-group">
                <label>ID</label>
                <span>{selectedBox.id}</span>
            </div>
            <div class="details-group">
                <label>Type</label>
                <span>{selectedBox.type}</span>
            </div>
            <div class="details-group">
                <label>Context Path</label>
                <span>{selectedBox.context}</span>
            </div>
        {:else}
            <div class="no-selection">
                Select a box to see its details.
            </div>
        {/if}
    </div>
</div>