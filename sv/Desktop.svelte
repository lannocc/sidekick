<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { windows } from './windows.js';
    import Window from './Window.svelte';
</script>

<style>
    .desktop {
        flex-grow: 1;
        position: relative;
        width: 100%;
        overflow: hidden;
    }
</style>

<div class="desktop">
    {#each $windows as win (win.id)}
        <Window {...win} />
    {/each}
</div>

