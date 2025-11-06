<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import Desktop from './Desktop.svelte';
    import Taskbar from './Taskbar.svelte';
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

