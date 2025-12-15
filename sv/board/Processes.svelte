<script>
    import { onMount, onDestroy } from 'svelte';
    import { 
        runningProcesses,
        processOutput,
        stopProcess,
        killProcess,
        pauseProcess,
        resumeProcess,
        sendProcessStdin,
        listRunningProcesses,
        connectionStatus,
        requestedPid
    } from '../bridge.js';
    import { newLocalFileViewer, showBoxesAndSelect } from '../apps.js';
    import { parseAnsi } from '../ansi.js';

    export let initialSelectedPid = null;

    let selectedPid = null;
    let selectedProcess = null;
    let processLogs = {}; // pid -> { lines: string[], element: HTMLElement }

    let leftPanelWidth = 300;
    let isResizing = false;

    // --- State and logic for uptime calculation ---
    let uptime = 'N/A';
    let uptimeInterval = null;

    function formatUptime(startTime) {
        if (!startTime) return 'N/A';
        const start = new Date(startTime);
        const now = new Date();
        let seconds = Math.floor((now - start) / 1000);
        let minutes = Math.floor(seconds / 60);
        let hours = Math.floor(minutes / 60);
        let days = Math.floor(hours / 24);

        hours %= 24;
        minutes %= 60;
        seconds %= 60;

        return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    function calculateUptime() {
        if (selectedProcess && selectedProcess.status === 'running') {
            uptime = formatUptime(selectedProcess.start_time);
        } else {
            uptime = 'N/A';
        }
    }

    // --- Reactive updates based on selections and incoming data ---

    $: if (selectedPid !== null) {
        selectedProcess = $runningProcesses.find(p => p.pid === selectedPid) || null;
        if (!processLogs[selectedPid]) {
            processLogs[selectedPid] = { lines: [], element: null };
        }
    } else {
        selectedProcess = null;
    }

    $: if ($processOutput) {
        const { pid, data, stream } = $processOutput;
        if (processLogs[pid]) {
            const processedData = parseAnsi(data);
            const coloredData = `<span class="log-${stream}">${processedData}</span>`;
            processLogs[pid].lines = [...processLogs[pid].lines, coloredData];
            setTimeout(() => {
                const el = processLogs[pid].element;
                if (el && (el.scrollHeight - el.scrollTop - el.clientHeight < 100)) {
                    el.scrollTop = el.scrollHeight;
                }
            }, 0);
        }
    }

    $: {
        calculateUptime();
        if (selectedProcess && selectedProcess.status === 'running' && !uptimeInterval) {
            uptimeInterval = setInterval(calculateUptime, 1000);
        } else if ((!selectedProcess || selectedProcess.status !== 'running') && uptimeInterval) {
            clearInterval(uptimeInterval);
            uptimeInterval = null;
            if (selectedProcess?.status === 'stopped') uptime = 'Stopped';
        }
    }

    // --- Stdin Input ---
    let stdinInput = '';
    function handleStdinSubmit() {
        if (!selectedPid || !stdinInput) return;
        sendProcessStdin(selectedPid, stdinInput + '\n'); // Append newline for terminal-like behavior
        stdinInput = '';
    }

    // --- Resizer logic ---
    function onMouseDown(event) { isResizing = true; }
    function onMouseMove(event) {
        if (isResizing) {
            leftPanelWidth += event.movementX;
            if (leftPanelWidth < 200) leftPanelWidth = 200;
            if (leftPanelWidth > 800) leftPanelWidth = 800;
        }
    }
    function onMouseUp() { isResizing = false; }

    const unsubscribeRequestedPid = requestedPid.subscribe(pid => {
        if (pid !== null) {
            selectedPid = pid;
            requestedPid.set(null); // Consume the request
        }
    });

    onMount(() => {
        if (initialSelectedPid) {
            selectedPid = initialSelectedPid;
        }
        listRunningProcesses();
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    });

    onDestroy(() => {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        if (uptimeInterval) clearInterval(uptimeInterval);
        unsubscribeRequestedPid();
    });
</script>

<style>
    .manager-container { display: flex; height: 100%; background-color: transparent; color: var(--text-color); }
    .manager-container.resizing { cursor: col-resize; user-select: none; }
    .left-panel { min-width: 200px; max-width: 800px; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; overflow-y: auto; background-color: hsla(0, 0%, 50%, 0.1); border-radius: 8px 0 0 8px; flex-shrink: 0; }
    .resizer { width: 5px; cursor: col-resize; background: transparent; flex-shrink: 0; }
    .resizer:hover, .manager-container.resizing .resizer { background-color: var(--item-selected-bg); }
    .proc-list-item { display: grid; grid-template-columns: auto 1fr; gap: 4px 8px; padding: 10px; cursor: pointer; border-left: 3px solid transparent; align-items: center; }
    .proc-list-item:hover { background-color: var(--item-hover-bg); }
    .proc-list-item.selected { font-weight: bold; background-color: var(--item-selected-bg); border-left-color: var(--accent-color); }
    .status-indicator { grid-row: 1 / span 2; width: 10px; height: 10px; border-radius: 50%; }
    .status-running { background-color: #2ecc71; }
    .status-stopped { background-color: #e74c3c; }
    .status-paused { background-color: #f39c12; }
    .status-error { background-color: #9b59b6; }
    .proc-name { font-weight: bold; }
    .proc-details { font-size: 0.8em; color: var(--text-color-light); font-family: monospace; }
    .right-panel { flex-grow: 1; padding: 16px; display: flex; flex-direction: column; gap: 16px; overflow: hidden; }
    .no-selection { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-color-light); font-style: italic; font-size: 1.2em; }
    .details-grid { display: grid; grid-template-columns: auto 1fr; gap: 8px 16px; align-items: center; }
    .details-grid dt { font-weight: bold; color: var(--text-color-light); justify-self: end; }
    .details-grid dd { font-family: monospace; background: var(--input-bg); padding: 4px 8px; border-radius: 4px; user-select: text; word-break: break-all; }
    .details-grid dd.clickable { cursor: pointer; color: var(--accent-color); }
    .details-grid dd.clickable:hover { text-decoration: underline; }
    .controls { display: flex; gap: 8px; border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); padding: 12px 0; }
    .controls button { padding: 6px 14px; border: 1px solid var(--button-border-color); background-color: var(--button-bg); color: var(--text-color); border-radius: 4px; cursor: pointer; font-weight: bold; transition: background-color 0.2s; }
    .controls button:hover:not(:disabled) { background-color: var(--button-hover-bg); }
    .controls button:disabled { opacity: 0.5; cursor: not-allowed; }
    .controls .kill-btn:not(:disabled) { background-color: #c0392b; border-color: #e74c3c; color: white; }
    .controls .kill-btn:hover:not(:disabled) { background-color: #e74c3c; }
    .terminal-container { flex-grow: 1; display: flex; flex-direction: column; background: #1e1e1e; border-radius: 6px; overflow: hidden; border: 1px solid var(--border-color); }
    .terminal-view { flex-grow: 1; overflow-y: auto; padding: 10px; font-family: 'Courier New', Courier, monospace; font-size: 14px; color: #ccc; white-space: pre-wrap; word-wrap: break-word; line-height: 1.4; }
    .terminal-view :global(.log-stderr) { color: #f07178; }
    .terminal-view :global(.log-stdout) { color: #ccc; }
    .stdin-form { display: flex; border-top: 1px solid var(--border-color); }
    .stdin-form input { flex-grow: 1; background: transparent; border: none; color: #ccc; padding: 8px 10px; font-family: inherit; font-size: inherit; outline: none; }
    .disconnected-overlay { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 8px; color: var(--text-color-light); background-color: hsla(0, 0%, 20%, 0.5); font-size: 1.5em; font-weight: bold; border-radius: 8px; }
</style>

{#if $connectionStatus === 'connected'}
<div class="manager-container" class:resizing={isResizing}>
    <div class="left-panel" style:width="{leftPanelWidth}px">
        {#each $runningProcesses as proc (proc.id)}
            <div class="proc-list-item" class:selected={proc.pid === selectedPid} on:click={() => selectedPid = proc.pid}>
                <div class="status-indicator status-{proc.status}"></div>
                <div class="proc-name">{proc.box_name || proc.type}</div>
                <div class="proc-details">PID: {proc.pid} | {proc.status}</div>
            </div>
        {/each}
        {#if $runningProcesses.length === 0}
            <div class="no-selection" style="font-size: 0.9em; padding: 20px;">No managed processes are running.</div>
        {/if}
    </div>

    <div class="resizer" on:mousedown={onMouseDown}></div>

    <div class="right-panel">
        {#if selectedProcess}
            <dl class="details-grid">
                <dt>Box</dt>
                {#if selectedProcess.box_id != null}
                    <dd class="clickable" on:click={() => showBoxesAndSelect(selectedProcess.box_id)}>
                        {selectedProcess.box_name || 'N/A'}
                    </dd>
                {:else}
                    <dd>{selectedProcess.box_name || 'N/A'}</dd>
                {/if}
                <dt>PID</dt><dd>{selectedProcess.pid}</dd>
                <dt>Type</dt><dd>{selectedProcess.type}</dd>
                <dt>Status</dt><dd>{selectedProcess.status}</dd>
                <dt>Start Time</dt><dd>{new Date(selectedProcess.start_time).toLocaleString()}</dd>
                <dt>Uptime</dt><dd>{uptime}</dd>
                <dt>STDOUT Log</dt>
                <dd class="clickable" on:click={() => newLocalFileViewer({ path: selectedProcess.stdout_log_path })}>
                    {selectedProcess.stdout_log_path}
                </dd>
                <dt>STDERR Log</dt>
                <dd class="clickable" on:click={() => newLocalFileViewer({ path: selectedProcess.stderr_log_path })}>
                    {selectedProcess.stderr_log_path}
                </dd>
            </dl>
            <div class="controls">
                <button on:click={() => pauseProcess(selectedPid)} disabled={selectedProcess.status !== 'running' || $connectionStatus !== 'connected'}>Pause</button>
                <button on:click={() => resumeProcess(selectedPid)} disabled={selectedProcess.status !== 'paused' || $connectionStatus !== 'connected'}>Resume</button>
                <button on:click={() => stopProcess(selectedPid)} disabled={selectedProcess.status === 'stopped' || selectedProcess.status === 'error' || $connectionStatus !== 'connected'}>Terminate</button>
                <button on:click={() => killProcess(selectedPid)} disabled={selectedProcess.status === 'stopped' || selectedProcess.status === 'error' || $connectionStatus !== 'connected'} class="kill-btn">Kill</button>
            </div>
            <div class="terminal-container">
                <div class="terminal-view" bind:this={processLogs[selectedPid].element}>
                    {#if processLogs[selectedPid]}
                        {#each processLogs[selectedPid].lines as line, i (i)}
                            {@html line}
                        {/each}
                    {/if}
                </div>
                {#if selectedProcess.enable_stdin && selectedProcess.status === 'running'}
                    <form class="stdin-form" on:submit|preventDefault={handleStdinSubmit}>
                        <input type="text" bind:value={stdinInput} placeholder="Send to stdin and press Enter..." autocomplete="off" spellcheck="false" disabled={$connectionStatus !== 'connected'}>
                    </form>
                {/if}
            </div>
        {:else}
            <div class="no-selection">Select a process to view details.</div>
        {/if}
    </div>
</div>
{:else}
    <div class="disconnected-overlay">
        <span>SKYBRIDGE REQUIRED</span>
        <span style="font-size: 0.7em; font-weight: normal; text-transform: capitalize;">Connection Status: {$connectionStatus}</span>
    </div>
{/if}