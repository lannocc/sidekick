# Proposal: Local File Proxy via SKYBRIDGE

**Author:** LANNOCC
**Date:** 12/11/2025
**Status:** Implemented

## 1. Introduction & Motivation

The SKYBOARD environment, particularly within the `Settings` board, provides file pickers that allow users to select local files for customization, such as setting a desktop background image. Currently, this selection is stored as a `file://` URI.

However, modern web browsers enforce strict security policies that prevent web pages, even those served from `localhost`, from accessing `file://` resources. This same-origin policy restriction means that while users can select a local image file, the application cannot actually load and display it. This creates a broken user experience and limits the potential for rich, local media integration.

This proposal outlines a plan to overcome this limitation by enhancing our existing `sk bridge` service to act as a secure and efficient proxy for local file resources. This will enable the frontend to request and display content from local file paths, unlocking features like custom backgrounds and paving the way for future integrations like local video playback.

## 2. Core Requirements

1.  **Bridge as File Proxy:** The `sk bridge` WebSocket server must serve content from arbitrary local file paths requested by the frontend.
2.  **Efficient Transfer:** The solution must be performant for both small files (e.g., icons, configuration files) and very large files (e.g., high-resolution images, videos).
3.  **Streaming & Seeking Support:** To handle large media files, the proxy mechanism must support chunked reads and ranged requests, allowing for functionalities like pausing, resuming, and seeking in video players.
4.  **Seamless Frontend Integration:** The process of requesting and displaying a local file on the frontend should be straightforward and abstracted away from the component-level logic.
5.  **Solve Immediate Use Case:** The implementation must successfully enable the use of local images for background settings within the `Settings` board.

## 3. Proposed Architecture

We will leverage the existing, but currently underutilized, `fs_read` WebSocket endpoint which is already implemented in `sk/bridge.py`. Its design is perfectly suited for this task.

### Backend Recap (`sk/bridge.py`)

The `fs_read` message handler already possesses the necessary features:

*   **Input:** It accepts a `path`, an `offset` (in bytes), and a `length` (in bytes).
*   **Processing:** It opens the specified file in binary mode, seeks to the `offset`, and reads `length` bytes. A `length` of `-1` signifies reading to the end of the file.
*   **Output:** It returns a `fs_read_response` message containing:
    *   `content_b64`: The Base64-encoded content of the requested file chunk.
    *   `total_size`: The total size of the file in bytes.
    *   `offset` & `length`: The byte range of the returned chunk.
    *   `is_binary`: A flag indicating if the file is binary.

This existing implementation robustly supports both full-file reads (for small assets) and the ranged requests essential for streaming large media files.

### Frontend Architecture

The frontend will implement a consumption layer to make use of this backend capability.

1.  **Filesystem Adapter (`sv/fs_adapter.js`):** The adapter already exposes a `readFile(path, offset, length)` method that sends the correctly formatted `fs_read` message. It also subscribes to the `fsReadResponse` store from `sv/bridge.js`, making responses available to the component that instantiated it. No major changes are needed here.

2.  **Asset Resolution Service:** We will introduce a new client-side service or utility to manage the process of resolving `file://` URIs into displayable content. This service will act as a centralized point for fetching and caching local assets.

3.  **Consumption Patterns:**
    *   **For Small/Medium Files (e.g., Images):**
        When a component needs to display an image from a `file://` URI, the asset resolver will call `fsAdapter.readFile(path)` with default parameters to fetch the entire file in one request. Upon receiving the Base64-encoded content, it will construct a `data:` URL (e.g., `data:image/png;base64,...`). This `data:` URL can be used directly in `<img>` tags or CSS `background-image` properties.

    *   **For Large Files (e.g., Videos):**
        For a `<video>` element, loading the entire file into a `data:` URL is inefficient and memory-intensive. Instead, a dedicated video player component will use the **Media Source Extensions (MSE) API**. This component will use the asset resolver to request the video file in smaller chunks by making successive calls to `fsAdapter.readFile(path, offset, length)`. As each Base64 chunk arrives, it will be decoded and appended to an MSE `SourceBuffer`. This allows the browser to stream the video efficiently from our WebSocket bridge, enabling playback of large files with full support for seeking.

## 4. Implementation Plan

The backend and adapter layers are already in place. The work is focused entirely on the frontend consumption logic.

**Step 1: Create a Frontend Asset Resolution Utility**

