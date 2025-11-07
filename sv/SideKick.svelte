<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import Desktop from './Desktop.svelte';
    import Taskbar from './Taskbar.svelte';
    import { windows } from './windows.js';

    function handleKeyDown(e) {
        // Check for Meta/Alt + ` or Meta/Alt + ~ (Shift + `)
        if ((e.metaKey || e.altKey) && (e.key === '`' || e.key === '~')) {
            e.preventDefault();

            // e.shiftKey is true for '~', false for '`'
            const forward = !e.shiftKey;
            windows.cycleWindow(forward);
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

<div class="sk-container">
    <Taskbar />
    <Desktop />
</div>
