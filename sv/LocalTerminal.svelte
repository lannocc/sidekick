<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { connect, sendMessage, terminalData, connectionStatus } from './localAgentStore.js';
    import { dragRequest } from './windows.js';

    import { Terminal } from '@xterm/xterm';
    import { FitAddon } from '@xterm/addon-fit';
    import 'xterm/css/xterm.css';

    export let isActive;
    export let groupId;
    export let maximized;

    let terminalEl;
    let term;
    let fitAddon;
    let initialTermOpenSent = false;

    let unsubscribeTerminalData;
    let unsubscribeStatus;

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
                sendMessage({ type: 'term_resize', rows: term.rows, cols: term.cols });
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
            sendMessage({ type: 'term_data', data: data });
        });

        connect();

        unsubscribeStatus = connectionStatus.subscribe(status => {
            if (status === 'connected' && !initialTermOpenSent) {
                sendMessage({ type: 'term_open' });
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
            if (msg && term) {
                term.write(msg.data);
            }
        });

        const resizeObserver = new ResizeObserver(() => {
            resizeTerminal();
        });
        resizeObserver.observe(terminalEl.parentElement);

        return () => {
            if (unsubscribeTerminalData) unsubscribeTerminalData();
            if (unsubscribeStatus) unsubscribeStatus();
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
