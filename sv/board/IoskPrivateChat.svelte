<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate, tick } from 'svelte';
    import { get } from 'svelte/store';
    import { sendCommand, privateMessages } from '../iosk.js';
    import { windows } from '../windows.js';
    import { parseAnsi, stripAnsi } from '../ansi.js';

    export let id;
    export let groupId;
    export let connectionId;
    export let localUser;
    export let remoteUser;

    let messages = [];
    let inputMessage = '';
    let messageContainer;
    let inputEl;
    let shouldScroll = true;

    // Reactive function to get the display name (username part) from a full address
    const getDisplayName = (fullAddress) => (fullAddress || '').split('.')[0];

    // Update window store with props for Dash saving
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { connectionId, localUser, remoteUser });
    }

    // Reactive logic to find console after a Dash restore is no longer needed
    // with the persistent, centralized connection management system.

    async function focusInput() {
        await tick();
        inputEl?.focus();
    }

    function handleClickOnMessages() {
        if (window.getSelection().isCollapsed) {
            focusInput();
        }
    }

    function handleMessage(message) {
        if (!message || message.connectionId !== connectionId) return;

        const isForThisWindow =
            (message.from === remoteUser && message.to === localUser) ||
            (message.from === localUser && message.to === remoteUser);

        if (isForThisWindow) {
            messages = [...messages, message];
            shouldScroll = true;

            // SENTINEL NOTIFICATION: Trigger for new incoming messages on an inactive window
            if (message.from !== localUser) {
                const isWindowActive = get(windows).find(w => w.id === groupId)?.isActive;
                if (!isWindowActive) {
                    const sender = getDisplayName(message.from);
                    const content = stripAnsi(message.content);
                    windows.notifyActivity(groupId, id, { summary: `${sender}: ${content}` });
                }
            }
        }
    }

    let unsubscribe;
    onMount(() => {
        unsubscribe = privateMessages.subscribe(handleMessage);
        focusInput();
    });

    onDestroy(() => {
        if (unsubscribe) unsubscribe();
    });

    afterUpdate(() => {
        if (shouldScroll && messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
            shouldScroll = false;
        }
    });

    function sendMessage() {
        const trimmedMessage = inputMessage.trim();
        if (!trimmedMessage || !connectionId) return;

        const command = `@${remoteUser} ${trimmedMessage}`;
        sendCommand(connectionId, command);

        // Local echo of the message is removed. The central connection hub will receive
        // the message back from the server and update the `privateMessages` store,
        // making the server the single source of truth.

        inputMessage = '';
    }
</script>

<style>
    .chat-container { display: flex; flex-direction: column; height: 100%; font-family: monospace; background-color: var(--console-bg); color: var(--console-text); font-size: 14px; user-select: text; }
    .messages { flex-grow: 1; overflow-y: auto; padding: 8px; }
    .message { margin-bottom: 8px; line-height: 1.4; }
    .message-header { font-weight: bold; margin-bottom: 2px; }
    .message-content { white-space: pre-wrap; word-break: break-word; }
    .input-area { display: flex; padding: 8px; border-top: 1px solid var(--border-color); background-color: var(--title-bar-bg); }
    .input-area input { flex-grow: 1; background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 5px 8px; border-radius: 3px; font-family: inherit; font-size: inherit; outline: none; }
</style>

<div class="chat-container">
    <div class="messages" bind:this={messageContainer} on:click={handleClickOnMessages}>
        {#each messages as msg (msg.timestamp)}
            <div class="message">
                <div class="message-header" style="color: {msg.from === localUser ? 'var(--ansi-bright-white)' : 'var(--ansi-cyan)'}">
                    {getDisplayName(msg.from)}:
                </div>
                <div class="message-content">{@html parseAnsi(msg.content)}</div>
            </div>
        {/each}
    </div>
    <div class="input-area" on:click={focusInput}>
        <form on:submit|preventDefault={sendMessage} style="width: 100%; display: flex;">
            <input type="text" bind:this={inputEl} bind:value={inputMessage} placeholder="Type your message..." spellcheck="false" disabled={!connectionId} />
        </form>
    </div>
</div>