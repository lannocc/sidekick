<!-- sv/AttachMenu.svelte -->
<script>
    import { createEventDispatcher, onMount } from 'svelte';

    export let isLoadingDevices = false;
    export let attachDevices = [];
    export let isLoadingUsers = false;
    export let attachUsers = [];

    const dispatch = createEventDispatcher();

    let selectedDevice = null;
    let selectedUser = null; // For list highlighting
    let username = ''; // For the input field
    let inputEl;

    function handleDeviceClick(item) {
        selectedDevice = item.displayName;
        if (!username) {
            username = item.displayName;
        }
    }

    function handleUserClick(item) {
        selectedUser = item.name;
        username = item.name;
    }

    function performAttach() {
        if (!selectedDevice) return;
        dispatch('attach', { device: selectedDevice, user: username });
    }

    function handleKeydown(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            performAttach();
        }
    }

    onMount(() => {
        // Request data from parent when mounted
        dispatch('requestData');
        inputEl?.focus();
    });
</script>

<style>
    .attach-menu { display: flex; width: 600px; height: 300px; flex-direction: column; }
    .attach-panels { display: flex; flex-grow: 1; overflow: hidden; }
    .attach-panel { width: 35%; display: flex; flex-direction: column; border-right: 1px solid var(--border-color); }
    .attach-panel:first-child { width: 65%; }
    .attach-panel:last-child { border-right: none; }
    .panel-header { padding: 4px 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); font-weight: bold; }
    .panel-list { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .list-item { padding: 4px 8px; cursor: pointer; border-radius: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .list-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .list-item.selected { background-color: #3498db; color: white; }
    .attach-footer { padding: 6px 8px; border-top: 1px solid var(--border-color); display: flex; align-items: center; gap: 8px; flex-shrink: 0; background-color: var(--title-bar-bg); }
    .attach-footer input {
        flex-grow: 1;
        box-sizing: border-box;
        background-color: var(--console-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 4px;
        border-radius: 3px;
    }
    .attach-footer button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 4px 8px; cursor: pointer; border-radius: 3px; }
    .attach-footer button:disabled { opacity: 0.5; cursor: not-allowed; }
    .attach-footer button.primary { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .path-header { font-size: 0.9em; color: #95a5a6; padding: 2px 8px; flex-shrink: 0; }
</style>

<div class="attach-menu">
    <div class="attach-panels">
        <div class="attach-panel">
            <div class="panel-header">Device</div>
            <div class="panel-list">
                {#if isLoadingDevices}
                    <div class="list-item">Loading...</div>
                {:else}
                    {#each attachDevices as item (item.fullPath)}
                        <div
                            class="list-item"
                            class:selected={selectedDevice === item.displayName}
                            on:click={() => handleDeviceClick(item)}
                            title={item.displayName}
                        >
                            {item.type === 'dir' ? '🗂️' : '🔌'} {item.displayName}
                        </div>
                    {:else}
                        <div class="list-item">(empty)</div>
                    {/each}
                {/if}
            </div>
        </div>
        <div class="attach-panel">
            <div class="panel-header">User (Optional)</div>
            <div class="path-header">/home</div>
             <div class="panel-list">
                {#if isLoadingUsers}
                    <div class="list-item">Loading...</div>
                {:else}
                    {#each attachUsers as item (item.name)}
                        <div
                            class="list-item"
                            class:selected={selectedUser === item.name}
                            on:click={() => handleUserClick(item)}
                            title={item.name}
                        >
                            👤 {item.name}
                        </div>
                  {:else}
                        <div class="list-item">(no users found)</div>
                    {/each}
                {/if}
            </div>
        </div>
    </div>
    <div class="attach-footer">
        <input
            type="text"
            placeholder="username (optional)"
            bind:this={inputEl}
            bind:value={username}
            on:keydown={handleKeydown}
        />
        <button
            class="primary attach-button-main"
            disabled={!selectedDevice}
            on:click={performAttach}>
            Attach
        </button>
    </div>
</div>