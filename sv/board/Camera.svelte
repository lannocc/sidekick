<script>
    import { onMount, onDestroy } from 'svelte';

    let videoEl;
    let stream;
    let error = null;

    onMount(async () => {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
                if (videoEl) {
                    videoEl.srcObject = stream;
                }
            } catch (err) {
                console.error("Error accessing webcam:", err);
                if (err.name === 'NotAllowedError') {
                    error = "Webcam access was denied. Please allow camera access in your browser settings.";
                } else {
                    error = "Could not access webcam. Please ensure it is connected and not in use by another application.";
                }
            }
        } else {
            error = "Your browser does not support webcam access.";
        }
    });

    onDestroy(() => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    });
</script>

<style>
    .webcam-container {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #111;
        overflow: hidden;
    }
    video {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    .error-message {
        padding: 20px;
        color: #e74c3c;
        text-align: center;
        font-family: sans-serif;
    }
</style>

<div class="webcam-container">
    {#if error}
        <div class="error-message">{error}</div>
    {:else}
        <video bind:this={videoEl} autoplay playsinline muted></video>
    {/if}
</div>