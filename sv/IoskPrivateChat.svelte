<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate } from 'svelte';
    import { consoleCommands, privateMessages } from './ioskEvents.js';
    import { windows } from './windows.js';

    export let id;
    export let consoleId;
    export let localUser;
    export let remoteUser;

    let messages = [];
    let inputMessage = '';
    let messageContainer;
    let shouldScroll = true;

    // The remote user's display name (without device/host info if local)
    $: remoteUserDisplay = remoteUser.includes('.') ? remoteUser : remoteUser.split('.')[0];
    $: localUserDisplay = localUser.split('.')[0];

    // Update window store with props for Dash saving
    $: if (id !== undefined) {
        windows.updateWindowProps(id, { consoleId, localUser, remoteUser });
    }

    function handleMessage(message) {
        if (!message) return;
        
        const isForThisWindow =
            (message.from === remoteUser && message.to === localUser) ||
            (message.from === localUser && message.to === remoteUser);

        if (isForThisWindow) {
            messages = [...messages, message];
            shouldScroll = true;
        }
    }

    let unsubscribe;
    onMount(() => {
        unsubscribe = privateMessages.subscribe(handleMessage);
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
        if (!trimmedMessage) return;

        // Command to be sent via the console
        const command = `@${remoteUser} ${trimmedMessage}`;
        consoleCommands.set({ consoleId, command, timestamp: Date.now() });

        // Post to our own bus for local display
        privateMessages.set({
            from: localUser,
            to: remoteUser,
            content: trimmedMessage,
            timestamp: Date.now()
        });

        inputMessage = '';
    }
</script>

<style>
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-size: 14px;
        user-select: text;
    }
    .messages {
        flex-grow: 1;
        overflow-y: auto;
        padding: 8px;
    }
    .message {
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .message-header {
        font-weight: bold;
        margin-bottom: 2px;
    }
    .message-content {
        white-space: pre-wrap;
        word-break: break-word;
    }
    .input-area {
        display: flex;
        padding: 8px;
        border-top: 1px solid var(--border-color);
        background-color: var(--title-bar-bg);
    }
    .input-area input {
        flex-grow: 1;
        background-color: var(--console-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 5px 8px;
        border-radius: 3px;
        font-family: inherit;
        font-size: inherit;
        outline: none;
    }
</style>

<div class="chat-container">
    <div class="messages" bind:this={messageContainer}>
        {#each messages as msg (msg.timestamp)}
            <div class="message">
                <div class="message-header" style="color: {msg.from === localUser ? 'var(--ansi-bright-white)' : 'var(--ansi-cyan)'}">
                    {msg.from === localUser ? localUserDisplay : remoteUserDisplay}:
                </div>
                <div class="message-content">{msg.content}</div>
            </div>
        {/each}
    </div>
    <div class="input-area">
        <form on:submit|preventDefault={sendMessage} style="width: 100%;">
            <input
                type="text"
                bind:value={inputMessage}
                placeholder="Type your message..."
                spellcheck="false"
                disabled={!consoleId}
            />
        </form>
    </div>
</div>