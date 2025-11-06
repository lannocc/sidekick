<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    // This is a simple presentation component for the dashboard view.
</script>

<style>
    .dashboard-dialog {
        position: absolute;
        /* Center it in the parent (Desktop component) */
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);

        /* "Maximized with a gap" appearance */
        width: calc(100% - 80px); /* 40px gap on each side */
        height: calc(100% - 80px); /* 40px gap on each side */

        /* Styling similar to a window */
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);

        display: flex;
        flex-direction: column;
        padding: 20px;
        color: var(--title-bar-text);
        z-index: 1000; /* High z-index to be on top of the overlay */
        user-select: none;
        box-sizing: border-box;
    }

    h1 {
        margin: 0 0 20px 0;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 10px;
        font-weight: 400;
    }
</style>

<div class="dashboard-dialog">
    <h1>Dashboard</h1>
    <p>This is the main dashboard view. Widgets and information can be placed here.</p>
</div>

