<script>
    import { onMount } from 'svelte';
    import { slide } from 'svelte/transition';
    import { get } from 'svelte/store';
    import { notificationHistory, unreadNoticeCount } from '../desktop.js';
    import { windows } from '../windows.js';
    import NotificationCenter from './NotificationCenter.svelte';

    export let isActive;
    export let id;
    export let groupId;
    export let isDetached = false; // Is this a popped-out view?
    export let detachedGroupId = null; // If so, which group to display?


    // --- State ---
    let currentView = 'chronological'; // 'chronological' or 'grouped'
    let expandedNotifications = {}; // For collapsible items
    let selectedNotifications = new Set(); // For selection
    let activeGroupId = null; // For grouped view tabs
    let detachedGroups = {}; // For tracking popped-out groups

    // --- Lifecycle ---
    onMount(() => {
        // As per proposal, reset count on mount
        if (!isDetached) {
            unreadNoticeCount.set(0);
        }
    });

    // --- Reactive Computations ---
    $: groupedNotifications = (() => {
        if (!$notificationHistory || $notificationHistory.length === 0) return [];

        const groups = $notificationHistory.reduce((acc, notification) => {
            const groupKey = notification.groupId;
            if (!acc[groupKey]) {
                acc[groupKey] = [];
            }
            acc[groupKey].push(notification);
            return acc;
        }, {});

        // Map to an array of group objects for the template
        return Object.values(groups).map(notifications => {
            const mostRecent = notifications[0]; // History is already sorted newest first
            const tab = get(windows).flatMap(g => g.tabs).find(t => t.id === mostRecent.tabId);
            return {
                groupId: mostRecent.groupId,
                title: tab?.title || mostRecent.icon,
                count: notifications.length,
                notifications,
            };
        });
    })();

    // Set initial active group or reset if it disappears
    $: if (!isDetached && currentView === 'grouped') {
        if (groupedNotifications.length > 0) {
            const groupExists = groupedNotifications.some(g => g.groupId === activeGroupId);
            if (!groupExists) {
                activeGroupId = groupedNotifications[0].groupId;
            }
        } else {
            activeGroupId = null;
        }
    }

    $: activeGroup = activeGroupId ? groupedNotifications.find(g => g.groupId === activeGroupId) : null;
    $: detachedGroup = isDetached ? groupedNotifications.find(g => g.groupId === detachedGroupId) : null;

    // Clear selection when view or active group changes
    $: if (currentView) {
        selectedNotifications = new Set();
        expandedNotifications = {};
    }
    $: if (activeGroupId) {
        selectedNotifications = new Set();
        expandedNotifications = {};
    }

    // Reactive statement to check if a detached window was closed or moved
    $: if (!isDetached && $windows) {
        const allTabsToGroups = new Map($windows.flatMap(w => w.tabs.map(t => [t.id, w.id])));
        let changed = false;
        for (const groupId in detachedGroups) {
            const detachedInfo = detachedGroups[groupId];
            if (detachedInfo) { // detachedInfo is now { groupId, tabId }
                const currentGroupId = allTabsToGroups.get(detachedInfo.tabId);

                if (!currentGroupId) {
                    // The tab no longer exists, it must have been closed.
                    detachedGroups[groupId] = null;
                    changed = true;
                } else if (currentGroupId !== detachedInfo.groupId) {
                    // The tab has been moved to a new window group. Update our reference.
                    detachedGroups[groupId].groupId = currentGroupId;
                    changed = true;
                }
            }
        }
        if (changed) {
            detachedGroups = detachedGroups; // Trigger reactivity
        }
    }

    // --- Handlers ---
    function handleItemClick(notification) {
        windows.focusWindow(notification.groupId);
        windows.setActiveTab(notification.groupId, notification.tabId);
    }

    function popOutGroup(groupId) {
        const group = groupedNotifications.find(g => g.groupId === groupId);
        if (!group) return;

        const newWindow = windows.addWindow(NotificationCenter, {
            title: `Notifications - ${group.title}`,
            isDetached: true,
            detachedGroupId: groupId,
            width: 475,
            height: 475,
        });

        if (newWindow && newWindow.groupId) {
            detachedGroups[groupId] = { groupId: newWindow.groupId, tabId: newWindow.tabId };
            detachedGroups = detachedGroups;
        }
    }

    function toggleExpand(notificationId) {
        expandedNotifications[notificationId] = !expandedNotifications[notificationId];
    }

    function toggleSelection(notificationId) {
        if (selectedNotifications.has(notificationId)) {
            selectedNotifications.delete(notificationId);
        } else {
            selectedNotifications.add(notificationId);
        }
        selectedNotifications = selectedNotifications;
    }

    function selectAll() {
        deselectAll(); // Clear first
        let idsToSelect = [];
        if (isDetached) {
            if (detachedGroup) idsToSelect = detachedGroup.notifications.map(n => n.id);
        } else if (currentView === 'chronological') {
            idsToSelect = $notificationHistory.map(n => n.id);
        } else if (activeGroup) {
            idsToSelect = activeGroup.notifications.map(n => n.id);
        }
        selectedNotifications = new Set(idsToSelect);
    }

    function deselectAll() {
        selectedNotifications = new Set();
    }

    function expandAll() {
        let list;
        if (isDetached) {
            list = detachedGroup?.notifications;
        } else {
            list = currentView === 'chronological' ? $notificationHistory : activeGroup?.notifications;
        }
        if (!list) return;
        const newExpanded = { ...expandedNotifications };
        list.forEach(n => newExpanded[n.id] = true);
        expandedNotifications = newExpanded;
    }

    function collapseAll() {
        expandedNotifications = {};
    }

    function clearSingle(notificationId, event) {
        event.stopPropagation();
        notificationHistory.update(h => h.filter(n => n.id !== notificationId));
        selectedNotifications.delete(notificationId);
        selectedNotifications = selectedNotifications;
    }

    function clearSelected() {
        if (selectedNotifications.size === 0) return;
        if (confirm(`Are you sure you want to clear ${selectedNotifications.size} selected notifications?`)) {
            notificationHistory.update(h => h.filter(n => !selectedNotifications.has(n.id)));
            deselectAll();
        }
    }

    function clearHistory() {
        if (isDetached) {
            if (!detachedGroup) return;
            if (confirm(`Are you sure you want to clear all ${detachedGroup.count} notifications for "${detachedGroup.title}"? This cannot be undone.`)) {
                const groupNotificationIds = new Set(detachedGroup.notifications.map(n => n.id));
                notificationHistory.update(h => h.filter(n => !groupNotificationIds.has(n.id)));
            }
            return;
        }

        if (currentView === 'grouped') {
            if (!activeGroup) return;
            if (confirm(`Are you sure you want to clear all ${activeGroup.count} notifications for "${activeGroup.title}"? This cannot be undone.`)) {
                const groupNotificationIds = new Set(activeGroup.notifications.map(n => n.id));
                notificationHistory.update(h => h.filter(n => !groupNotificationIds.has(n.id)));
            }
        } else { // 'chronological' view
            if (confirm('Are you sure you want to clear all notifications? This cannot be undone.')) {
                notificationHistory.set([]);
                deselectAll();
                expandedNotifications = {};
            }
        }
    }

    function formatTime(date) {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    }

    function formatFullTime(date) {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        return date.toLocaleString();
    }

    function getFirstLine(text) {
        if (!text || typeof text !== 'string') return '';
        const newlineIndex = text.indexOf('\n');
        return newlineIndex === -1 ? text : text.substring(0, newlineIndex);
    }

    // --- Color logic ---
    const groupColors = [
        '--ansi-bright-blue',
        '--ansi-bright-green',
        '--ansi-bright-cyan',
        '--ansi-bright-magenta',
        '--ansi-bright-yellow',
        '--ansi-bright-red',
    ];

    function getColorForGroup(groupId) {
        if (groupId == null) return groupColors[0];
        return groupColors[groupId % groupColors.length];
    }
