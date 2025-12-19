<script>
    import { onMount, onDestroy } from 'svelte';

    // Make `mirrored` a prop to receive saved state on re-creation.
    export let mirrored = true;

    // Add a `getState` function so the window manager can save the component's state.
    export function getState() {
        return { mirrored };
    }

    let videoEl;
    let canvasEl; // For taking snapshots
    let stream;
    let error = null;
    let showControls = false; // State to control control visibility

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

    /**
     * Captures the current frame from the video, creates a PNG, and triggers a download.
     * It correctly handles the mirrored state of the video.
     */
    function takeSnapshot() {
        if (!videoEl || !canvasEl) return;

        const context = canvasEl.getContext('2d');
        const width = videoEl.videoWidth;
        const height = videoEl.videoHeight;

        canvasEl.width = width;
        canvasEl.height = height;

        // Flip the canvas context horizontally if the video is mirrored
        if (mirrored) {
            context.translate(width, 0);
            context.scale(-1, 1);
        }

        context.drawImage(videoEl, 0, 0, width, height);

        // Create a download link for the snapshot
        const dataUrl = canvasEl.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = dataUrl;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        link.download = `snapshot-${timestamp}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
</script>

<style>
    .webcam-container {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        position: relative; /* Needed for absolute positioning of controls */
    }
    video {
        width: 100%;
        height: 100%;
        object-fit: contain;
        transition: transform 0.3s ease; /* For smooth mirroring */
    }
    video.mirrored {
        transform: scaleX(-1);
    }
    .error-message {
        padding: 20px;
        color: #e74c3c;
        text-align: center;
        font-family: sans-serif;
    }
    .controls {
        position: absolute;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 10px;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 10px;
        border-radius: 10px;
        z-index: 10;
        opacity: 0; /* Hidden by default */
        transition: opacity 0.3s ease-in-out; /* Fade transition */
        pointer-events: none; /* Don't interact when hidden */
    }
    .controls.visible {
        opacity: 1; /* Visible on hover */
        pointer-events: auto;
    }
    .controls button {
        padding: 8px 16px;
        border: none;
        background-color: #3498db;
        color: white;
        border-radius: 5px;
        cursor: pointer;
        font-family: sans-serif;
        font-size: 14px;
        transition: background-color 0.2s;
        font-weight: bold;
    }
    .controls button:hover {
        background-color: #2980b9;
    }
    .snapshot-canvas {
        display: none; /* This canvas is used off-screen */
    }
</style>

<div
    class="webcam-container"
    on:mouseenter={() => showControls = true}
    on:mouseleave={() => showControls = false}
>
    {#if error}
        <div class="error-message">{error}</div>
    {:else}
        <video bind:this={videoEl} class:mirrored autoplay playsinline muted></video>

        <!-- Camera Controls -->
        <div class="controls" class:visible={showControls}>
            <button on:click={() => mirrored = !mirrored}>
                {#if mirrored}Unmirror{:else}Mirror{/if}
            </button>
            <button on:click={takeSnapshot}>
                Take Snapshot
            </button>
        </div>

        <!-- Hidden canvas for generating snapshots -->
        <canvas bind:this={canvasEl} class="snapshot-canvas"></canvas>
    {/if}
</div>
