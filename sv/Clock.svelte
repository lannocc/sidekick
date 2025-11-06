<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';

    let time = new Date();
    let interval;

    onMount(() => {
        interval = setInterval(() => {
            time = new Date();
        }, 1000);
    });

    onDestroy(() => {
        clearInterval(interval);
    });

    $: hours = time.getHours();
    $: minutes = time.getMinutes();
    $: seconds = time.getSeconds();

    // Calculations for hand rotations in degrees
    $: hourRotation = (hours % 12) * 30 + minutes / 2;
    $: minuteRotation = minutes * 6 + seconds / 10;
    $: secondRotation = seconds * 6;
</script>

<style>
    .clock {
        width: 34px;
        height: 34px;
        filter: drop-shadow(0 1px 1px rgba(0,0,0,0.2));
    }
    .face {
        stroke: var(--border-color);
        stroke-width: 2;
        fill: var(--taskbar-button-bg);
    }
    .hand {
        stroke-linecap: round;
    }
    .hour {
        stroke: var(--taskbar-text);
        stroke-width: 6;
    }
    .minute {
        stroke: var(--taskbar-text);
        stroke-width: 4;
    }
    .second {
        stroke: #e74c3c; /* A distinct red for the second hand */
        stroke-width: 2;
    }
    .pivot {
        fill: #e74c3c;
    }
</style>

<div class="clock">
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <circle class="face" cx="50" cy="50" r="48" />

        <!-- Hour Markers -->
        {#each Array(12) as _, i}
            <line
                stroke=var(--border-color)
                stroke-width="3"
                x1="50"
                y1="5"
                x2="50"
                y2="12"
                transform="rotate({i * 30} 50 50)"
            />
        {/each}

        <!-- Hands of the clock -->
        <line
            class="hand hour"
            x1="50"
            y1="50"
            x2="50"
            y2="25"
            transform="rotate({hourRotation} 50 50)"
        />
        <line
            class="hand minute"
            x1="50"
            y1="50"
            x2="50"
            y2="15"
            transform="rotate({minuteRotation} 50 50)"
        />
        <line
            class="hand second"
            x1="50"
            y1="50"
            x2="50"
            y2="10"
            transform="rotate({secondRotation} 50 50)"
        />

        <circle class="pivot" cx="50" cy="50" r="3" />
    </svg>
</div>