</script>

<style>
    :global(:root) {
        --ansi-red: #c0392b; --ansi-green: #27ae60; --ansi-yellow: #f1c40f; --ansi-blue: #2980b9; --ansi-magenta: #8e44ad; --ansi-cyan: #16a085;
        --ansi-bright-red: #e74c3c; --ansi-bright-green: #2ecc71; --ansi-bright-yellow: #f39c12; --ansi-bright-blue: #3498db; --ansi-bright-magenta: #9b59b6; --ansi-bright-cyan: #1abc9c;
    }
    .notification-center {
        display: flex;
        flex-direction: column;
        height: 100%;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-family: monospace;
        font-size: 14px;
        overflow: hidden;
    }
    .header {
        padding: 10px;
        flex-shrink: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border-color);
    }
    h1 {
        font-size: 1.2em;
        margin: 0;
        color: var(--title-bar-text);
        flex-grow: 1;
    }
    .header-controls {
        display: flex;
        align-items: center;
        gap: 12px;
        padding-left: 15px;
    }
    .view-switcher {
        display: flex;
        background: var(--taskbar-button-bg);
        border-radius: 3px;
        border: 1px solid var(--border-color);
        overflow: hidden;
    }
    .view-switcher button {
        background: transparent;
        border: none;
        color: var(--taskbar-text);
        padding: 4px 10px;
        cursor: pointer;
        font-size: 0.9em;
        opacity: 0.7;
        border-left: 1px solid var(--border-color);
    }
    .view-switcher button:first-child {
        border-left: none;
    }
    .view-switcher button.active {
        background-color: var(--taskbar-button-hover-bg);
        color: var(--ansi-bright-blue);
        opacity: 1;
    }
    .view-switcher button:hover:not(.active) {
        background-color: var(--taskbar-button-hover-bg);
        opacity: 0.9;
    }

    /* Tab styles for Group View */
    .tabs-container {
        display: flex;
        flex-direction: column;
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
    }
    .tabs-row {
        display: flex;
        justify-content: flex-start;
        flex-wrap: wrap;
        background-color: #012133;
    }
    .tab-button {
        padding: 8px 16px;
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        border-bottom: 2px solid transparent;
        outline: none;
    }
    .tab-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .tab-button.active {
        color: var(--ansi-bright-blue);
        border-bottom-color: var(--ansi-bright-blue);
    }

    /* List Styles */
    .list-container {
        overflow-y: auto;
        flex-grow: 1;
        padding: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-height: 0;
    }
    .notification-entry {
        border: 1px solid var(--border-color);
        border-left-width: 4px;
        border-left-style: solid;
        border-radius: 3px;
        overflow: hidden;
        flex-shrink: 0;
    }
    .notification-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 8px;
        cursor: pointer;
        background-color: var(--title-bar-bg);
        user-select: none;
        overflow: hidden;
    }
    .notification-header:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .notification-delete-button {
        background: none; border: none; color: var(--title-bar-text); cursor: pointer;
        font-size: 1.5em; line-height: 1; padding: 0 8px 0 0; opacity: 0.5;
        font-weight: bold; align-self: center;
    }
    .notification-delete-button:hover {
        opacity: 1;
        color: var(--ansi-red);
    }
    .icon {
        flex-shrink: 0;
        width: 24px; height: 24px;
        background-color: var(--taskbar-button-bg); border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.6em; text-align: center; overflow-wrap: break-word;
        padding: 2px; box-sizing: border-box;
        margin: 0 5px;
    }
    .timestamp {
        font-size: 0.85em; opacity: 0.9; align-self: center;
        white-space: nowrap;
        padding-left: 5px;
        color: var(--ansi-bright-yellow);
    }
    .notification-preview {
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        opacity: 0.9; flex-grow: 1; min-width: 0;
        padding: 2px 8px; border-radius: 3px; cursor: pointer;
    }
    .notification-preview:hover {
        text-decoration: underline;
        color: var(--ansi-bright-cyan);
    }
    .notification-content {
        padding: 10px 15px;
        background-color: var(--window-bg);
        white-space: pre-wrap;
        word-break: break-all;
        cursor: pointer;
    }
     .notification-content:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .notification-select-checkbox {
        margin-left: auto; cursor: pointer; width: 16px; height: 16px; align-self: center;
    }

    /* Action Bar Styles */
    .action-bar {
        flex-shrink: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px;
        background-color: var(--title-bar-bg);
        border-top: 1px solid var(--border-color);
    }
    .action-bar button {
        background-color: var(--taskbar-button-bg);
        border: 1px solid var(--border-color); color: var(--title-bar-text);
        padding: 4px 8px; border-radius: 3px; cursor: pointer;
        margin-left: 5px; font-size: 0.9em;
    }
    .action-bar button:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .action-bar button:disabled {
        opacity: 0.5; cursor: not-allowed;
    }
    .action-bar .clear-button {
        background-color: var(--ansi-red); border-color: #e74c3c; color: white;
    }
    .action-bar .clear-button:hover:not(:disabled) {
        background-color: #e74c3c;
    }

    .empty-state {
        padding: 40px 20px; text-align: center; color: #7f8c8d;
        margin: auto;
    }
    .empty-state .icon {
        font-size: 2.5em; margin: 0 auto 10px; opacity: 0.5;
        width: auto; height: auto; background: none;
    }

    /* New styles for pop-out functionality */
    .tab-button-container {
        display: flex;
        align-items: center;
        position: relative;
    }
    .pop-out-button {
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        font-size: 1.1em;
        padding: 0 8px;
        opacity: 0.5;
        transition: opacity 0.2s;
    }
    .pop-out-button:hover {
        opacity: 1;
        color: var(--ansi-bright-blue);
    }
    .detached-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        text-align: center;
        color: var(--title-bar-text);
        margin: auto;
        flex-grow: 1;
    }
    .detached-placeholder button {
        margin-top: 15px;
        padding: 8px 16px;
        border-radius: 3px;
        cursor: pointer;
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        background-color: var(--taskbar-button-bg);
    }
    .detached-placeholder button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
