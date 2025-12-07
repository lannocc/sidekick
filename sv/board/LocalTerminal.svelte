<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { sendMessage, terminalData, connectionStatus, terminalExit } from '../local.js';
    import { dragRequest, windows } from '../windows.js';

    import { Terminal } from '@xterm/xterm';
    import { FitAddon } from '@xterm/addon-fit';
    import 'xterm/css/xterm.css';

    export let id; // Tab ID, required for Sentinel
    export let isActive;
    export let groupId;
    export let maximized;
    export let initialPath = null;

    let terminalEl;
    let term;
    let fitAddon;
    let initialTermOpenSent = false;
    let canNotify = true; // For throttling Sentinel notifications

    let unsubscribeTerminalData;
    let unsubscribeStatus;
    let unsubscribeTerminalExit;

    function handleMouseDown(event) {
        if ((event.altKey || event.metaKey) && event.button === 0 && !maximized) {
            event.preventDefault();
            event.stopPropagation();

            dragRequest.set({
                id: groupId,
                type: 'move',
                direction: null,
                clientX: event.clientX,
                clientY: event.clientY,
            });
        }
    }

    function resizeTerminal() {
        if (fitAddon && term) {
            try {
                fitAddon.fit();
                sendMessage({ type: 'term_resize', term_id: id, rows: term.rows, cols: term.cols });
            } catch (e) {
                // can happen if not fully visible
            }
        }
    }

    onMount(() => {
        term = new Terminal({
            cursorBlink: true,
            theme: {
                background: 'var(--console-bg)',
                foreground: 'var(--console-text)',
            }
        });
        fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(terminalEl);

        term.onData(data => {
            sendMessage({ type: 'term_data', term_id: id, data: data });
        });

        unsubscribeStatus = connectionStatus.subscribe(status => {
            if (status === 'connected' && !initialTermOpenSent) {
                const openMessage = { type: 'term_open', term_id: id };
                if (initialPath) {
                    openMessage.path = initialPath;
                }
                sendMessage(openMessage);
                initialTermOpenSent = true;
                resizeTerminal();
                term.focus();
            } else if (status === 'disconnected') {
                term.write('\r\n\n--- CONNECTION CLOSED ---\r\n');
            } else if (status === 'error') {
                 term.write('\r\n\n--- CONNECTION ERROR ---\r\n');
            }
        });

        unsubscribeTerminalData = terminalData.subscribe(msg => {
            if (msg && term && msg.term_id === id) {
                // SENTINEL INTEGRATION
                if (canNotify && !get(windows).find(w => w.id === groupId)?.isActive) {
                    windows.notifyActivity(groupId, id, { summary: 'New terminal output' });
                    canNotify = false;
                    setTimeout(() => { canNotify = true; }, 3000); // 3-second cooldown
                }
                term.write(msg.data);
            }
        });

        unsubscribeTerminalExit = terminalExit.subscribe(msg => {
            if (msg && msg.term_id === id) {
                windows.removeTab(groupId, id);
            }
        });

        const resizeObserver = new ResizeObserver(() => {
            resizeTerminal();
        });
        resizeObserver.observe(terminalEl.parentElement);

        return () => {
            sendMessage({ type: 'term_close', term_id: id });
            if (unsubscribeTerminalData) unsubscribeTerminalData();
            if (unsubscribeStatus) unsubscribeStatus();
            if (unsubscribeTerminalExit) unsubscribeTerminalExit();
            resizeObserver.disconnect();
            term.dispose();
        };
    });

    $: if (isActive && term) {
        term.focus();
    }
</script>

<style>
    .terminal-container {
        width: 100%;
        height: 100%;
        background-color: var(--console-bg);
        padding: 5px;
        box-sizing: border-box;
    }
</style>

<div class="terminal-container" bind:this={terminalEl} on:mousedown|capture={handleMouseDown}></div>
