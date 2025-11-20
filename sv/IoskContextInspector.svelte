<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onDestroy } from 'svelte';
    import { contextUpdates } from './ioskEvents.js';
    import { windows } from './windows.js';
    import IoskContextInspector from './IoskContextInspector.svelte';

    // --- Component Props ---
    export let groupId; // The window group ID for this component instance
    export let consoleId; // The console tab ID this inspector is linked to
    export let targetUser; // The user whose context is being inspected
    export let consoleWs; // Reference to the console's WebSocket for unsubscribing
    export let isDetached = false; // Is this a popped-out view?
    export let detachedView = ''; // If so, which view to display?
    
    // If this component is rendered inline via <svelte:self>, contextData is passed directly.
    // If it's a top-level window, it will be populated by the store subscription.
    export let contextData = null;

    // --- State for the main inspector window ---
    let activeTab = 'overview';
    // State for tracking detached (popped-out) tabs
    let detachedTabs = {
        overview: null,
        environment: null,
        history: null,
        telemetry: null,
        preamble: null,
        memoryBanks: null,
        prompts: null,
        postamble: null,
        json: null,
    };
    
    // --- Data structure for rendering tab rows ---
    const tabRows = [
        [
            { id: 'overview', name: 'Overview' },
            { id: 'environment', name: 'Environment' },
            { id: 'history', name: 'Commands' },
            { id: 'telemetry', name: 'Telemetry' },
        ],
        [
            { id: 'preamble', name: 'Preamble' },
            { id: 'memoryBanks', name: 'Banks' },
            { id: 'prompts', name: 'Prompts' },
            { id: 'postamble', name: 'Postamble' },
        ],
        [
            { id: 'json', name: 'JSON' },
        ]
    ];


    // --- State for Token Telemetry ---
    let tokenTooltip = { visible: false, x: 0, y: 0 };

    // --- State for collapsible sections ---
    let bankExpandedState = {};
    let promptExpandedState = {};

    // --- State for prompt management ---
    let selectedPrompts = new Set();


    const unsubscribeStore = contextUpdates.subscribe(update => {
        // FIX: Reverted to the simpler, working logic from the .bak file.
        // The new check for `consoleId` was preventing updates from being received.
        if (update && update.targetUser === targetUser) {
            if (update.type === 'full') {
                contextData = update.data;
            } else if (update.type === 'partial' && contextData) {
                // Merge partial updates into the existing context.
                // This creates a new object, triggering Svelte's reactivity.
                contextData = { ...contextData, ...update.data };
            }
        }
    });

    // Reactive statement to check if a detached window was closed or moved
    $: if (!isDetached && $windows) {
        // Create a map of tabId -> groupId for efficient lookup
        const allTabsToGroups = new Map($windows.flatMap(w => w.tabs.map(t => [t.id, w.id])));
        let changed = false;
        for (const tabName in detachedTabs) {
            const detachedInfo = detachedTabs[tabName];
            if (detachedInfo) { // detachedInfo is now { groupId, tabId }
                const currentGroupId = allTabsToGroups.get(detachedInfo.tabId);

                if (!currentGroupId) {
                    // The tab no longer exists, it must have been closed.
                    detachedTabs[tabName] = null;
                    changed = true;
                } else if (currentGroupId !== detachedInfo.groupId) {
                    // The tab has been moved to a new window group. Update our reference.
                    detachedTabs[tabName].groupId = currentGroupId;
                    changed = true; // IMPORTANT: Signal that an update happened
                }
            }
        }
        if (changed) {
            detachedTabs = detachedTabs; // Trigger reactivity
        }
    }

    // Reactive pruning of selected prompts if they disappear from the history
    $: if (contextData && contextData.aiContext && contextData.aiContext.sessionHistory) {
        const existingPromptNumbers = new Set(contextData.aiContext.sessionHistory.map(e => e.number));
        let changed = false;
        for (const selected of selectedPrompts) {
            if (!existingPromptNumbers.has(selected)) {
                selectedPrompts.delete(selected);
                changed = true;
            }
        }
        if (changed) {
            selectedPrompts = selectedPrompts; // Trigger reactivity
        }
    }

    onDestroy(() => {
        unsubscribeStore();
        // Only the main inspector window sends the unsubscribe message when it closes.
        // Detached windows are ephemeral views.
        if (!isDetached && consoleWs && consoleWs.readyState === WebSocket.OPEN) {
            consoleWs.send(JSON.stringify({ type: 'ui_context_unsubscribe', targetUser }));
        }
    });

    function popOutTab(viewName) {
        if (!contextData) return;
        // Find the display name for the title from our tabRows structure
        const tabInfo = tabRows.flat().find(t => t.id === viewName);
        const titleName = tabInfo ? tabInfo.name : (viewName.charAt(0).toUpperCase() + viewName.slice(1));
        
        const newWindow = windows.addWindow(IoskContextInspector, {
            title: `${titleName} - ${targetUser}`,
            consoleId: consoleId,
            targetUser: targetUser,
            consoleWs: consoleWs,
            isDetached: true,
            detachedView: viewName,
            width: 600,
            height: 500,
        });
        if (newWindow && newWindow.groupId) {
            detachedTabs[viewName] = { groupId: newWindow.groupId, tabId: newWindow.tabId };
            detachedTabs = detachedTabs;
        }
    }

    // --- Helper functions for telemetry display ---
    function abbreviateNumber(num) {
        if (num == null) return '';
        if (num < 1000) return num.toString();
        const suffixes = ["", "k", "m", "b", "t"];
        const i = Math.floor(Math.log10(num) / 3);
        let short = num / Math.pow(1000, i);
        let precision = 2;
        if (short >= 100) {
            precision = 0;
        } else if (short >= 10) {
            precision = 1;
        }
        // Using toFixed and then parseFloat to remove trailing zeros
        return parseFloat(short.toFixed(precision)) + suffixes[i];
    }

    // --- New event handlers for header controls ---
    function showTokenTooltip(event) {
        if (!contextData || !contextData.tokenStats) return;
        const rect = event.currentTarget.getBoundingClientRect();
        tokenTooltip = {
            visible: true,
            x: rect.right,
            y: rect.bottom + 5
        };
    }

    function hideTokenTooltip() {
        tokenTooltip = { ...tokenTooltip, visible: false };
    }

    function handleTokenClick() {
        if (isDetached) return;
        const info = detachedTabs['telemetry'];
        if (info) {
            windows.setActiveTab(info.groupId, info.tabId);
        } else {
            activeTab = 'telemetry';
        }
    }

    function togglePause() {
        if (!contextData || !contextData.isBot || !consoleWs || consoleWs.readyState !== WebSocket.OPEN) return;
        const command = contextData.isPaused ? `unpause ${targetUser}` : `pause ${targetUser}`;
        const commandToRun = `$ ${command}`;
        consoleWs.send(JSON.stringify({ type: 'client_input', data: commandToRun + '\n' }));
    }


    // --- Helper Functions (copied from .bak file) ---
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

    function formatBytes(bytes, decimals = 2) {
        if (bytes == null || bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function formatDate(isoString) {
        if (!isoString) return 'N/A';
        try {
            return new Date(isoString).toLocaleString();
        } catch (e) {
            return 'Invalid Date';
        }
    }

    // --- New helpers for collapsible views ---
    function getFirstLine(text) {
        if (!text || typeof text !== 'string') return '';
        const newlineIndex = text.indexOf('\n');
        return newlineIndex === -1 ? text : text.substring(0, newlineIndex);
    }

    function toggleAllBanks(expand) {
        if (!contextData || !contextData.aiContext || !contextData.aiContext.banks) return;
        const newState = {};
        for (const bank of contextData.aiContext.banks) {
            newState[bank.name] = expand;
        }
        bankExpandedState = newState;
    }

    function toggleAllPrompts(expand) {
        if (!contextData || !contextData.aiContext || !contextData.aiContext.sessionHistory) return;
        const newState = {};
        for (const entry of contextData.aiContext.sessionHistory) {
            newState[entry.number] = expand;
        }
        promptExpandedState = newState;
    }

    // --- New function for Prompt Analysis ---
    function analyzePrompt(originalContent) {
        if (typeof originalContent !== 'string') {
            return { type: 'unknown', content: '', prompt: null, strippedContent: '' };
        }

        // 1. Strip leading blank lines (or lines with only whitespace)
        const content = originalContent.replace(/^(\s*[\r\n])+/, '');

        // 2. Info message
        if (content.startsWith(':: ')) {
            return { type: 'info', content, strippedContent: content.substring(3), prompt: null };
        }

        // 3. Error message
        if (content.startsWith('!! ')) {
            return { type: 'error', content, strippedContent: content.substring(3), prompt: null };
        }

        // 4. Command
        const commandMatch = content.match(/^(\[.*?\] \$ )(.*)/s);
        if (commandMatch) {
            return { type: 'command', content, prompt: commandMatch[1], strippedContent: commandMatch[2] };
        }

        // 5. Comment
        const commentMatch = content.match(/^(\[.*?\] # )(.*)/s);
        if (commentMatch) {
            return { type: 'comment', content, prompt: commentMatch[1], strippedContent: commentMatch[2] };
        }

        // 6. Chat sent
        const chatSentMatch = content.match(/^(\[.*?\] >> )(.*)/s);
        if (chatSentMatch) {
            return { type: 'chat-sent', content, prompt: chatSentMatch[1], strippedContent: chatSentMatch[2] };
        }
        
        // 7. Chat received
        const chatReceivedMatch = content.match(/^(\[.*?\] << )(.*)/s);
        if (chatReceivedMatch) {
            return { type: 'chat-received', content, prompt: chatReceivedMatch[1], strippedContent: chatReceivedMatch[2] };
        }

        // Fallback for unknown prompt types
        return { type: 'unknown', content, strippedContent: content, prompt: null };
    }

    // --- New functions for Prompt Management ---
    function sendInspectorCommand(command) {
        if (!consoleWs || consoleWs.readyState !== WebSocket.OPEN) return;
        const user = contextData ? contextData.user : targetUser;
        consoleWs.send(JSON.stringify({ type: 'client_input', data: '$ su ' + user + ' ' + command + '\n' }));
    }

    function forgetSinglePrompt(number) {
        sendInspectorCommand(`forget ${number}`);
    }

    function togglePromptSelection(number) {
        if (selectedPrompts.has(number)) {
            selectedPrompts.delete(number);
        } else {
            selectedPrompts.add(number);
        }
        selectedPrompts = selectedPrompts; // trigger reactivity
    }

    function selectAllPrompts() {
        if (!contextData || !contextData.aiContext || !contextData.aiContext.sessionHistory) return;
        selectedPrompts = new Set(contextData.aiContext.sessionHistory.map(e => e.number));
    }

    function deselectAllPrompts() {
        selectedPrompts = new Set();
    }

    function forgetSelectedPrompts() {
        if (selectedPrompts.size === 0) return;
        if (confirm(`Are you sure you want to forget ${selectedPrompts.size} selected prompts?`)) {
            const numbersToForget = Array.from(selectedPrompts).join(' ');
            sendInspectorCommand(`forget ${numbersToForget}`);
            selectedPrompts = new Set(); // Clear selection after sending
        }
    }

    function clearHistory() {
        if (confirm('Are you sure you want to clear the entire session history? This cannot be undone.')) {
            sendInspectorCommand('clear');
            selectedPrompts = new Set(); // Clear selection as well
        }
    }


    // --- Computed properties for Telemetry (copied from .bak file) ---
    let telemetryData = [];
    $: if (contextData && contextData.tokenStats) {
        const stats = contextData.tokenStats;
        telemetryData = [
            { label: 'Cumulative Input', tokens: stats.cumulative_input_tokens, bytes: stats.cumulative_input_bytes },
            { label: 'Cumulative Output', tokens: stats.cumulative_output_tokens, bytes: stats.cumulative_output_bytes },
            { label: 'Last Trip Input', tokens: stats.last_trip_input_tokens, bytes: stats.last_trip_input_bytes },
            { label: 'Last Trip Output', tokens: stats.last_trip_output_tokens, bytes: stats.last_trip_output_bytes },
            { label: 'Banked Memory', tokens: stats.banked_tokens, bytes: stats.banked_bytes },
            { label: 'Session History', tokens: stats.history_tokens, bytes: stats.history_bytes },
            { label: 'Caching Context', tokens: stats.caching_context_tokens, bytes: stats.caching_context_bytes },
        ];
    }
</script>

<style>
    /* FIX: Restored all original CSS from the .bak file */
    :global(:root) { /* Ensure ANSI colors are available if not globally defined */
        --ansi-black: #2c3e50; --ansi-red: #c0392b; --ansi-green: #27ae60; --ansi-yellow: #f1c40f; --ansi-blue: #2980b9; --ansi-magenta: #8e44ad; --ansi-cyan: #16a085; --ansi-white: #bdc3c7;
        --ansi-bright-black: #95a5a6; --ansi-bright-red: #e74c3c; --ansi-bright-green: #2ecc71; --ansi-bright-yellow: #f39c12; --ansi-bright-blue: #3498db; --ansi-bright-magenta: #9b59b6; --ansi-bright-cyan: #1abc9c; --ansi-bright-white: #ecf0f1;
    }
    .inspector-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        font-family: monospace;
        background-color: var(--console-bg);
        color: var(--console-text);
        font-size: 14px;
    }
    .header {
        padding: 10px;
        flex-shrink: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    h1 {
        font-size: 1.2em;
        margin: 0;
        color: var(--title-bar-text);
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 5px;
        flex-grow: 1; /* Allow title to take up space */
    }
    
    /* --- NEW Tab Layout Styles --- */
    .tabs-container {
        display: flex;
        flex-direction: column;
        border-bottom: 1px solid var(--border-color);
        flex-shrink: 0;
    }
    .tabs-row {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
    }
    .tabs-row-1 { background-color: #012133; }
    .tabs-row-2 { background-color: #113143; }
    .tabs-row-3 { background-color: #214153; }

    .tab-button {
        padding: 8px 16px;
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        border-bottom: 2px solid transparent;
        outline: none;
    }
    .tab-button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .tab-button.active {
        color: var(--ansi-bright-blue);
        border-bottom-color: var(--ansi-bright-blue);
    }
    .tab-content {
        padding: 15px;
        overflow-y: auto;
        flex-grow: 1;
    }
    .waiting-text {
        color: #7f8c8d;
        padding: 15px;
    }
    .section {
        margin-bottom: 20px;
    }
    .section-title {
        font-weight: bold;
        color: var(--title-bar-text);
        margin-bottom: 8px;
        border-bottom: 1px dotted var(--border-color);
        padding-bottom: 4px;
    }
    .key-value-grid {
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 5px 15px;
    }
    .key-value-grid .key {
        color: var(--ansi-cyan);
        text-align: right;
    }
    .key-value-grid .value {
        word-break: break-all;
    }
    .command-history-list {
        list-style: decimal;
        padding-left: 20px;
        margin: 0;
    }
    .command-history-list li {
        padding: 2px 0;
    }
    details {
        border: 1px solid var(--border-color);
        border-radius: 3px;
        margin-bottom: 10px;
    }
    summary {
        padding: 8px;
        cursor: pointer;
        background-color: var(--title-bar-bg);
        font-weight: bold;
    }
    .content-box {
        padding: 10px;
        background-color: var(--window-bg);
        white-space: pre-wrap;
        word-break: break-all;
        /* max-height: 400px; <-- REMOVED for vertical expansion */
        /* overflow-y: auto; <-- REMOVED for vertical expansion */
    }
    .history-entry {
        border-bottom: 1px solid var(--border-color);
        padding: 8px 0;
    }
    .history-entry:last-child {
        border-bottom: none;
    }
    .history-entry-header {
        color: var(--ansi-yellow);
        margin-bottom: 5px;
    }
    .telemetry-grid {
        display: grid;
        grid-template-columns: auto max-content max-content;
        gap: 4px 12px;
        align-items: center;
    }
    .telemetry-grid span:nth-child(3n-2) { /* Label */
        font-weight: bold;
        text-align: right;
        color: var(--title-bar-text);
    }
    .telemetry-grid span:nth-child(3n-1) { /* Bytes */
        text-align: right;
        color: var(--ansi-bright-black);
    }
    .telemetry-grid span:nth-child(3n) { /* Tokens */
        text-align: right;
    }

    /* New styles for summary/section controls */
    .summary-with-controls, .section-title-with-controls {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%; /* Needed for correct layout in <summary> */
    }
    .expand-collapse-controls {
        flex-shrink: 0; /* Prevent controls from wrapping */
    }
    .expand-collapse-controls button {
        background: none;
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 2px 6px;
        font-size: 0.8em;
        border-radius: 3px;
        cursor: pointer;
        margin-left: 5px;
    }
    .expand-collapse-controls button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }

    /* New styles for collapsible prompts */
    .prompts-list-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .prompt-entry {
        border: 1px solid var(--border-color);
        border-radius: 3px;
        overflow: hidden; /* Keeps child bg colors within border radius */
    }
    .prompt-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px;
        cursor: pointer;
        background-color: var(--title-bar-bg);
        user-select: none;
        overflow: hidden;
    }
    .prompt-header:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .prompt-number {
        font-weight: bold;
        color: var(--ansi-yellow);
        flex-shrink: 0;
    }
    .prompt-preview {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        opacity: 0.8;
        flex-grow: 1;
        min-width: 0; /* Fix for text-overflow in flexbox */
    }
    .prompt-content {
        padding: 10px;
        background-color: var(--window-bg);
    }
    .prompt-content pre {
        margin: 0;
        white-space: pre-wrap;
    }

    /* New styles for header controls */
    .header-controls {
        display: flex;
        align-items: center;
        gap: 12px;
        padding-left: 15px; /* space between title and controls */
    }
    .header-controls .token-count-wrapper {
        position: relative;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        cursor: pointer;
        border: 1px solid var(--border-color);
        padding: 4px 8px;
        border-radius: 4px;
        background-color: var(--title-bar-bg);
    }
    .header-controls .token-count-wrapper:hover {
        background-color: var(--taskbar-button-hover-bg);
    }
    .header-controls .token-count,
    .header-controls .last-trip-token-count {
        font-weight: bold;
        font-size: 1.2em;
    }
    .header-controls .token-count { color: var(--ansi-yellow); }
    .header-controls .last-trip-token-count { color: var(--ansi-cyan); }
    .header-controls .pause-resume-button {
        background: none; border: none; cursor: pointer; padding: 0 4px;
        font-size: 1.8em; /* Bigger as requested */
        line-height: 1; opacity: 0.6; transition: opacity 0.2s;
    }
    .header-controls .pause-resume-button:hover { opacity: 1; }

    /* New styles for pop-out functionality */
    .tab-button-container {
        display: flex;
        align-items: center;
        position: relative;
    }
    .pop-out-button {
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        font-size: 1.1em;
        padding: 0 8px;
        opacity: 0.5;
        transition: opacity 0.2s;
    }
    .pop-out-button:hover {
        opacity: 1;
        color: var(--ansi-bright-blue);
    }
    .detached-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        text-align: center;
        color: var(--title-bar-text);
    }
    .detached-placeholder button {
        margin-top: 15px;
        padding: 8px 16px;
        border-radius: 3px;
        cursor: pointer;
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        background-color: var(--taskbar-button-bg);
    }
    .detached-placeholder button:hover {
        background-color: var(--taskbar-button-hover-bg);
    }

    /* Token Tooltip styles */
    .token-tooltip {
        position: fixed;
        background-color: var(--window-bg);
        border: 1px solid var(--border-color);
        padding: 8px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        z-index: 210;
        width: max-content;
        font-size: 12px;
        color: var(--console-text);
        text-align: left;
        white-space: nowrap;
        pointer-events: none;
    }
    .tooltip-grid { display: grid; grid-template-columns: auto max-content max-content; gap: 4px 12px; align-items: center; }
    .tooltip-grid span:nth-child(3n-2) { /* Label */
        font-weight: bold;
        text-align: right;
        color: var(--title-bar-text);
    }
    .tooltip-grid span:nth-child(3n-1) { /* Bytes */
        text-align: right;
        color: var(--ansi-bright-black);
    }
    .tooltip-grid span:nth-child(3n) { /* Tokens */
        text-align: right;
    }

    /* New styles for prompt management */
    .prompts-action-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px;
        background-color: var(--title-bar-bg);
        border: 1px solid var(--border-color);
        border-radius: 3px;
        margin-top: 10px;
    }
    .prompts-action-bar button {
        background-color: var(--taskbar-button-bg);
        border: 1px solid var(--border-color);
        color: var(--title-bar-text);
        padding: 4px 8px;
        border-radius: 3px;
        cursor: pointer;
        margin-left: 5px;
        font-size: 0.9em;
    }
    .prompts-action-bar button:hover:not(:disabled) {
        background-color: var(--taskbar-button-hover-bg);
    }
    .prompts-action-bar button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .prompts-action-bar .forget-button,
    .prompts-action-bar .clear-button {
        background-color: var(--ansi-red);
        border-color: #e74c3c;
        color: white;
    }
    .prompts-action-bar .forget-button:hover:not(:disabled),
    .prompts-action-bar .clear-button:hover {
        background-color: #e74c3c;
    }
    .prompt-delete-button {
        background: none;
        border: none;
        color: var(--title-bar-text);
        cursor: pointer;
        font-size: 1.5em;
        line-height: 1;
        padding: 0 8px 0 0;
        opacity: 0.5;
        font-weight: bold;
        align-self: center;
    }
    .prompt-delete-button:hover {
        opacity: 1;
        color: var(--ansi-red);
    }
    .prompt-select-checkbox {
        margin-right: 8px;
        cursor: pointer;
        width: 16px;
        height: 16px;
        align-self: center;
    }

    /* --- NEW styles for all prompt types --- */
    /* Styles are applied to the parent .prompt-entry based on type,
       affecting the entire entry (collapsed and expanded states). */

    /* Info Type (e.g., system messages) */
    .prompt-entry.prompt-type-info { border-left: 4px solid var(--ansi-bright-blue); }
    .prompt-entry.prompt-type-info .prompt-content {
        background-color: rgba(52, 152, 219, 0.1); /* Faded blue */
        font-style: italic;
    }

    /* Error Type */
    .prompt-entry.prompt-type-error { border-left: 4px solid var(--ansi-bright-red); }
    .prompt-entry.prompt-type-error .prompt-content {
        background-color: rgba(231, 76, 60, 0.1); /* Faded red */
    }

    /* Command Type */
    .prompt-entry.prompt-type-command { border-left: 4px solid var(--ansi-bright-green); }
    .prompt-entry.prompt-type-command .prompt-content {
        background-color: rgba(46, 204, 113, 0.1); /* Faded green */
    }

    /* Comment Type */
    .prompt-entry.prompt-type-comment { border-left: 4px solid var(--ansi-bright-black); }
    .prompt-entry.prompt-type-comment .prompt-content {
        background-color: rgba(149, 165, 166, 0.1); /* Faded grey */
        font-style: italic;
    }

    /* Chat Sent Type */
    .prompt-entry.prompt-type-chat-sent { border-left: 4px solid var(--ansi-bright-cyan); }
    .prompt-entry.prompt-type-chat-sent .prompt-content {
        background-color: rgba(26, 188, 156, 0.1); /* Faded cyan */
    }

    /* Chat Received Type */
    .prompt-entry.prompt-type-chat-received { border-left: 4px solid var(--ansi-bright-magenta); }
    .prompt-entry.prompt-type-chat-received .prompt-content {
        background-color: rgba(155, 89, 182, 0.1); /* Faded magenta */
    }

    /* Unknown Type */
    .prompt-entry.prompt-type-unknown { border-left: 4px solid var(--ansi-yellow); }
    .prompt-entry.prompt-type-unknown .prompt-content {
        background-color: rgba(241, 196, 15, 0.1); /* Faded yellow */
    }
</style>

<div class="inspector-container">
    {#if !isDetached}
        <!-- MAIN INSPECTOR UI (with tabs) -->
        <div class="header">
            {#if contextData}
                <h1>Context for {contextData.user}</h1>
            {:else}
                <h1>Context for {targetUser}</h1>
            {/if}

            {#if contextData && contextData.isBot}
                {@const stats = contextData.tokenStats}
                <div class="header-controls">
                    {#if stats}
                        <div class="token-count-wrapper"
                             on:mouseenter={showTokenTooltip}
                             on:mouseleave={hideTokenTooltip}
                             on:click={handleTokenClick}
                             title="Click to view Telemetry">
                            <span class="last-trip-token-count" title="Last trip input tokens">
                                {abbreviateNumber(stats.last_trip_input_tokens)}
                            </span>
                            <span style="color: var(--ansi-bright-black); margin: 0 4px;">/</span>
                            <span class="token-count" title="Cumulative input tokens">
                                {abbreviateNumber(stats.cumulative_input_tokens)}
                            </span>
                        </div>
                    {/if}
                    <button
                        class="pause-resume-button"
                        on:click|stopPropagation={togglePause}
                        title={contextData.isPaused ? `Resume ${targetUser}` : `Pause ${targetUser}`}
                    >
                        {contextData.isPaused ? '▶️' : '⏸️'}
                    </button>
                </div>
            {/if}
        </div>

        <div class="tabs-container">
            {#each tabRows as tabs, rowIndex}
                <div class="tabs-row tabs-row-{rowIndex + 1}">
                    {#each tabs as tab (tab.id)}
                        <div class="tab-button-container">
                            <button class="tab-button" class:active={activeTab === tab.id} on:click={() => activeTab = tab.id}>
                                {tab.name}{#if detachedTabs[tab.id]} ⇲{/if}
                            </button>
                            <button
                                class="pop-out-button"
                                title={detachedTabs[tab.id] ? 'Focus popped-out window' : 'Pop out to new window'}
                                on:click|stopPropagation={() => {
                                    const info = detachedTabs[tab.id];
                                    if (info) {
                                        windows.setActiveTab(info.groupId, info.tabId);
                                    } else {
                                        popOutTab(tab.id);
                                    }
                                }}
                            >
                                ⇲
                            </button>
                        </div>
                    {/each}
                </div>
            {/each}
        </div>

        <div class="tab-content">
            {#if !contextData}
                <p class="waiting-text">Waiting for context data for {targetUser}...</p>
            {:else if detachedTabs[activeTab]}
                <div class="detached-placeholder">
                    <p>Content is in a separate window.</p>
                    <button on:click={() => {
                        const info = detachedTabs[activeTab];
                        if (info) windows.setActiveTab(info.groupId, info.tabId);
                    }}>
                        Focus Window
                    </button>
                </div>
            {:else}
                <!-- Render content inline using a recursive call to self in detached mode -->
                <svelte:self {contextData} isDetached={true} detachedView={activeTab} {consoleWs} />
            {/if}
        </div>

    {:else if contextData}
        <!-- DETACHED/INLINE VIEW UI (no tabs) -->
        <!-- FIX: Reformatted all views below for readability and correctness -->
        {#if detachedView === 'overview'}
            <div class="section">
                <h2 class="section-title">User Details</h2>
                <div class="key-value-grid">
                    <span class="key">Login Time:</span>
                    <span class="value">{formatDate(contextData.loginTime)}</span>
                    <span class="key">Bot:</span>
                    <span class="value">{contextData.isBot ? 'Yes' : 'No'}</span>
                    <span class="key">Super User:</span>
                    <span class="value">{contextData.isSuperUser ? 'Yes' : 'No'}</span>
                </div>
            </div>
            <div class="section">
                <h2 class="section-title">Session State</h2>
                <div class="key-value-grid">
                     <span class="key">PWD:</span>
                     <span class="value">{contextData.pwd}</span>
                </div>
            </div>
        {:else if detachedView === 'environment'}
            <div class="section">
                <h2 class="section-title">Environment Variables</h2>
                <div class="key-value-grid">
                    {#each Object.entries(contextData.env) as [key, value]}
                        <span class="key">{key}:</span>
                        <span class="value">{value}</span>
                    {:else}
                        <span class="value">No environment variables set.</span>
                    {/each}
                </div>
            </div>
            <div class="section">
                <h2 class="section-title">Aliases</h2>
                <div class="key-value-grid">
                    {#each Object.entries(contextData.aliases) as [key, value]}
                        <span class="key">{key}:</span>
                        <span class="value">{value}</span>
                    {:else}
                        <span class="value">No aliases defined.</span>
                    {/each}
                </div>
            </div>
        {:else if detachedView === 'history'}
            <div class="section">
                 <h2 class="section-title">Command History</h2>
                 {#if contextData.commandHistory && contextData.commandHistory.length > 0}
                    <ol class="command-history-list">
                        {#each contextData.commandHistory as cmd, i (i)}
                            <li>{cmd}</li>
                        {/each}
                    </ol>
                 {:else}
                    <p>No command history.</p>
                 {/if}
            </div>
        {:else if detachedView === 'preamble'}
             <div class="section">
                <h2 class="section-title">AI Preamble</h2>
                <pre class="content-box">{contextData.aiContext?.preamble || '(empty)'}</pre>
            </div>
        {:else if detachedView === 'memoryBanks'}
            <div class="section">
                <div class="section-title-with-controls">
                    <h2 class="section-title" style="margin-bottom: 0; border-bottom: none; padding-bottom: 0;">
                        Memory Banks ({contextData.aiContext?.banks?.length ?? 0})
                    </h2>
                    {#if contextData.aiContext?.banks?.length > 0}
                        <div class="expand-collapse-controls">
                            <button on:click={() => toggleAllBanks(true)}>Expand All</button>
                            <button on:click={() => toggleAllBanks(false)}>Collapse All</button>
                        </div>
                    {/if}
                </div>
    
                {#if contextData.aiContext?.banks?.length > 0}
                    <div style="margin-top: 10px; display: flex; flex-direction: column; gap: 10px;">
                        {#each contextData.aiContext.banks as bank (bank.name)}
                            <details bind:open={bankExpandedState[bank.name]}>
                                <summary>{bank.name}</summary>
                                <pre class="content-box" style="background-color: var(--console-bg); margin-top: 5px;">{bank.content}</pre>
                            </details>
                        {/each}
                    </div>
                {:else}
                    <p class="waiting-text" style="padding-top: 10px;">No banks loaded.</p>
                {/if}
            </div>
        {:else if detachedView === 'postamble'}
             <div class="section">
                <h2 class="section-title">AI Postamble</h2>
                <pre class="content-box">{contextData.aiContext?.postamble || '(empty)'}</pre>
            </div>
        {:else if detachedView === 'prompts'}
            <div class="section">
                <div class="section-title-with-controls">
                    <h2 class="section-title" style="margin-bottom: 0; border-bottom: none; padding-bottom: 0;">
                        Session Prompts ({contextData.aiContext.sessionHistory.length} entries)
                    </h2>
                    {#if contextData.aiContext.sessionHistory.length > 0}
                        <div class="expand-collapse-controls">
                            <button on:click={() => toggleAllPrompts(true)}>Expand All</button>
                            <button on:click={() => toggleAllPrompts(false)}>Collapse All</button>
                        </div>
                    {/if}
                </div>

                {#if contextData.aiContext.sessionHistory.length > 0}
                    <div class="prompts-action-bar">
                        <div class="selection-controls">
                            <button on:click={selectAllPrompts}>Select All</button>
                            <button on:click={deselectAllPrompts}>Deselect All</button>
                        </div>
                        <div class="action-buttons">
                            <button
                                class="forget-button"
                                disabled={selectedPrompts.size === 0}
                                on:click={forgetSelectedPrompts}
                            >
                                Forget Selected ({selectedPrompts.size})
                            </button>
                            <button class="clear-button" on:click={clearHistory}>Clear History</button>
                        </div>
                    </div>
                {/if}

                <div class="prompts-list-container" style="margin-top: 10px;">
                    {#each contextData.aiContext.sessionHistory as entry (entry.number)}
                        {@const analysis = analyzePrompt(entry.content)}
                        <div class="prompt-entry prompt-type-{analysis.type}">
                            <div class="prompt-header" on:click={() => {
                                promptExpandedState[entry.number] = !promptExpandedState[entry.number];
                                promptExpandedState = promptExpandedState;
                            }}>
                                <button class="prompt-delete-button" title="Forget prompt #{entry.number}" on:click|stopPropagation={() => forgetSinglePrompt(entry.number)}>
                                    &times;
                                </button>
                                <input
                                    type="checkbox"
                                    class="prompt-select-checkbox"
                                    title="Select prompt #{entry.number}"
                                    checked={selectedPrompts.has(entry.number)}
                                    on:click|stopPropagation
                                    on:change={() => togglePromptSelection(entry.number)}
                                />
                                <span class="prompt-number">Prompt #{entry.number}</span>
                                {#if !promptExpandedState[entry.number]}
                                    <span class="prompt-preview">{@html parseAnsi(getFirstLine(analysis.content))}</span>
                                {/if}
                            </div>
                            {#if promptExpandedState[entry.number]}
                                <div class="prompt-content">
                                    <pre>{#if analysis.prompt}<span>{@html parseAnsi(analysis.prompt)}</span>{/if}{@html parseAnsi(analysis.strippedContent)}</pre>
                                </div>
                            {/if}
                        </div>
                    {:else}
                        <p>No session history.</p>
                    {/each}
                </div>
            </div>
        {:else if detachedView === 'telemetry'}
            <div class="section">
                <h2 class="section-title">Token Statistics</h2>
                <div class="telemetry-grid">
                    {#each telemetryData as item}
                        <span>{item.label}:</span>
                        <span>({formatBytes(item.bytes)})</span>
                        <span>{item.tokens.toLocaleString('en-US')} tokens</span>
                    {/each}
                </div>
            </div>
        {:else if detachedView === 'json'}
            <div class="section">
                <h2 class="section-title">Raw Context Data</h2>
                <pre class="content-box" style="max-height: 400px; overflow-y: auto;">{JSON.stringify(contextData, null, 2)}</pre>
            </div>
        {/if}
    {/if}

    {#if tokenTooltip.visible && contextData && contextData.tokenStats}
        {@const stats = contextData.tokenStats}
        <div
            class="token-tooltip"
            style="top: {tokenTooltip.y}px; left: {tokenTooltip.x}px; transform: translateX(-100%);"
        >
            <div class="tooltip-grid">
                <span>Cumulative Input:</span><span>({formatBytes(stats.cumulative_input_bytes)})</span><span>{stats.cumulative_input_tokens.toLocaleString('en-US')} tokens</span>
                <span>Cumulative Output:</span><span>({formatBytes(stats.cumulative_output_bytes)})</span><span>{stats.cumulative_output_tokens.toLocaleString('en-US')} tokens</span>
                <span>Last Trip Input:</span><span>({formatBytes(stats.last_trip_input_bytes)})</span><span>{stats.last_trip_input_tokens.toLocaleString('en-US')} tokens</span>
                <span>Last Trip Output:</span><span>({formatBytes(stats.last_trip_output_bytes)})</span><span>{stats.last_trip_output_tokens.toLocaleString('en-US')} tokens</span>
                <span>Banked Memory:</span><span>({formatBytes(stats.banked_bytes)})</span><span>{stats.banked_tokens.toLocaleString('en-US')} tokens</span>
                <span>Session History:</span><span>({formatBytes(stats.history_bytes)})</span><span>{stats.history_tokens.toLocaleString('en-US')} tokens</span>
                <span>Caching Context:</span><span>({formatBytes(stats.caching_context_bytes)})</span><span>{stats.caching_context_tokens.toLocaleString('en-US')} tokens</span>
            </div>
        </div>
    {/if}
</div>