</style>

{#if !isDetached}
    <div class="notification-center">
        <div class="header">
            <h1>Notifications</h1>
            <div class="header-controls">
                <div class="view-switcher">
                    <button class:active={currentView === 'chronological'} on:click={() => currentView = 'chronological'} title="List all notifications chronologically">
                        List
                    </button>
                    <button class:active={currentView === 'grouped'} on:click={() => currentView = 'grouped'} title="Group notifications by window">
                        Group
                    </button>
                </div>
            </div>
        </div>

        {#if currentView === 'chronological'}
            {#if $notificationHistory.length > 0}
                <div class="list-container">
                    {#each $notificationHistory as notification (notification.id)}
                        <div class="notification-entry" style="border-left-color: var({getColorForGroup(notification.groupId)})">
                            <div class="notification-header" on:click={() => toggleExpand(notification.id)}>
                                 <button class="notification-delete-button" title="Clear notification" on:click={(e) => clearSingle(notification.id, e)}>
                                    &times;
                                </button>
                                <div class="icon" title={notification.icon}>{notification.icon}</div>
                                {#if expandedNotifications[notification.id]}
                                    <span class="timestamp">{formatFullTime(notification.timestamp)}</span>
                                {:else}
                                    <span class="timestamp">{formatTime(notification.timestamp)}</span>
                                {/if}
                                {#if !expandedNotifications[notification.id]}
                                    <span class="notification-preview" on:click|stopPropagation={() => handleItemClick(notification)} title={notification.summary}>
                                        {getFirstLine(notification.summary)}
                                    </span>
                                {/if}
                                <input
                                    type="checkbox"
                                    class="notification-select-checkbox"
                                    title="Select notification"
                                    checked={selectedNotifications.has(notification.id)}
                                    on:click|stopPropagation
                                    on:change={() => toggleSelection(notification.id)}
                                />
                            </div>
                            {#if expandedNotifications[notification.id]}
                                <div class="notification-content" on:click={() => handleItemClick(notification)} transition:slide|local>
                                    {notification.summary}
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>
            {:else}
                <div class="empty-state">
                    <div class="icon">🔕</div>
                    <p>All caught up!</p>
                </div>
            {/if}
        {:else if currentView === 'grouped'}
            {#if groupedNotifications.length > 0}
                <div class="tabs-container">
                    <div class="tabs-row">
                        {#each groupedNotifications as group (group.groupId)}
                            <div class="tab-button-container">
                                <button class="tab-button" class:active={activeGroupId === group.groupId} on:click={() => activeGroupId = group.groupId}>
                                    {group.title} ({group.count}){#if detachedGroups[group.groupId]} ⇲{/if}
                                </button>
                                <button
                                    class="pop-out-button"
                                    title={detachedGroups[group.groupId] ? 'Focus popped-out window' : 'Pop out to new window'}
                                    on:click|stopPropagation={() => {
                                        const info = detachedGroups[group.groupId];
                                        if (info) {
                                            windows.setActiveTab(info.groupId, info.tabId);
                                        } else {
                                            popOutGroup(group.groupId);
                                        }
                                    }}
                                >
                                    ⇲
                                </button>
                            </div>
                        {/each}
                    </div>
                </div>
                
                {#if detachedGroups[activeGroupId]}
                    <div class="detached-placeholder">
                        <p>Content is in a separate window.</p>
                        <button on:click={() => {
                            const info = detachedGroups[activeGroupId];
                            if (info) windows.setActiveTab(info.groupId, info.tabId);
                        }}>
                            Focus Window
                        </button>
                    </div>
                {:else if activeGroup}
                    <div class="list-container">
                        {#each activeGroup.notifications as notification (notification.id)}
                            <div class="notification-entry" style="border-left-color: var({getColorForGroup(notification.groupId)})">
                                <div class="notification-header" on:click={() => toggleExpand(notification.id)}>
                                    <button class="notification-delete-button" title="Clear notification" on:click={(e) => clearSingle(notification.id, e)}>
                                        &times;
                                    </button>
                                    <div class="icon" title={notification.icon}>{notification.icon}</div>
                                    {#if expandedNotifications[notification.id]}
                                        <span class="timestamp">{formatFullTime(notification.timestamp)}</span>
                                    {:else}
                                        <span class="timestamp">{formatTime(notification.timestamp)}</span>
                                    {/if}
                                    {#if !expandedNotifications[notification.id]}
                                        <span class="notification-preview" on:click|stopPropagation={() => handleItemClick(notification)} title={notification.summary}>
                                            {getFirstLine(notification.summary)}
                                        </span>
                                    {/if}
                                    <input
                                        type="checkbox"
                                        class="notification-select-checkbox"
                                        title="Select notification"
                                        checked={selectedNotifications.has(notification.id)}
                                        on:click|stopPropagation
                                        on:change={() => toggleSelection(notification.id)}
                                    />
                                </div>
                                {#if expandedNotifications[notification.id]}
                                    <div class="notification-content" on:click={() => handleItemClick(notification)} transition:slide|local>
                                        {notification.summary}
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
            {:else}
                <div class="empty-state">
                    <div class="icon">🔕</div>
                    <p>All caught up!</p>
                </div>
            {/if}
        {/if}

        <!-- Action Bar -->
        {#if true}
          {@const list = currentView === 'chronological' ? $notificationHistory : (activeGroup && !detachedGroups[activeGroupId]) ? activeGroup.notifications : null}
          {#if list && list.length > 0}
              <div class="action-bar">
                  <div class="action-buttons">
                      <button class="clear-button" on:click={clearHistory}>
                          {currentView === 'grouped' ? 'Clear Group' : 'Clear All'}
                      </button>
                      <button
                          class="clear-button"
                          disabled={selectedNotifications.size === 0}
                          on:click={clearSelected}
                      >
                          Clear ({selectedNotifications.size})
                      </button>
                  </div>
                  <div class="selection-controls">
                      <button on:click={deselectAll}>Deselect All</button>
                      <button on:click={selectAll}>Select All</button>
                      <button on:click={collapseAll} title="Collapse all visible notifications">Collapse All</button>
                      <button on:click={expandAll} title="Expand all visible notifications">Expand All</button>
                  </div>
              </div>
          {/if}
        {/if}
    </div>
{:else}
    <div class="notification-center">
        {#if detachedGroup && detachedGroup.notifications.length > 0}
            <div class="list-container">
                {#each detachedGroup.notifications as notification (notification.id)}
                    <div class="notification-entry" style="border-left-color: var({getColorForGroup(notification.groupId)})">
                        <div class="notification-header" on:click={() => toggleExpand(notification.id)}>
                            <button class="notification-delete-button" title="Clear notification" on:click={(e) => clearSingle(notification.id, e)}>
                                &times;
                            </button>
                            <div class="icon" title={notification.icon}>{notification.icon}</div>
                            {#if expandedNotifications[notification.id]}
                                <span class="timestamp">{formatFullTime(notification.timestamp)}</span>
                            {:else}
                                <span class="timestamp">{formatTime(notification.timestamp)}</span>
                            {/if}
                            {#if !expandedNotifications[notification.id]}
                                <span class="notification-preview" on:click|stopPropagation={() => handleItemClick(notification)} title={notification.summary}>
                                    {getFirstLine(notification.summary)}
                                </span>
                            {/if}
                            <input
                                type="checkbox"
                                class="notification-select-checkbox"
                                title="Select notification"
                                checked={selectedNotifications.has(notification.id)}
                                on:click|stopPropagation
                                on:change={() => toggleSelection(notification.id)}
                            />
                        </div>
                        {#if expandedNotifications[notification.id]}
                            <div class="notification-content" on:click={() => handleItemClick(notification)} transition:slide|local>
                                {notification.summary}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
             <!-- Action Bar -->
            <div class="action-bar">
                <div class="action-buttons">
                    <button class="clear-button" on:click={clearHistory}>
                        Clear Group
                    </button>
                    <button
                        class="clear-button"
                        disabled={selectedNotifications.size === 0}
                        on:click={clearSelected}
                    >
                        Clear ({selectedNotifications.size})
                    </button>
                </div>
                <div class="selection-controls">
                    <button on:click={deselectAll}>Deselect All</button>
                    <button on:click={selectAll}>Select All</button>
                    <button on:click={collapseAll} title="Collapse all visible notifications">Collapse All</button>
                    <button on:click={expandAll} title="Expand all visible notifications">Expand All</button>
                </div>
            </div>
        {:else}
            <div class="empty-state">
                <div class="icon">🔕</div>
                <p>This group has been cleared.</p>
            </div>
        {/if}
    </div>
{/if}
