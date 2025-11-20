# Proposal: Project Sentinel for Activity Notice

**Author:** LANNOCC
**Date:** November 20, 2025
**Status:** Draft

## 1. Introduction & Motivation

In a multitasking environment like SKYBOARD, users often have multiple windows and tabs running background processes, such as long-running commands in an `IoskConsole`, automated tasks in an `Ask` window, or incoming messages in a `IoskPrivateChat`. Currently, there is no standardized way to bring a user's attention to significant events in these background windows, short of the user manually checking each one.

This proposal, codenamed **Project Sentinel**, outlines a comprehensive, system-wide "Notice" framework. This framework will monitor windows for meaningful activity, providing configurable visual and audible alerts to the user. Furthermore, it will introduce a centralized Notification Center, integrated into the Taskbar Clock, to log these events for later review. By implementing Sentinel, we will make SKYBOARD a more proactive and responsive environment, ensuring users never miss important updates from their background tasks.

## 2. Core Requirements

1.  **Generic Activity Emitter:** A centralized function, `windows.notifyActivity()`, that any component can call to signal a noteworthy event.
2.  **Visual Notifications:** When a notice is triggered for an inactive or minimized window, its frame and taskbar item will briefly flash or glow with a configurable color.
3.  **Audible Notifications:** The system will optionally play a sound effect upon receiving a notice. This will use the existing sound asset library and support custom URLs.
4.  **Granular Configuration:**
    *   **Global Defaults:** A new section in the main Desktop `Settings` panel will allow users to define default notice behavior (enable/disable, flash color, sound choice) for all windows.
    *   **Per-Window-Type Overrides:** Each window's settings panel will include options to either inherit the global defaults, disable notices entirely for that window type, or enable them with custom override settings for color and sound.
5.  **Smart Notifications:** Notices should only be triggered for windows that are not currently active and focused, preventing unnecessary alerts for tasks the user is already watching.
6.  **Notification Center:**
    *   The `Clock` on the taskbar will be enhanced to act as a notification hub.
    *   It will display a badge indicating the number of unread notifications.
    *   Clicking the clock will open a dropdown panel displaying a history of recent notice events.
    *   Each entry in the history will be clickable, allowing the user to immediately focus the corresponding window and tab.

## 3. Proposed Architecture

### 3.1. Centralized "Notice" System

The core of Sentinel will be a new function in `sv/windows.js` and new data structures in `sv/desktopStore.js`.

#### 3.1.1. `sv/windows.js`: The `notifyActivity` Emitter

A new exported function will be the entry point for all notifications.

```javascript
// in windows.js, within createWindowManager()
const notifyActivity = (groupId, tabId, payload = {}) => {
    update(windows => {
        const group = windows.find(g => g.id === groupId);
        if (!group || group.isActive) {
            return windows; // Don't notify for active windows
        }

        const tab = group.tabs.find(t => t.id === tabId);
        if (!tab) return windows;

        // 1. Resolve Settings (see below)
        const settings = resolveNoticeSettings(tab.componentName);
        if (!settings.enabled) return windows;

        // 2. Trigger Visual Effect
        const noticeId = Date.now();
        const updatedGroup = { ...group, notice: { id: noticeId, color: settings.visual.color } };

        // 3. Play Audio
        if (settings.audio.enabled && settings.audio.sound) {
            playNoticeSound(settings.audio);
        }

        // 4. Log to Notification Center
        logToNotificationCenter(group, tab, payload);

        // 5. Set timeout to clear the visual effect
        setTimeout(() => {
            update(currentWindows => currentWindows.map(w =>
                (w.id === groupId && w.notice?.id === noticeId) ? { ...w, notice: null } : w
            ));
        }, settings.visual.duration);

        return windows.map(w => w.id === groupId ? updatedGroup : w);
    });
};
```

Helper functions `resolveNoticeSettings`, `playNoticeSound`, and `logToNotificationCenter` will encapsulate the detailed logic.

#### 3.1.2. `sv/desktopStore.js`: Settings and History

New data structures will be added to manage configuration and state.

```javascript
// in desktopStore.js

// Add to desktopSettings defaults
const defaults = {
    // ... existing defaults
    noticeDefaults: {
        enabled: true,
        visual: {
            enabled: true,
            color: '#f39c12', // Default: Orange
            duration: 1200,   // ms
        },
        audio: {
            enabled: true,
            sound: 'ding.wav', // Default: Ding
            url: '',
        }
    }
};

// Add to windowSettings store for per-window overrides
// Example for IoskConsole:
// { "IoskConsole": { "notice": { "mode": "override", "visual": { "color": "#e74c3c" } } } }

// New stores for Notification Center
export const notificationHistory = writable([]);
export const unreadNoticeCount = writable(0);
```

### 3.2. Frontend Implementation

#### 3.2.1. Instrumenting Components

