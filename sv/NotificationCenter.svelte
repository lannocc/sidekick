<script>
    import { onMount } from 'svelte';
    import { slide } from 'svelte/transition';
    import { get } from 'svelte/store';
    import { notificationHistory, unreadNoticeCount } from './desktop.js';
    import { windows } from './windows.js';

    export let isActive;
    export let id;
    export let groupId;

    // --- State ---
    let currentView = 'chronological'; // 'chronological' or 'grouped'
    let expandedNotifications = {}; // For collapsible items
    let selectedNotifications = new Set(); // For selection
    let activeGroupId = null; // For grouped view tabs

    // --- Lifecycle ---
    onMount(() => {
        // As per proposal, reset count on mount
        unreadNoticeCount.set(0);
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
    $: if (currentView === 'grouped') {
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

    // Clear selection when view or active group changes
    $: if (currentView) {
        selectedNotifications = new Set();
        expandedNotifications = {};
    }
    $: if (activeGroupId) {
        selectedNotifications = new Set();
        expandedNotifications = {};
    }

    // --- Handlers ---
    function handleItemClick(notification) {
        windows.focusWindow(notification.groupId);
        windows.setActiveTab(notification.groupId, notification.tabId);
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
        if (currentView === 'chronological') {
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
        const list = currentView === 'chronological' ? $notificationHistory : activeGroup?.notifications;
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
        if (confirm('Are you sure you want to clear all notifications? This cannot be undone.')) {
            notificationHistory.set([]);
            deselectAll();
            expandedNotifications = {};
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
    }
    .notification-entry {
        border: 1px solid var(--border-color);
        border-left-width: 4px;
        border-left-style: solid;
        border-radius: 3px;
        overflow: hidden;
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
        font-size: 0.85em; opacity: 0.7; align-self: center;
        white-space: nowrap;
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
</style>

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
                         <button class="tab-button" class:active={activeGroupId === group.groupId} on:click={() => activeGroupId = group.groupId}>
                            {group.title} ({group.count})
                        </button>
                    {/each}
                </div>
            </div>
            <div class="list-container">
                {#if activeGroup}
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
                {/if}
            </div>
        {:else}
            <div class="empty-state">
                <div class="icon">🔕</div>
                <p>All caught up!</p>
            </div>
        {/if}
    {/if}

    <!-- Action Bar -->
    {#if true} <!-- @const must be direct child of #if or similar -->
      {@const list = currentView === 'chronological' ? $notificationHistory : activeGroup?.notifications}
      {#if list && list.length > 0}
          <div class="action-bar">
              <div class="action-buttons">
                  <button class="clear-button" on:click={clearHistory}>Clear All</button>
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