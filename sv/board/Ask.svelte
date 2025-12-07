<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { sendMessage, askOutput, askError, askExit, connectionStatus, askStatsResponse } from '../local.js';
    import { newLocalFileExplorer, windows } from '../windows.js';
    import { fileSelection } from './iosk.js';

    export let id; // tab id
    export let groupId;
    export let initialFiles = [];

    let askId = `ask-${id}-${Date.now()}`;
    let files = initialFiles;
    let promptText = '';
    let options = {
        use_openai: false,
        work: false,
        screenshot: false,
        model: '-2', // default
    };
    let output = [];
    let isRunning = false;
    let exitCode = null;
    let connectionState = 'disconnected';

    // New state for stats
    let totalBytes = 0;
    let totalTokens = 0;
    let isCalculating = false;
    let calculationRequestNonce = 0;

    let unsubscribeOutput, unsubscribeError, unsubscribeExit, unsubscribeStatus, unsubscribeSelection, unsubscribeStats;
    let outputEl;
    let debounceTimeout;

    function scrollToBottom() {
        if (outputEl) {
            outputEl.scrollTop = outputEl.scrollHeight;
        }
    }
    
    function calculateStats() {
        if (connectionState !== 'connected') {
            totalBytes = 0;
            totalTokens = 0;
            isCalculating = false;
            return;
        }
        isCalculating = true;
        calculationRequestNonce = Date.now();
        sendMessage({
            type: 'ask_stats',
            prompt: promptText,
            files,
            nonce: calculationRequestNonce,
        });
    }

    // Reactive block for stats calculation
    $: {
        if (connectionState === 'connected' && (promptText || files.length > 0)) {
            clearTimeout(debounceTimeout);
            isCalculating = true; // Show "calculating" immediately
            debounceTimeout = setTimeout(calculateStats, 500); // 500ms debounce
        } else {
            clearTimeout(debounceTimeout);
            totalBytes = 0;
            totalTokens = 0;
            isCalculating = false;
        }
    }

    onMount(() => {
        unsubscribeStatus = connectionStatus.subscribe(s => {
            connectionState = s;
            if (s === 'connected') {
                calculateStats(); // Calculate on connect if there's initial data
            }
        });

        unsubscribeOutput = askOutput.subscribe(msg => {
            if (msg && msg.askId === askId) {
                output = [...output, { stream: msg.stream, data: msg.data }];
                setTimeout(scrollToBottom, 0);
            }
        });
        unsubscribeError = askError.subscribe(msg => {
            if (msg && msg.askId === askId) {
                output = [...output, { stream: 'stderr', data: `[ERROR] ${msg.data}` }];
                setTimeout(scrollToBottom, 0);
            }
        });
        unsubscribeExit = askExit.subscribe(msg => {
            if (msg && msg.askId === askId) {
                isRunning = false;
                exitCode = msg.code;
                output = [...output, { stream: 'system', data: `--- Process finished with exit code ${msg.code} ---` }];
                
                // SENTINEL INTEGRATION
                if (!get(windows).find(w => w.id === groupId)?.isActive) {
                    windows.notifyActivity(groupId, id, { summary: `Ask task finished with exit code ${msg.code}` });
                }

                setTimeout(scrollToBottom, 0);
            }
        });
        
        unsubscribeStats = askStatsResponse.subscribe(msg => {
            if (msg && msg.nonce === calculationRequestNonce) {
                totalBytes = msg.bytes;
                totalTokens = msg.tokens;
                isCalculating = false;
            }
        });

        unsubscribeSelection = fileSelection.subscribe(selection => {
            if (selection && selection.targetId === askId) {
                const newFile = selection.path;
                if (newFile && !files.includes(newFile)) {
                    files = [...files, newFile];
                }
                fileSelection.set(null); // Reset store to avoid re-triggering
            }
        });
    });

    onDestroy(() => {
        if (unsubscribeOutput) unsubscribeOutput();
        if (unsubscribeError) unsubscribeError();
        if (unsubscribeExit) unsubscribeExit();
        if (unsubscribeStatus) unsubscribeStatus();
        if (unsubscribeSelection) unsubscribeSelection();
        if (unsubscribeStats) unsubscribeStats();
        clearTimeout(debounceTimeout);
    });

    function runAsk() {
        if (isRunning || connectionState !== 'connected') return;
        isRunning = true;
        output = [];
        exitCode = null;

        sendMessage({
            type: 'sk_ask',
            askId,
            prompt: promptText,
            files,
            options,
        });
    }

    function addFile() {
        newLocalFileExplorer({ title: 'Select Path for Ask', pickerTargetId: askId });
    }

    function removeFile(fileToRemove) {
        files = files.filter(f => f !== fileToRemove);
    }
</script>

