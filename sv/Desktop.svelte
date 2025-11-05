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
            let size = 'cover';
            let repeat = 'no-repeat';
            let position = 'center center';

            switch (settings.bgImageDisplayMode) {
                case 'contain': // fit
                    size = 'contain';
                    break;
                case 'stretch':
                    size = '100% 100%';
                    break;
                case 'tile':
                    size = 'auto';
                    repeat = 'repeat';
                    position = '0 0'; // Tiling starts from top-left
                    break;
                case 'cover':
                default:
                    // 'cover' is the default case
                    break;
            }
            backgroundStyle = `url('${settings.bgImage}') ${position} / ${size} ${repeat}`;
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
        background-position: center;
        transition: background 0.5s ease-in-out;
    }
</style>

<div class="desktop" style:background={backgroundStyle}>
    {#each $windows as win (win.id)}
        <Window {...win} />
    {/each}
</div>