We will create a helper function, `resolveLocalAssetUrl`, and an associated in-memory cache to handle `file://` URIs. This can be placed in `sv/bridge.js` file alongside other bridge helpers.

The core logic will be to manage the asynchronous request/response flow over the WebSocket.

```javascript
// In sv/fs_adapter.js, we need to ensure responses are directed to the correct caller.
// The existing `requester_id` pattern is perfect for this.

// Additions for `sv/bridge.js`:

import { v4 as uuidv4 } from 'uuid';

const pendingRequests = new Map();
const assetCache = new Map();

fsReadResponse.subscribe(msg => {
    if (msg && pendingRequests.has(msg.requester_id)) {
        const { resolve } = pendingRequests.get(msg.requester_id);
        resolve(msg);
        pendingRequests.delete(msg.requester_id);
    }
});

fsError.subscribe(err => {
     if (err && pendingRequests.has(err.requester_id)) {
        const { reject } = pendingRequests.get(err.requester_id);
        reject(new Error(err.error));
        pendingRequests.delete(err.requester_id);
    }
});

function readFileChunk(path, offset = 0, length = -1) {
    const requester_id = uuidv4();
    return new Promise((resolve, reject) => {
        pendingRequests.set(requester_id, { resolve, reject });
        sendMessage({ type: 'fs_read', path, offset, length, requester_id });
    });
}

export async function resolveAssetDataUrl(url) {
    if (!url || !url.startsWith('file://')) {
        return url;
    }
    if (assetCache.has(url)) {
        return assetCache.get(url);
    }

    const path = url.substring('file://'.length);
    const promise = readFileChunk(path).then(response => {
        // Simple MIME type detection, can be improved
        const extension = path.split('.').pop().toLowerCase();
        let mimeType = 'application/octet-stream';
        if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(extension)) {
            mimeType = `image/${extension}`;
        }
        const dataUrl = `data:${mimeType};base64,${response.content_b64}`;
        assetCache.set(url, dataUrl);
        return dataUrl;
    });

    assetCache.set(url, promise); // Cache the promise itself
    return promise;
}
```

**Step 2: Integrate with UI Components**

The primary component responsible for rendering the desktop background will be updated to use this new resolver.

```svelte
<!-- In a component like Desktop.svelte -->
<script>
    import { desktopSettings } from '../desktop.js';
    import { resolveAssetDataUrl } from '../bridge.js';

    let backgroundStyle = '';

    $: if ($desktopSettings.sky.scene.bgImage) {
        resolveAssetDataUrl($desktopSettings.sky.scene.bgImage).then(resolvedUrl => {
            // Construct CSS style using the resolved URL
            backgroundStyle = `background-image: url(${resolvedUrl}); ...`;
        });
    }
</script>

<div style={backgroundStyle}>...</div>
```

This reactive approach ensures that whenever the background image setting changes, the new URL is resolved and the UI updates accordingly.

**Step 3: Verify `Settings.svelte` Integration**

The `Settings.svelte` component is the source of these `file://` URIs. Its current implementation is already correct:

1.  It calls `newFileExplorer({ connectionType: 'skybridge', pickerTargetId: ... })`.
2.  It listens to the `fileSelection` store.
3.  When a file is selected, it updates the `desktopSettings` store with the `file://${path}` URI.

No changes are required in `Settings.svelte`. The final step is to verify that selecting a new local image in the Settings window correctly triggers the resolution logic in Step 2, causing the desktop background to update instantly.

## 5. Future Work: Video Playback

The architecture established here directly enables advanced media features. A future `<LocalVideoPlayer>` component can be implemented as follows:

1.  The component will use the Media Source Extensions (MSE) API to create a playable blob URL for a `<video>` element.
2.  It will use our new `readFileChunk(path, offset, length)` utility to fetch the video file in manageable segments (e.g., 1MB chunks).
3.  As each Base64 chunk is received, it will be decoded to a binary buffer and appended to the MSE `SourceBuffer`.
4.  User interactions like seeking will be handled by calculating the new byte `offset` based on the video's timeline and metadata, then issuing a new `readFileChunk` request to fetch the appropriate segment of the file from the backend.

No backend modifications will be necessary to support this functionality.

## 6. Conclusion

By implementing a frontend consumption layer for the existing `fs_read` bridge command, we can elegantly solve the browser's security restrictions on `file://` access. This approach provides an immediate solution for custom image backgrounds, improves the user experience, and establishes a powerful, scalable foundation for future local media integration, such as high-performance video streaming, directly within the SKYBOARD environment.

