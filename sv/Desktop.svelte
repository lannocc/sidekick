<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { windows } from './windows.js';
    import Window from './Window.svelte';
    import { desktopSettings } from './desktopStore.js';

    let backgroundStyle = '';

    desktopSettings.subscribe(settings => {
        if (settings.bgType === 'gradient') {
            backgroundStyle = `linear-gradient(45deg, ${settings.bgGradientStart} 0%, ${settings.bgGradientEnd} 100%)`;
        } else if (settings.bgType === 'color') {
            backgroundStyle = settings.bgColor;
        } else if (settings.bgType === 'image' && settings.bgImage) {
            backgroundStyle = `url('${settings.bgImage}')`;
        } else {
            // Fallback to default gradient
            backgroundStyle = `linear-gradient(45deg, #2c3e50 0%, #46627f 100%)`;
        }
    });
</script>

<style>
    .desktop {
        flex-grow: 1;
        position: relative;
        width: 100%;
        overflow: hidden;
        /* Default background color */
        background-color: var(--background-color);
        /* Dynamic background is applied via style attribute */
        background-size: cover;
        background-position: center;
        transition: background 0.5s ease-in-out;
    }
</style>

<div class="desktop" style:background={backgroundStyle}>
    {#each $windows as win (win.id)}
        <Window {...win} />
    {/each}
</div>

