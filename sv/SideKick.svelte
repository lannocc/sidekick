<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import Desktop from './Desktop.svelte';
    import Taskbar from './Taskbar.svelte';
    import { windows } from './windows.js';
    import { dashActive, dashLayouts, dashCycleIndex } from './desktopStore.js';
    import { get } from 'svelte/store';

    function handleKeyDown(e) {
        // Check for Meta/Alt + ` or Meta/Alt + ~ (Shift + `)
        if ((e.metaKey || e.altKey) && (e.key === '`' || e.key === '~')) {
            e.preventDefault();

            // e.shiftKey is true for '~', false for '`'
            const forward = !e.shiftKey;
            windows.cycleWindow(forward);
        }

        // Dash layout cycling
        if ((e.metaKey || e.altKey) && e.key === 'Escape') {
            e.preventDefault();

            const layouts = get(dashLayouts);
            const isDashActive = get(dashActive);
            const forward = !e.shiftKey;

            if (layouts.length === 0) {
                dashActive.update(v => !v);
                dashCycleIndex.set(-1);
                return;
            }

            if (!isDashActive) {
                // Dash is closed, open it and set index to first/last
                dashActive.set(true);
                dashCycleIndex.set(forward ? 0 : layouts.length - 1);
            } else {
                // Dash is open, cycle to the next/prev layout
                dashCycleIndex.update(idx => {
                    let newIndex;
                    if (idx === -1) {
                        // Not currently cycling, start from beginning/end
                        newIndex = forward ? 0 : layouts.length - 1;
                    } else {
                        newIndex = idx + (forward ? 1 : -1);
                    }

                    if (forward && newIndex >= layouts.length) {
                        dashActive.set(false);
                        return -1; // Cycled past the end
                    } else if (!forward && newIndex < 0) {
                        dashActive.set(false);
                        return -1; // Cycled past the beginning
                    } else {
                        return newIndex;
                    }
                });
            }
        }
    }

    onMount(() => {
        window.addEventListener('keydown', handleKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', handleKeyDown);
    });
</script>

<style>
    .sk-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        width: 100vw;
    }
</style>

<div class="sk-container" on:contextmenu|preventDefault>
    <Taskbar />
    <Desktop />
</div>