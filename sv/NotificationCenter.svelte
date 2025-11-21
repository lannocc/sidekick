<script>
    import { onMount, onDestroy, createEventDispatcher } from 'svelte';
    import { notificationHistory, unreadNoticeCount } from './desktop.js';
    import { windows } from './windows.js';

    const dispatch = createEventDispatcher();
    let self; // ref to the component's root element

    onMount(() => {
        // As per proposal, reset count on mount
        unreadNoticeCount.set(0);

        // Handle clicks outside the component to close it
        const handleClickOutside = (event) => {
            if (self && !self.contains(event.target) && !event.target.closest('.clock-button')) {
                 dispatch('close');
            }
        };
        
        // Use a timeout to avoid the initial click that opened it from immediately closing it
        setTimeout(() => window.addEventListener('click', handleClickOutside), 0);

        return () => {
            window.removeEventListener('click', handleClickOutside);
        };
    });

    function handleItemClick(notification) {
        windows.focusWindow(notification.groupId);
        windows.setActiveTab(notification.groupId, notification.tabId);
        dispatch('close');
    }

    function clearHistory() {
        notificationHistory.set([]);
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
        position: absolute;
        bottom: 45px; /* Position above the taskbar */
        left: 50%;
        transform: translateX(-50%);
        width: 350px;
        max-height: 400px;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        box-shadow: 0 -5px 15px rgba(0,0,0,0.2);
        z-index: 19000;
        display: flex;
        flex-direction: column;
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
    .history-list {
        overflow-y: auto;
        flex-grow: 1;
    }
    .notification-item {
        display: flex;
        padding: 10px 12px;
        border-bottom: 1px solid var(--border-color);
        cursor: pointer;
        transition: background-color 0.15s ease;
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
        font-style: italic;
    }
</style>

<div class="notification-center" bind:this={self}>
    <div class="header">
        <h3>Notifications</h3>
        <button on:click={clearHistory} title="Clear all notifications">Clear All</button>
    </div>
    <div class="history-list">
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
                <p>No notifications.</p>
            </div>
        {/each}
    </div>
</div>