Components will be modified to call `windows.notifyActivity` when appropriate. They should only do so when their window is not active.

*   **`sv/IoskPrivateChat.svelte`:** When a new message is received from the `remoteUser`.
    ```javascript
    // in handleMessage(message)
    if (isForThisWindow && message.from !== localUser) {
        messages = [...messages, message];
        if (!get(windows).find(w => w.id === groupId)?.isActive) {
            windows.notifyActivity(groupId, id, { summary: `New message from ${getDisplayName(message.from)}` });
        }
    }
    ```
*   **`sv/IoskWatch.svelte`:** When the `output` changes and is different from the previous output.
*   **`sv/IoskConsole.svelte`:** When new output arrives from the WebSocket, excluding user-entered commands. This could be done by checking if the console's `<input>` is focused.

#### 3.2.2. `Settings.svelte` (Global Defaults)

A new `<fieldset>` will be added to manage the `noticeDefaults` in `desktopSettings`.

```html
<!-- in sv/Settings.svelte -->
<fieldset>
    <legend>Activity Notice Defaults</legend>
    <label>
        <input type="checkbox" bind:checked={settings.noticeDefaults.enabled} on:change={handleUpdate}>
        Enable Notices Globally
    </label>
    {#if settings.noticeDefaults.enabled}
    <div class="options-group">
        <label class="color-picker-label">
            <span>Flash Color</span>
            <input type="color" bind:value={settings.noticeDefaults.visual.color} on:input={handleUpdate}>
        </label>
        <label class="color-picker-label">
            <span>Notice Sound</span>
            <select class="select-input" bind:value={settings.noticeDefaults.audio.sound} on:change={handleUpdate}>
                <!-- options for sounds -->
            </select>
        </label>
    </div>
    {/if}
</fieldset>
```

#### 3.2.3. Per-Window Settings Modals

The reusable `WindowSettingsModal.svelte` (proposed in `refactor.md`) or the generic modal in `Window.svelte` will be updated to manage per-window overrides stored in the `windowSettings` store.

```html
<!-- in a settings modal -->
<fieldset>
    <legend>Activity Notice</legend>
    <div class="radio-group">
        <label><input type="radio" bind:group={windowSettingsForModal.notice.mode} value="global"> Global Default</label>
        <label><input type="radio" bind:group={windowSettingsForModal.notice.mode} value="enabled"> Override</label>
        <label><input type="radio" bind:group={windowSettingsForModal.notice.mode} value="disabled"> Disabled</label>
    </div>
    {#if windowSettingsForModal.notice.mode === 'enabled'}
        <!-- Override controls for color and sound -->
    {/if}
</fieldset>
```

#### 3.2.4. `Window.svelte` & `Taskbar.svelte`: Visual Effects

These components will react to the new `notice` property on a window group.

```svelte
<!-- in Window.svelte -->
<script>
    export let notice; // { id, color } or null
    $: isNoticing = !!notice;
</script>

<div class="window-frame" class:noticing={isNoticing} style:--notice-color={notice?.color}>
    <!-- ... -->
</div>
```

```css
/* in Window.svelte */
@keyframes notice-glow {
    50% { border-color: var(--notice-color); box-shadow: 0 0 20px 5px var(--notice-color); }
}
.window-frame.noticing {
    animation: notice-glow 1.2s ease-in-out;
}
```

A similar class and animation will be added to the `.task-item` in `Taskbar.svelte`.

#### 3.2.5. Notification Center

*   **`sv/Taskbar.svelte`:** The `Clock` component will be wrapped in a button. A badge will be displayed, bound to the `unreadNoticeCount` store.
    ```svelte
    <!-- in Taskbar.svelte -->
    <div class="taskbar-center" bind:this={centerSectionEl}>
        <button class="clock-button" on:click={toggleNotificationCenter}>
            <Clock />
            {#if $unreadNoticeCount > 0}
                <span class="notice-badge">{$unreadNoticeCount}</span>
            {/if}
        </button>
    </div>
    {#if showNotificationCenter}
        <NotificationCenter on:close={() => showNotificationCenter = false} />
    {/if}
    ```
*   **`sv/NotificationCenter.svelte` (New Component):** This component will be created to render the notification history.
    *   It subscribes to the `notificationHistory` store.
    *   On mount, it will reset `unreadNoticeCount` to zero and mark all visible notices as read.
    *   Each item will display a timestamp, icon, summary, and a "Focus" button that calls `windows.focusWindow()` and `windows.setActiveTab()`.

## 4. Conclusion

**Project Sentinel** provides a robust and elegant solution for managing background activity notifications. By combining a centralized event system with flexible, layered configuration, it empowers users to stay informed without being overwhelmed. The integration of the Notification Center into the taskbar clock creates an intuitive, non-intrusive log of events. This feature will significantly enhance the user experience, making SKYBOARD feel more alive, intelligent, and useful as a multitasking OS.

