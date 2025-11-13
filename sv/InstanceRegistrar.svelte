<!-- sv/InstanceRegistrar.svelte -->
<script>
    import { onMount } from 'svelte';
    import { instanceRegistry } from './windows.js';
    export let tabId;
    export let instance;

    onMount(() => {
        instanceRegistry.register(tabId, instance);
        return () => {
            instanceRegistry.unregister(tabId);
        }
    });
</script>