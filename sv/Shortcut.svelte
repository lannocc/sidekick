<!-- sv/Shortcut.svelte -->
<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { newLocalFileExplorer, newLocalFileViewer } from './windows.js';
    import { desktopView, selectedItems, wasDraggingItems } from './desktop.js';
    import { desktopShortcuts, updateShortcutTransform } from './local.js';
    import { get } from 'svelte/store';
    import { onDestroy, afterUpdate, createEventDispatcher } from 'svelte';

    export let id;
    export let name;
    export let type; // 'file' or 'dir'
    export let path;
    export let x;
    export let y;
    export let scale = 1.0;

    const dispatch = createEventDispatcher();
    $: isSelected = $selectedItems.has(`shortcut-${id}`);
    let element;

    $: transform = `translate(${$desktopView.panX}px, ${$desktopView.panY}px) scale(${$desktopView.zoom}) translate(${x}px, ${y}px) scale(${scale || 1.0})`;

    // By using afterUpdate, we ensure the rendered dimensions are always kept up-to-date
    // in our central store. This is more robust than onMount because it accounts for
    // dimension changes that might happen after the initial render, such as a long
    // name wrapping to a new line, or fonts loading.
    afterUpdate(() => {
        if (element) {
            // Get the currently stored data to compare against.
            const currentData = get(desktopShortcuts).find(s => s.id === id);

            // Only update the global store if the dimensions have actually changed.
            // This check is crucial to prevent an infinite loop of updates.
            if (!currentData || currentData.renderWidth !== element.offsetWidth || currentData.renderHeight !== element.offsetHeight) {
                desktopShortcuts.update(shortcuts =>
                    shortcuts.map(s =>
                        s.id === id
                            ? { ...s, renderWidth: element.offsetWidth, renderHeight: element.offsetHeight }
                            : s
                    )
                );
            }
        }
    });

    function handleClick(event) {
        if (get(wasDraggingItems) || event.ctrlKey) {
            return;
        }
        if (type === 'dir') {
            newLocalFileExplorer({ initialPath: path, title: `Files - ${name}` });
        } else if (type === 'file') {
            newLocalFileViewer({ path, title: name });
        }
    }

    function handleWheel(event) {
        if (event.ctrlKey || event.altKey) {
            event.preventDefault();
            const zoomStep = 0.05;
            const delta = event.deltaY < 0 ? zoomStep : -zoomStep;
            const newScale = Math.max(0.2, (scale ?? 1.0) + delta);
            dispatch('scale', { id, newScale });
        }
    }
</script>

<style>
    .shortcut {
        position: absolute;
        width: 80px;
        display: flex;
        flex-direction: column;
        align-items: center;
        cursor: pointer;
        user-select: none;
        padding: 4px;
        border-radius: 4px;
        transition: background-color 0.1s ease-in-out;
        pointer-events: auto;
        border: 1px solid transparent;
        /* Position is now handled by transform, so set top/left to 0 */
        top: 0;
        left: 0;
    }
    .shortcut.selected {
        background-color: rgba(52, 152, 219, 0.3);
        border-color: rgba(52, 152, 219, 0.7);
    }
    .shortcut:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    .shortcut.selected:hover {
        background-color: rgba(52, 152, 219, 0.4);
    }
    .icon {
        font-size: 48px;
        line-height: 1;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.4);
    }
    .name {
        color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
        font-size: 12px;
        text-align: center;
        word-break: break-word;
        margin-top: 4px;
    }
</style>

<div
    bind:this={element}
    class="shortcut"
    class:selected={isSelected}
    data-id={id}
    data-type="shortcut"
    style:transform={transform}
    on:click={handleClick}
    on:wheel={handleWheel}
    on:scale
>
    <div class="icon">{type === 'dir' ? '🗂️' : '📄'}</div>
    <div class="name">{name}</div>
</div>