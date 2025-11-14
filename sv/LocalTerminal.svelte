<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { connect, sendMessage, terminalData, connectionStatus } from './localAgentStore.js';

    // Mocking xterm.js for this implementation, as it's an external dependency.
    // A real implementation would `import { Terminal } from 'xterm';` etc.
    class MockTerminal {
        constructor(options) { this.options = options; this.rows = 24; this.cols = 80; this._onData = () => {}; }
        open(element) { element.innerHTML = '<pre>xterm.js mock terminal. Requires installation.</pre><div class="mock-cursor">_</div>'; }
        loadAddon(addon) {}
        onData(callback) { this._onData = callback; }
        write(data) { console.log(`MockTerminal Write: ${data}`); }
        focus() {}
        dispose() {}
    }
    class MockFitAddon { fit() {} }

    export let isActive;

    let terminalEl;
    let term;
    let fitAddon;
    let initialTermOpenSent = false;

    let unsubscribeTerminalData;
    let unsubscribeStatus;

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
        const Terminal = MockTerminal;
        const FitAddon = MockFitAddon;

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
    .terminal-container :global(pre) {
        margin: 0;
    }
    @keyframes blink {
        50% { opacity: 0; }
    }
    .terminal-container :global(.mock-cursor) {
        display: inline-block;
        animation: blink 1s step-end infinite;
        background: var(--console-text);
        width: 8px; /* Approx width of a char */
        height: 1em;
    }
</style>

<div class="terminal-container" bind:this={terminalEl}></div>

