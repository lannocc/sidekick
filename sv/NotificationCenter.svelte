<script>
    import { onMount } from 'svelte';
    import { slide } from 'svelte/transition';
    import { notificationHistory, unreadNoticeCount } from './desktop.js';
    import { windows } from './windows.js';

    export let isActive;
    export let id;
    export let groupId;

    let currentView = 'chronological'; // 'chronological' or 'grouped'
    let expandedGroups = {};

    onMount(() => {
        // As per proposal, reset count on mount
        unreadNoticeCount.set(0);
    });

    // Reactive computation for grouped view
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
            return {
                groupId: mostRecent.groupId,
                title: mostRecent.icon,
                count: notifications.length,
                notifications,
            };
        });
    })();

    function handleItemClick(notification) {
        windows.focusWindow(notification.groupId);
        windows.setActiveTab(notification.groupId, notification.tabId);
    }

    function toggleGroup(groupId) {
        expandedGroups[groupId] = !expandedGroups[groupId];
    }

    function clearHistory() {
        notificationHistory.set([]);
        expandedGroups = {};
    }

    function formatTime(date) {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    }
</script>

<style>
    .notification-center {
        display: flex;
        flex-direction: column;
        height: 100%;
        background-color: var(--window-bg);
        color: var(--taskbar-text);
        overflow: hidden;
    }
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
        gap: 10px;
    }
    .header h3 {
        margin: 0;
        font-size: 1em;
        font-weight: 500;
    }
    .header button {
        background: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--taskbar-text);
        padding: 2px 6px;
        font-size: 0.8em;
        border-radius: 3px;
        cursor: pointer;
        opacity: 0.7;
    }
    .header button:hover {
        background-color: var(--taskbar-button-hover-bg);
        opacity: 1;
    }

    /* Styles for view switcher */
    .view-switcher {
        display: flex;
        background: var(--taskbar-button-bg);
        border-radius: 3px;
        border: 1px solid var(--border-color);
        overflow: hidden;
        margin-left: auto; /* Push it to the left of the 'Clear All' button */
    }
    .view-switcher button {
        background: transparent;
        border: none;
        color: var(--taskbar-text);
        padding: 2px 8px;
        cursor: pointer;
        font-size: 0.8em;
        opacity: 0.7;
        border-left: 1px solid var(--border-color);
    }
    .view-switcher button:first-child {
        border-left: none;
    }
    .view-switcher button.active {
        background-color: var(--taskbar-button-hover-bg);
        color: #3498db;
        opacity: 1;
    }
    .view-switcher button:hover:not(.active) {
        background-color: var(--taskbar-button-hover-bg);
        opacity: 0.9;
    }

    .history-list {
        overflow-y: auto;
        flex-grow: 1;
    }
    .notification-item {
        display: flex;
        padding: 10px 12px;
        border-bottom: 1px solid var(--border-color);
        cursor: pointer;
        transition: background-color: 0.15s ease;
        gap: 10px;
        align-items: center;
    }
    .notification-item:last-child {
        border-bottom: none;
    }
    .notification-item:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .icon {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        background-color: var(--taskbar-button-bg);
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7em;
        text-align: center;
        overflow-wrap: break-word;
        padding: 2px;
        box-sizing: border-box;
    }
    .content {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
        overflow: hidden;
    }
    .summary {
        margin: 0;
        font-size: 0.9em;
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .timestamp {
        font-size: 0.75em;
        opacity: 0.7;
        align-self: flex-start;
    }
    .empty-state {
        padding: 40px 20px;
        text-align: center;
        color: #7f8c8d;
    }
    .empty-state .icon {
        font-size: 2.5em;
        margin: 0 auto 10px;
        opacity: 0.5;
        width: auto;
        height: auto;
        background: none;
    }

    /* Grouped View Styles */
    .group-item {
        border-bottom: 1px solid var(--border-color);
        overflow: hidden;
    }
    .group-item:last-child {
        border-bottom: none;
    }
    .group-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        cursor: pointer;
        background-color: var(--title-bar-bg);
        user-select: none;
        transition: background-color 0.15s ease;
    }
    .group-header:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .group-expander {
        font-size: 0.7em;
        width: 10px;
        text-align: center;
    }
    .group-title {
        font-weight: 500;
        flex-grow: 1;
    }
    .group-count {
        font-size: 0.8em;
        background-color: var(--taskbar-button-bg);
        padding: 2px 6px;
        border-radius: 10px;
        min-width: 12px;
        text-align: center;
    }
    .group-content {
        background-color: var(--window-bg);
        /* No padding here, notification items have their own */
    }

</style>

<div class="notification-center">
    <div class="header">
        <h3>Notifications</h3>
        <div class="view-switcher">
            <button class:active={currentView === 'chronological'} on:click={() => currentView = 'chronological'} title="List all notifications chronologically">
                List
            </button>
            <button class:active={currentView === 'grouped'} on:click={() => currentView = 'grouped'} title="Group notifications by window">
                Group
            </button>
        </div>
        <button on:click={clearHistory} title="Clear all notifications">Clear All</button>
    </div>
    <div class="history-list">
        {#if currentView === 'chronological'}
            {#each $notificationHistory as notification (notification.id)}
                <div class="notification-item" on:click={() => handleItemClick(notification)} title="Click to focus window">
                    <div class="icon" title={notification.icon}>{notification.icon}</div>
                    <div class="content">
                        <p class="summary" title={notification.summary}>{notification.summary}</p>
                        <span class="timestamp">{formatTime(notification.timestamp)}</span>
                    </div>
                </div>
            {:else}
                <div class="empty-state">
                    <div class="icon">🔕</div>
                    <p>All caught up!</p>
                </div>
            {/each}
        {:else if currentView === 'grouped'}
            {#each groupedNotifications as group (group.groupId)}
                <div class="group-item">
                    <div class="group-header" on:click={() => toggleGroup(group.groupId)}>
                        <span class="group-expander">{expandedGroups[group.groupId] ? '▼' : '►'}</span>
                        <span class="group-title">{group.title}</span>
                        <span class="group-count">{group.count}</span>
                    </div>
                    {#if expandedGroups[group.groupId]}
                        <div class="group-content" transition:slide|local>
                            {#each group.notifications as notification (notification.id)}
                                <div class="notification-item" on:click={() => handleItemClick(notification)} title="Click to focus window">
                                    <div class="icon" title={notification.icon}>{notification.icon}</div>
                                    <div class="content">
                                        <p class="summary" title={notification.summary}>{notification.summary}</p>
                                        <span class="timestamp">{formatTime(notification.timestamp)}</span>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            {:else}
                <div class="empty-state">
                    <div class="icon">🔕</div>
                    <p>All caught up!</p>
                </div>
            {/each}
        {/if}
    </div>
</div>