<style>
    .ask-container { display: flex; height: 100%; font-family: monospace; background-color: var(--console-bg); color: var(--console-text); }
    .sidebar { width: 280px; padding: 10px; border-left: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 15px; overflow-y: auto; flex-shrink: 0; }
    .main-content { flex-grow: 1; display: flex; flex-direction: column; }
    .prompt-area { flex-shrink: 0; padding: 10px; border-bottom: 1px solid var(--border-color); }
    .prompt-area textarea { width: 100%; height: 120px; background-color: var(--window-bg); color: var(--title-bar-text); border: 1px solid var(--border-color); resize: vertical; padding: 5px; }
    .output-area { flex-grow: 1; padding: 10px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
    .output-line.stderr { color: var(--ansi-red); }
    .output-line.system { color: var(--ansi-yellow); }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 8px; margin: 0; }
    legend { color: var(--title-bar-text); padding: 0 5px; font-size: 0.9em; }
    label { display: flex; align-items: center; gap: 8px; font-size: 0.9em; }
    .file-list { list-style: none; padding: 0; margin: 0; max-height: 150px; overflow-y: auto; border: 1px solid var(--border-color); background-color: var(--window-bg); }
    .file-item { display: flex; justify-content: space-between; align-items: center; padding: 4px; border-bottom: 1px solid var(--border-color); }
    .file-item:last-child { border-bottom: none; }
    .file-item button { background: none; border: none; color: #e74c3c; cursor: pointer; font-size: 1.2em; }
    .file-controls { display: flex; justify-content: flex-end; }
    .file-controls button { font-size: 0.8em; padding: 2px 5px; }
    .run-button { width: 100%; padding: 10px; font-size: 1.2em; background-color: #27c93f; color: white; border: 1px solid #1a9c2a; border-radius: 4px; cursor: pointer; margin-top: auto; }
    .run-button:disabled { background-color: #95a5a6; cursor: not-allowed; }
    .stats-container { display: flex; flex-direction: column; gap: 5px; font-size: 0.9em; }
    .stat-item { display: flex; justify-content: space-between; align-items: center; }
    .calculating-text { font-style: italic; color: #7f8c8d; }
</style>

<div class="ask-container">
    <div class="main-content">
        <div class="prompt-area">
            <textarea placeholder="Enter your prompt here... (this will be piped to the command's stdin)" bind:value={promptText}></textarea>
        </div>
        <div class="output-area" bind:this={outputEl}>
            {#each output as line}
                <div class="output-line" class:stderr={line.stream === 'stderr'} class:system={line.stream === 'system'}>{line.data}</div>
            {/each}
        </div>
    </div>
    <div class="sidebar">
        <fieldset>
            <legend>Model</legend>
            <label><input type="radio" bind:group={options.model} value="-1"> Quick 1 (Flash/Mini)</label>
            <label><input type="radio" bind:group={options.model} value="-2"> Quick 2 (Flash/Mini)</label>
            <label><input type="radio" bind:group={options.model} value="-3"> Smart (Pro/GPT-5)</label>
        </fieldset>
        <fieldset>
            <legend>Options</legend>
            <label><input type="checkbox" bind:checked={options.use_openai}> Use OpenAI</label>
            <label><input type="checkbox" bind:checked={options.work}> Work on files (-w)</label>
            <label><input type="checkbox" bind:checked={options.screenshot}> Take screenshot (-s)</label>
        </fieldset>
        <fieldset>
            <legend>Attachments</legend>
            <ul class="file-list">
                {#each files as file (file)}
                    <li class="file-item">
                        <span title={file}>{file.split('/').pop() || file}</span>
                        <button on:click={() => removeFile(file)}>&times;</button>
                    </li>
                {:else}
                    <li style="padding: 4px; font-style: italic; color: #7f8c8d;">No files attached.</li>
                {/each}
            </ul>
            <div class="file-controls">
                <button on:click={addFile}>Add Path...</button>
            </div>
        </fieldset>

        <fieldset>
            <legend>Totals</legend>
            <div class="stats-container">
                {#if isCalculating}
                    <span class="calculating-text">Calculating...</span>
                {:else}
                    <div class="stat-item">
                        <span>Bytes:</span>
                        <span>{totalBytes.toLocaleString()}</span>
                    </div>
                    <div class="stat-item">
                        <span>Tokens:</span>
                        <span>{totalTokens.toLocaleString()}</span>
                    </div>
                {/if}
            </div>
        </fieldset>

        <button class="run-button" on:click={runAsk} disabled={isRunning || connectionState !== 'connected'}>
            {#if connectionState !== 'connected'}
                Disconnected
            {:else if isRunning}
                Running...
            {:else}
                Ask
            {/if}
        </button>
    </div>
</div>
