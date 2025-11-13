<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy, afterUpdate, tick } from 'svelte';
    import { consoleCommands, privateMessages } from './ioskEvents.js';
    import { windows } from './windows.js';

    export let id;
    export let consoleId;
    export let localUser;
    export let remoteUser;

    let messages = [];
    let inputMessage = '';
    let messageContainer;
    let inputEl;
    let shouldScroll = true;

    // --- FIX START ---
    // Reactive function to get the display name (username part) from a full address
    const getDisplayName = (fullAddress) => (fullAddress || '').split('.')[0];
    // --- FIX END ---

    // Update window store with props for Dash saving
    $: if (id !== undefined) {
        windows.updateTabProps(id, { consoleId, localUser, remoteUser });
    }

    const ansiCodeToCssVar = {
        '30': 'var(--ansi-black)', '31': 'var(--ansi-red)', '32': 'var(--ansi-green)', '33': 'var(--ansi-yellow)',
        '34': 'var(--ansi-blue)', '35': 'var(--ansi-magenta)', '36': 'var(--ansi-cyan)', '37': 'var(--ansi-white)',
        '90': 'var(--ansi-bright-black)', '91': 'var(--ansi-bright-red)', '92': 'var(--ansi-bright-green)', '93': 'var(--ansi-bright-yellow)',
        '94': 'var(--ansi-bright-blue)', '95': 'var(--ansi-bright-magenta)', '96': 'var(--ansi-bright-cyan)', '97': 'var(--ansi-bright-white)',
    };

    function parseAnsi(text) {
        if (typeof text !== 'string') return '';
        const ansiRegex = /\u001b\[(\d+)m/g;
        let openSpan = false;

        let sanitizedText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');

        let html = sanitizedText.replace(ansiRegex, (match, code) => {
            let newHtml = '';
            if (openSpan) {
                newHtml += '</span>';
                openSpan = false;
            }
            if (code === '0') {
                // Reset code, just close the span
            } else if (ansiCodeToCssVar[code]) {
                newHtml += `<span style="color: ${ansiCodeToCssVar[code]}">`;
                openSpan = true;
            }
            return newHtml;
        });

        if (openSpan) {
            html += '</span>';
        }
        return html;
    }

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
    /* Copied from IoskConsole.svelte for color consistency */
    :global(:root) {
        --ansi-black: #2c3e50;
        --ansi-red: #c0392b;
        --ansi-green: #27ae60;
        --ansi-yellow: #f1c40f;
        --ansi-blue: #2980b9;
        --ansi-magenta: #8e44ad;
        --ansi-cyan: #16a085;
        --ansi-white: #bdc3c7;
        --ansi-bright-black: #95a5a6;
        --ansi-bright-red: #e74c3c;
        --ansi-bright-green: #2ecc71;
        --ansi-bright-yellow: #f39c12;
        --ansi-bright-blue: #3498db;
        --ansi-bright-magenta: #9b59b6;
        --ansi-bright-cyan: #1abc9c;
        --ansi-bright-white: #ecf0f1;
    }
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
            <input
                type="text"
                bind:this={inputEl}
                bind:value={inputMessage}
                placeholder="Type your message..."
                spellcheck="false"
                disabled={!consoleId}
            />
        </form>
    </div>
</div>

