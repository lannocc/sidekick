<!-- sv/RoomsMenu.svelte -->
<script>
    import { createEventDispatcher } from 'svelte';

    export let availableRooms = [];
    export let currentRoomName = null;

    const dispatch = createEventDispatcher();

    function join(roomName) {
        dispatch('join', roomName);
    }

    function close() {
        dispatch('close');
    }
</script>

<style>
    .rooms-menu { position: absolute; top: 45px; left: 8px; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 100; display: flex; flex-direction: column; min-width: 180px; max-height: 250px; overflow-y: auto; }
    .menu-item { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; border-bottom: 1px solid var(--border-color); }
    .menu-item:last-child { border-bottom: none; }
    .menu-item:hover:not(:disabled) { background-color: var(--taskbar-button-hover-bg); }
    .menu-item:disabled { color: #7f8c8d; cursor: not-allowed; font-style: italic; }
    .menu-item-empty { padding: 8px 12px; color: #7f8c8d; font-style: italic; }
    .menu-separator { height: 3px; background-color: var(--border-color); margin: 0; }
    .close-item { color: #e74c3c; }
    .close-item:hover { background-color: #c0392b; color: white; }
</style>

<div class="rooms-menu">
    {#each availableRooms as room (room.name)}
        <button class="menu-item" on:click={() => join(room.name)} disabled={room.name === currentRoomName} title={room.topic || 'No topic'}>
            {room.name}
        </button>
    {:else}
        <span class="menu-item-empty">No rooms available</span>
    {/each}
    {#if currentRoomName}
        <div class="menu-separator"></div>
        <button class="menu-item close-item" on:click={close}>
            Close '{currentRoomName}'
        </button>
    {/if}
</div>