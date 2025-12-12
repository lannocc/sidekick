<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    import { onMount, onDestroy } from 'svelte';
    import { get } from 'svelte/store';
    import { createFsAdapter } from '../fs_adapter.js';
    import { windows, activeConsoles, newFileViewer, newAskWindow } from '../windows.js';
    import { windowSettings, windowView, TASKBAR_HEIGHT } from '../desktop.js';
    import { connectionStatus, createBox } from '../bridge.js';
    import { fileSelection } from '../iosk.js';
    import WindowSettingsModal from '../popup/WindowSettingsModal.svelte';

    // --- Component Props & State ---
    export let id;
    export let groupId;
    export let connectionType; // 'iosk' or 'skybridge'
    export let consoleId = null; // Used only for 'iosk'
    export let initialPath = '.';
    export let pickerTargetId = null;
    export let componentName;
    export let x, y, width, height;
    export let consoleConnection = null; // Passed during Dash restore

    // --- Recursive Rendering Props (for <svelte:self>) ---
    export let treeNode = null;
    export let treeLevel = 0;
    // Pass down reactive props needed by the recursive part
    export { viewMode, colorMode, getTileColor, handleItemClick, expandedNodes, toggleNode, handleRightClick, handleDragStart };

    let currentPath = (initialPath && initialPath !== '.') ? initialPath : '/';
    let items = [];
    let errorMessage = '';
    let fsAdapter;

    // --- State for Watch feature ---
    let isWatching = false;
    let previousItemsMap = new Map();
    export let itemChangeStatus = {};
    let changeClearTimeout;

    // --- View State ---
    let viewMode = 'list';
    export let columnsEnabled = false;
    let colorMode = 'type';
    export let nestedView = false;
    let treeItems = [];
    let expandedNodes = new Set();
    let columnFiles = [];
    let columnDirs = [];

    // --- Column View Panning State ---
    let columnsContainer;
    let isPanning = false;
    let panStartX, panScrollLeftStart, panStartY;
    let scrollableColumns = [];

    // --- Settings Modal State ---
    let showSettings = false;
    let settingsModel = { usePwd: true, path: '/' };

    // --- Ported State from LocalFileExplorer ---
    let contextMenu = { visible: false, x: 0, y: 0, item: null };

    // --- Feature Flags ---
    // Phase 2: Backend parity. All features are now supported by skybridge.
    $: supportsWatch = true;
    $: supportsRecursive = true;

    function getFileExtension(name) {
        if (name === '..') return '';
        const lastDot = name.lastIndexOf('.');
        if (lastDot === -1 || lastDot === 0) return '';
        return name.substring(lastDot + 1).toLowerCase();
    }

    function getTileColor(item, mode) {
        if (item.type === 'dir' && item.name === '..') return '#555e64';

        if (mode === 'age') {
            if (item.mtime <= 0) return '#7f8c8d';
            const now = Date.now() / 1000;
            const ageSeconds = now - item.mtime;

            if (ageSeconds < 3600) return '#27ae60';
            if (ageSeconds < 86400) return '#2980b9';
            if (ageSeconds < 604800) return '#f39c12';
            if (ageSeconds < 2592000) return '#d35400';
            return '#c0392b';
        } else { // mode === 'type'
            if (item.type === 'dir') return '#2980b9';

            const ext = getFileExtension(item.name);
            switch (ext) {
                case 'txt': case 'md': case 'json': case 'yml': case 'xml': case 'log': return '#27ae60';
                case 'js': case 'py': case 'svelte': case 'html': case 'css': case 'sh': case 'c': case 'cpp': return '#8e44ad';
                case 'png': case 'jpg': case 'jpeg': case 'gif': case 'svg': case 'ico': return '#c0392b';
                case 'zip': case 'gz': case 'tar': case 'rar': return '#d35400';
                default: return '#7f8c8d';
            }
        }
    }

    // --- Settings ---
    export function showSettingsDialog() {
        const allSettings = get(windowSettings);
        const currentSettings = allSettings[componentName];
        settingsModel = {
            usePwd: currentSettings?.initialPath === '.',
            path: currentSettings?.initialPath !== '.' ? currentSettings.initialPath : '/'
        };
        showSettings = true;
    }

    function handleSaveComponentSettings() {
        const componentSettings = { initialPath: settingsModel.usePwd ? '.' : (settingsModel.path || '/') };
        windowSettings.update(all => ({ ...all, [componentName]: { ...all[componentName], ...componentSettings } }));
    }

    // --- Context Menu & Drag/Drop (Ported from LocalFileExplorer) ---
    function handleRightClick(event, item) {
        event.preventDefault();
        const { panX, panY, zoom } = get(windowView);
        const menuX = (event.clientX - panX) / zoom;
        const menuY = ((event.clientY - TASKBAR_HEIGHT) - panY) / zoom;
        contextMenu = { visible: true, x: menuX, y: menuY, item };
    }

    function closeContextMenu() {
        contextMenu = { visible: false, x: 0, y: 0, item: null };
    }

    function onAsk() {
        if (!contextMenu.item) return;
        const itemPath = contextMenu.item.path || (contextMenu.item.name === '..'
            ? (currentPath.substring(0, currentPath.lastIndexOf('/')) || '/')
            : (currentPath === '/' ? `/${contextMenu.item.name}` : `${currentPath}/${contextMenu.item.name}`));
        
        newAskWindow([itemPath]);
        closeContextMenu();
    }

    function onBoxThis() {
        if (!contextMenu.item || contextMenu.item.type !== 'dir') return;
        const itemPath = contextMenu.item.path || (contextMenu.item.name === '..'
            ? (currentPath.substring(0, currentPath.lastIndexOf('/')) || '/')
            : (currentPath === '/' ? `/${contextMenu.item.name}` : `${currentPath}/${contextMenu.item.name}`));
        
        const defaultBoxName = itemPath.split('/').pop() || (itemPath === '/' ? 'root' : 'New Box');
        const boxName = prompt(`Enter a name for the new Box for path "${itemPath}":`, defaultBoxName);
        if (!boxName) return;

        createBox(boxName, 'local', itemPath, { screenX: contextMenu.x, screenY: contextMenu.y });
        closeContextMenu();
    }

    function handleDragStart(event, item) {
        if (connectionType !== 'skybridge' || !item || item.name === '..') {
            event.preventDefault();
            return;
        }
        const itemPath = item.path || (currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`);
        const data = {
            type: item.type,
            path: itemPath,
            name: item.name
        };
        event.dataTransfer.setData('application/sidekick-fs-item', JSON.stringify(data));
        event.dataTransfer.effectAllowed = 'copy';
    }

    function selectCurrentPath() {
        if (pickerTargetId) {
            fileSelection.set({ targetId: pickerTargetId, path: currentPath });
            windows.removeWindow(groupId);
        }
    }

    // --- State & Connection Management ---
    $: if (id !== undefined && groupId !== undefined) {
        windows.updateTabProps(groupId, id, { currentPath, isSettingsModalOpen: showSettings });
    }

    $: if (connectionType === 'iosk' && consoleConnection && $windows) {
        const myConsoleTab = $windows.flatMap(g => g.tabs).find(t => t.id === consoleId);
        if (!myConsoleTab || !myConsoleTab.isConsoleConnected) {
            const key = `${consoleConnection.user}@${consoleConnection.url}`;
            const compatibleConsole = $activeConsoles.get(key);
            if (compatibleConsole) {
                if (consoleId !== compatibleConsole.id) {
                    windows.updateTabProps(groupId, id, { consoleId: compatibleConsole.id });
                }
            } else {
                if (consoleId !== null) {
                    windows.updateTabProps(groupId, id, { consoleId: null });
                }
                errorMessage = 'No active IOSK connection available.';
                items = [];
            }
        }
    }

    // --- View Logic ---
    function switchViewMode(newMode) { viewMode = newMode; }
    function toggleNode(path) {
        expandedNodes.has(path) ? expandedNodes.delete(path) : expandedNodes.add(path);
        expandedNodes = expandedNodes;
    }

    function toggleWithRefetch(flag) {
        const oldRecursive = nestedView || columnsEnabled;
        if (flag === 'nested') nestedView = !nestedView;
        if (flag === 'columns') columnsEnabled = !columnsEnabled;
        const newRecursive = nestedView || columnsEnabled;

        if (oldRecursive !== newRecursive || flag === 'nested') {
            items = [];
            treeItems = [];
            if (viewMode === 'list') expandedNodes.clear();
            requestPath(currentPath);
        }
    }

    function buildTree(flatList, basePath) {
        if (!flatList || flatList.length === 0) return [];
        const map = new Map();
        flatList.forEach(item => map.set(item.path, { ...item, children: [] }));
        const roots = [];
        flatList.forEach(item => {
            const node = map.get(item.path);
            const lastSlash = item.path.lastIndexOf('/');
            let parentPath = lastSlash > 0 ? item.path.substring(0, lastSlash) : (lastSlash === 0 && item.path.length > 1 ? '/' : null);
            if (parentPath === basePath) roots.push(node);
            else if (parentPath && map.has(parentPath)) map.get(parentPath).children.push(node);
        });
        const sortRecursive = (nodes) => {
            nodes.sort((a, b) => (a.type === b.type) ? a.name.localeCompare(b.name) : (a.type === 'dir' ? -1 : 1));
            nodes.forEach(node => { if (node.children.length > 0) sortRecursive(node.children); });
        };
        sortRecursive(roots);
        return roots;
    }

    $: if ((nestedView || columnsEnabled) && supportsRecursive) {
        treeItems = buildTree(items, currentPath);
        if (columnsEnabled) {
            columnFiles = treeItems.filter(item => item.type === 'file');
            columnDirs = treeItems.filter(item => item.type === 'dir');
        }
    }

    // --- Data Fetching ---
    function toggleWatch() {
        isWatching = !isWatching;
        if (isWatching) {
            fsAdapter.watch(currentPath);
        } else {
            fsAdapter.unwatch(currentPath);
            previousItemsMap.clear();
            itemChangeStatus = {};
            clearTimeout(changeClearTimeout);
        }
    }

    function requestPath(path) {
        errorMessage = '';
        if ((connectionType === 'iosk' && !consoleId)) return;
        if (!supportsRecursive) {
            nestedView = false;
            columnsEnabled = false;
        }
        const isRecursive = (nestedView || columnsEnabled) && supportsRecursive;
        fsAdapter.requestPath(path, isRecursive, isRecursive);
    }

    function handleItemClick(item) {
        const keyFn = i => (supportsRecursive && (nestedView || columnsEnabled)) ? i.path : i.name;
        if (itemChangeStatus[keyFn(item)] === 'removed') return;

        if (item.type === 'file') {
            const filePath = (supportsRecursive && (nestedView || columnsEnabled)) ? item.path : (currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`);
            if (pickerTargetId) {
                fileSelection.set({ targetId: pickerTargetId, path: filePath });
                windows.removeWindow(groupId);
            } else {
                newFileViewer({ connectionType, consoleId, path: filePath, groupId });
            }
        } else if (item.type === 'dir') {
            const canNavigate = (item.name === '..' || !nestedView || columnsEnabled || (nestedView && viewMode === 'tiles'));
            if (canNavigate || !supportsRecursive) {
                if (isWatching) toggleWatch(); // Stop watching old path before navigating
                let newPath;
                if (item.name === '..') {
                    if (currentPath === '/') return;
                    newPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
                } else {
                    newPath = item.path || (currentPath === '/' ? `/${item.name}` : `${currentPath}/${item.name}`);
                }
                requestPath(newPath);
            }
        }
    }

    // --- Column View Pan/Scroll ---
    function handleWheelScroll(event) {
        if (event.shiftKey && columnsContainer) {
            event.preventDefault();
            columnsContainer.scrollLeft += event.deltaY;
        }
    }
    function handlePanStart(event) { if (event.button !== 1 || !columnsContainer) return; event.preventDefault(); isPanning = true; columnsContainer.style.cursor = 'grabbing'; columnsContainer.style.userSelect = 'none'; panStartX = event.clientX; panScrollLeftStart = columnsContainer.scrollLeft; panStartY = event.clientY; scrollableColumns = []; const els = columnsContainer.querySelectorAll('.column-content'); els.forEach(el => { if (el.scrollHeight > el.clientHeight) scrollableColumns.push({ element: el, initialScrollTop: el.scrollTop }); }); window.addEventListener('mousemove', handlePanMove); window.addEventListener('mouseup', handlePanEnd); }
    function handlePanMove(event) { if (!isPanning) return; const dx = event.clientX - panStartX; columnsContainer.scrollLeft = panScrollLeftStart - dx; const dy = event.clientY - panStartY; scrollableColumns.forEach(({ element, initialScrollTop }) => { element.scrollTop = initialScrollTop - dy; }); }
    function handlePanEnd(event) { if (event.button !== 1 || !isPanning) return; isPanning = false; columnsContainer.style.cursor = 'grab'; columnsContainer.style.userSelect = 'auto'; scrollableColumns = []; window.removeEventListener('mousemove', handlePanMove); window.removeEventListener('mouseup', handlePanEnd); }
    function getMaxExpandedDepth(node) { if (!node.children || node.children.length === 0) return 0; function findMax(currentNode, currentLevel) { if (!expandedNodes.has(currentNode.path) || !currentNode.children || currentNode.children.length === 0) return currentLevel; let maxChildLevel = currentLevel; for (const child of currentNode.children) { const childMaxLevel = findMax(child, currentLevel + 1); if (childMaxLevel > maxChildLevel) maxChildLevel = childMaxLevel; } return maxChildLevel; } let maxDepth = 0; for (const child of node.children) { const childMaxDepth = findMax(child, 0); if (childMaxDepth > maxDepth) maxDepth = childMaxDepth; } return maxDepth; }

    onMount(() => {
        if (treeNode) return; // Prevent execution in recursive children

        fsAdapter = createFsAdapter({ connectionType, consoleId, requesterId: id });
        window.addEventListener('click', closeContextMenu);

        fsAdapter.listResponse.subscribe(response => {
            if (!response) return;
            if (response.requester_id !== id) return;
            const { path, entries, error } = response;
            if (error) {
                errorMessage = error;
                items = [];
                previousItemsMap.clear();
            } else if (entries) {
                let finalListing = [...entries];
                const keyFn = item => (supportsRecursive && (nestedView || columnsEnabled)) ? item.path : item.name;

                if (isWatching && previousItemsMap.size > 0) {
                    const newItemsMap = new Map(entries.map(item => [keyFn(item), item]));
                    const newChangeStatus = {};
                    newItemsMap.forEach((newItem, key) => {
                        if (!previousItemsMap.has(key)) newChangeStatus[key] = 'new';
                        else {
                            const oldItem = previousItemsMap.get(key);
                            if (newItem.mtime !== oldItem.mtime || newItem.size !== oldItem.size) newChangeStatus[key] = 'modified';
                        }
                    });
                    previousItemsMap.forEach((oldItem, key) => {
                        if (key !== '..' && !newItemsMap.has(key)) {
                            newChangeStatus[key] = 'removed';
                            finalListing.push(oldItem);
                        }
                    });
                    delete newChangeStatus['..'];
                    if (Object.keys(newChangeStatus).length > 0) {
                       if (!get(windows).find(w => w.id === groupId)?.isActive) {
                           windows.notifyActivity(groupId, id, { summary: `File changes in ${currentPath}` });
                       }
                       itemChangeStatus = { ...itemChangeStatus, ...newChangeStatus };
                       clearTimeout(changeClearTimeout);
                       changeClearTimeout = setTimeout(() => {
                           items = items.filter(item => itemChangeStatus[keyFn(item)] !== 'removed');
                           itemChangeStatus = {};
                       }, 1500);
                    }
                }
                previousItemsMap = new Map(entries.map(item => [keyFn(item), item]));
                currentPath = path;

                if (!supportsRecursive || (!nestedView && !columnsEnabled)) {
                    const parentDir = { name: '..', type: 'dir', size: -1, mtime: -1 };
                    const sortedItems = finalListing.sort((a, b) => (a.type === b.type) ? a.name.localeCompare(b.name) : (a.type === 'dir' ? -1 : 1));
                    items = (path !== '/') ? [parentDir, ...sortedItems] : sortedItems;
                } else {
                    items = finalListing;
                }
                errorMessage = '';
            }
        });

        fsAdapter.watchEvent.subscribe(event => {
            if (event && isWatching && event.path === currentPath) {
                requestPath(currentPath);
            }
        });
        
        if (connectionType === 'skybridge') {
            connectionStatus.subscribe(s => {
                if (s === 'connected') {
                    requestPath(initialPath);
                } else if (s === 'disconnected' || s === 'error') {
                    errorMessage = "SKYBRIDGE REQUIRED. Not connected to local backend.";
                    items = [];
                }
            });
        } else { // iosk
            if (consoleId) requestPath(currentPath);
        }
    });

    onDestroy(() => {
        if (treeNode) return; // Prevent execution in recursive children

        if (isWatching) fsAdapter.unwatch(currentPath);
        if (fsAdapter) fsAdapter.destroy();
        clearTimeout(changeClearTimeout);
        window.removeEventListener('click', closeContextMenu);
        window.removeEventListener('mousemove', handlePanMove);
        window.removeEventListener('mouseup', handlePanEnd);
    });
</script>

<style>
    .explorer-container { display: flex; flex-direction: column; height: 100%; font-family: monospace; background-color: var(--console-bg); color: var(--console-text); font-size: 14px; user-select: none; }
    .path-bar { padding: 4px 8px; background-color: var(--title-bar-bg); border-bottom: 1px solid var(--border-color); flex-shrink: 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
    .path-bar .path-text { flex-grow: 1; overflow-x: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .path-bar .right-controls { display: flex; align-items: center; }
    .path-bar button { background-color: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--taskbar-text); padding: 2px 8px; border-radius: 3px; cursor: pointer; margin-left: 10px; flex-shrink: 0; }
    .path-bar button:hover { background-color: var(--taskbar-button-hover-bg); }
    .controls-group { display: flex; align-items: center; gap: 10px; flex-shrink: 0; margin-left: 10px; flex-wrap: wrap; justify-content: flex-end; }
    .view-mode-selector, .color-mode-selector { display: flex; background: var(--taskbar-button-bg); border-radius: 3px; border: 1px solid var(--border-color); overflow: hidden; }
    .color-mode-selector { padding: 2px 5px; gap: 8px; font-size: 12px; }
    .color-mode-selector label { display: flex; align-items: center; gap: 3px; cursor: pointer; }
    .view-button { background: transparent; border: none; border-left: 1px solid var(--border-color); color: var(--taskbar-text); padding: 2px 8px; cursor: pointer; font-size: 16px; line-height: 1; }
    .view-button:first-child { border-left: none; }
    .view-button:hover { background-color: var(--taskbar-button-hover-bg); }
    .view-button.active { background-color: var(--taskbar-button-hover-bg); color: #3498db; }
    .watch-button { background: var(--taskbar-button-bg); border: 1px solid var(--border-color); color: var(--taskbar-text); padding: 2px 8px; border-radius: 3px; cursor: pointer; flex-shrink: 0; }
    .watch-button:hover { background-color: var(--taskbar-button-hover-bg); }
    .watch-button.active { background-color: var(--taskbar-button-hover-bg); border-color: #2980b9; color: #3498db; }
    .watch-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .error-message { color: #e74c3c; padding: 8px; flex-shrink: 0; }
    .item-list { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .item { display: flex; padding: 2px 8px; cursor: pointer; border-radius: 2px; }
    .item:hover { background-color: var(--taskbar-button-hover-bg); }
    .item-icon { width: 25px; flex-shrink: 0; }
    .item-name { flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .item-size { width: 80px; text-align: right; flex-shrink: 0; color: #7f8c8d; }
    .tree-node-expander { width: 15px; text-align: center; flex-shrink: 0; }
    .tree-item { padding-left: calc(8px + var(--level) * 20px); }
    .tile-grid { flex-grow: 1; overflow-y: auto; padding: 8px; display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; }
    .tile-item { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 8px; border-radius: 4px; cursor: pointer; text-align: center; color: white; word-break: break-word; aspect-ratio: 1 / 1; transition: transform 0.1s ease-in-out, box-shadow 0.1s ease-in-out; }
    .tile-item:hover { transform: scale(1.05); box-shadow: 0 0 10px rgba(0,0,0,0.5); z-index: 10; }
    .tile-icon { font-size: 2.5em; line-height: 1; min-height: 1em; }
    .tile-name { font-size: 12px; margin-top: 5px; max-height: 2.6em; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .nested-dir-container { display: flex; flex-direction: column; border: 2px solid; border-radius: 4px; background: rgba(0,0,0,0.1); min-height: 0; overflow: hidden; cursor: default; }
    .nested-dir-name { padding: 2px 4px; text-align: center; color: white; font-size: 12px; font-weight: bold; flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .nested-dir-name:hover { filter: brightness(1.2); }
    .nested-dir-content-grid { flex-grow: 1; display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 3px; padding: 3px; overflow: hidden; min-height: 0; }
    .nested-tile { padding: 4px 2px; aspect-ratio: unset; min-height: 45px; }
    .nested-tile .tile-icon { font-size: 1.5em; min-height: 0; }
    .nested-tile .tile-name { font-size: 10px; margin-top: 2px; -webkit-line-clamp: 1; max-height: 1.4em; }
    .columns-view { flex-grow: 1; display: flex; overflow: auto; padding: 8px; gap: 8px; cursor: grab; }
    .column { flex: 0 0 160px; display: flex; flex-direction: column; background-color: var(--taskbar-button-bg); border-radius: 4px; border: 1px solid var(--border-color); overflow: hidden; }
    .column.files-column { flex: 0 0 328px; }
    .columns-view.tile-mode .column:not(.files-column) { flex: 0 0 174px; }
    .columns-view.tile-mode .column-content { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 4px; align-content: start; }
    .column-header { padding: 4px 6px; font-weight: bold; cursor: pointer; color: white; flex-shrink: 0; display: flex; align-items: center; gap: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .column-header:hover { filter: brightness(1.2); }
    .column-content { flex-grow: 1; overflow-y: auto; padding: 4px; }
    .column-content-item { padding: 2px 6px; border-radius: 2px; cursor: pointer; display: flex; align-items: center; gap: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .column-content-item:hover { background-color: var(--taskbar-button-hover-bg); }
    .column-item-icon { flex-shrink: 0; }
    .column-item-name { flex-grow: 1; overflow: hidden; text-overflow: ellipsis; }
    .column-header-nav-up { flex-shrink: 0; }
    @keyframes green-pop-tile { 0% { transform: scale(0.5); opacity: 0; box-shadow: 0 0 30px 10px rgba(39, 174, 96, 0.9); } 50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 15px 5px rgba(39, 174, 96, 0.6); } 100% { transform: scale(1); opacity: 1; box-shadow: none; } }
    @keyframes blue-pulse-tile { 0% { transform: scale(1); box-shadow: none; } 25% { transform: scale(1.05); box-shadow: 0 0 25px 8px rgba(41, 128, 185, 0.8); } 50% { transform: scale(0.95); box-shadow: none; } 75% { transform: scale(1.05); box-shadow: 0 0 25px 8px rgba(41, 128, 185, 0.8); } 100% { transform: scale(1); box-shadow: none; } }
    @keyframes red-implode-tile { from { transform: scale(1) rotate(0deg); opacity: 1; box-shadow: 0 0 20px 5px rgba(231, 76, 60, 0.8); } to { transform: scale(0) rotate(90deg); opacity: 0; box-shadow: none; } }
    .tile-item.new, .nested-dir-container.new { animation: green-pop-tile 1.2s ease-out; }
    .tile-item.modified, .nested-dir-container.modified { animation: blue-pulse-tile 1.2s ease-in-out; }
    .tile-item.removed, .nested-dir-container.removed { animation: red-implode-tile 1s ease-in forwards; pointer-events: none; }
    @keyframes green-flash-list { from { background-color: rgba(39, 174, 96, 0.4); } to { background-color: transparent; } }
    @keyframes blue-flash-list { from { background-color: rgba(41, 128, 185, 0.4); } to { background-color: transparent; } }
    @keyframes red-flash-list { from { background-color: rgba(231, 76, 60, 0.5); opacity: 1; } to { background-color: rgba(231, 76, 60, 0); transform: translateX(-30px); opacity: 0; } }
    .item.new, .column-content-item.new { animation: green-flash-list 1.5s ease-out; }
    .item.modified, .column-content-item.modified { animation: blue-flash-list 1.5s ease-out; }
    .item.removed, .column-content-item.removed { animation: red-flash-list 1s ease-out forwards; pointer-events: none; }
    .context-menu { position: fixed; background-color: var(--window-bg); border: 1px solid var(--border-color); border-radius: 4px; box-shadow: 0 3px 10px rgba(0,0,0,0.2); z-index: 10001; display: flex; flex-direction: column; padding: 4px 0; min-width: 120px; }
    .context-menu button { background: none; border: none; color: var(--taskbar-text); padding: 8px 12px; text-align: left; cursor: pointer; font-size: 14px; }
    .context-menu button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(2px); display: flex; justify-content: center; align-items: center; z-index: 100; }
    .modal-content { background-color: var(--window-bg); padding: 20px; border-radius: 5px; border: 1px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.4); width: 90%; max-width: 450px; display: flex; flex-direction: column; gap: 15px; }
    .modal-content h3 { margin: 0; color: var(--title-bar-text); font-weight: 500; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
    fieldset { border: 1px solid var(--border-color); border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    legend { color: var(--title-bar-text); padding: 0 5px; }
    .modal-content label { display: flex; align-items: center; gap: 8px; }
    .modal-content input[type="text"] { background-color: var(--console-bg); border: 1px solid var(--border-color); color: var(--title-bar-text); padding: 8px; border-radius: 3px; font-family: monospace; width: 100%; box-sizing: border-box; }
    .path-input-container { padding-left: 20px; }
    .buttons { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
    .modal-content button { padding: 8px 16px; border-radius: 3px; cursor: pointer; border: 1px solid var(--border-color); color: var(--title-bar-text); background-color: var(--taskbar-button-bg); }
    .modal-content button:hover { background-color: var(--taskbar-button-hover-bg); }
    .modal-content .save-button { background-color: #27c93f; border-color: #1a9c2a; color: white; }
    .modal-content .save-button:hover { background-color: #1a9c2a; }
</style>

{#if !treeNode}
<div class="explorer-container">
    <div class="path-bar">
        <span class="path-text" title={currentPath}>{currentPath}</span>
        <div class="right-controls">
            {#if pickerTargetId}
                <button on:click={selectCurrentPath}>Select Current Folder</button>
            {/if}
            <div class="controls-group">
                <div class="color-mode-selector">
                    <label title="Color by file type"><input type="radio" bind:group={colorMode} value={'type'}> Type</label>
                    <label title="Color by modification time"><input type="radio" bind:group={colorMode} value={'age'}> Age</label>
                </div>
                <div class="view-mode-selector">
                    <button class="view-button" class:active={columnsEnabled} on:click={() => toggleWithRefetch('columns')} title="Toggle Columns View" disabled={!supportsRecursive}>◫</button>
                </div>
                <div class="view-mode-selector">
                    <button class="view-button" class:active={viewMode === 'list'} on:click={() => switchViewMode('list')} title="List View">☰</button>
                    <button class="view-button" class:active={viewMode === 'tiles'} on:click={() => switchViewMode('tiles')} title="Tiles View">⊞</button>
                </div>
                 <button class="watch-button" class:active={nestedView} on:click={() => toggleWithRefetch('nested')} title="Toggle Nested View" disabled={!supportsRecursive}>Nested</button>
                 <button class="watch-button" class:active={isWatching} on:click={toggleWatch} title="Watch for live updates" disabled={!supportsWatch}>
                    {isWatching ? 'Watching' : 'Watch'} 👀
                </button>
            </div>
        </div>
    </div>
    {#if errorMessage}
        <div class="error-message">{errorMessage}</div>
    {/if}

    {#if columnsEnabled && supportsRecursive}
        <div class="columns-view" bind:this={columnsContainer} on:mousedown={handlePanStart} on:wheel={handleWheelScroll} class:tile-mode={viewMode === 'tiles'}>
            {#if currentPath !== '/' || columnFiles.length > 0}
                <div class="column files-column">
                    <div class="column-header" on:click={currentPath !== '/' ? () => handleItemClick({name: '..', type: 'dir'}) : undefined} on:contextmenu={e => handleRightClick(e, {name: '..', type: 'dir'})} title={currentPath !== '/' ? 'Parent Directory' : 'Root Directory'} style:background-color={getTileColor({name: '..', type: 'dir'}, colorMode)} style:cursor={currentPath !== '/' ? 'pointer' : 'default'}>
                        <span class="column-item-icon">🗂️</span>
                        <span class="column-item-name">{currentPath}</span>
                        <span class="column-header-nav-up">{#if currentPath !== '/'}..{/if}</span>
                    </div>
                    <div class="column-content">
                        {#if viewMode === 'list'}
                             {#each columnFiles as file (file.path)}
                                <div class="column-content-item" on:click={() => handleItemClick(file)} on:contextmenu={e => handleRightClick(e, file)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, file)} title={file.name} style="color: {getTileColor(file, colorMode)}" class:new={itemChangeStatus[file.path] === 'new'} class:modified={itemChangeStatus[file.path] === 'modified'} class:removed={itemChangeStatus[file.path] === 'removed'}>
                                    <span class="column-item-icon">📄</span>
                                    <span class="column-item-name">{file.name}</span>
                                </div>
                            {/each}
                        {:else}
                            {#each columnFiles as file (file.path)}
                                <div class="tile-item nested-tile" on:click={() => handleItemClick(file)} on:contextmenu={e => handleRightClick(e, file)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, file)} title={file.name} style:background-color={getTileColor(file, colorMode)} class:new={itemChangeStatus[file.path] === 'new'} class:modified={itemChangeStatus[file.path] === 'modified'} class:removed={itemChangeStatus[file.path] === 'removed'}>
                                    <div class="tile-icon">📄</div>
                                    <div class="tile-name">{file.name}</div>
                                </div>
                            {/each}
                        {/if}
                    </div>
                </div>
            {/if}
            {#each columnDirs as item (item.path)}
                {@const isNestedListColumn = nestedView && viewMode === 'list'}
                {@const maxDepth = isNestedListColumn ? getMaxExpandedDepth(item) : 0}
                {@const columnWidth = 160 + maxDepth * 20}
                <div class="column" style={isNestedListColumn ? `flex-basis: ${columnWidth}px;` : ''}>
                    <div class="column-header" on:click={() => handleItemClick(item)} on:contextmenu={e => handleRightClick(e, item)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, item)} title={item.name} style:background-color={getTileColor(item, colorMode)}>
                        <span class="column-item-icon">🗂️</span>
                        <span class="column-item-name">{item.name}</span>
                    </div>
                    {#if item.type === 'dir' && item.children && item.children.length > 0}
                        <div class="column-content">
                             {#if nestedView}
                                {#each item.children as child (child.path)}
                                    <svelte:self treeNode={child} treeLevel={0} {viewMode} {colorMode} {getTileColor} {handleItemClick} {toggleNode} bind:expandedNodes {itemChangeStatus} {columnsEnabled} {nestedView} {consoleId} {handleRightClick} {handleDragStart} {connectionType}/>
                                {/each}
                             {:else}
                                {#if viewMode === 'list'}
                                    {#each item.children as child (child.path)}
                                        <div class="column-content-item" on:click={() => handleItemClick(child)} on:contextmenu={e => handleRightClick(e, child)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, child)} title={child.name} style="color: {getTileColor(child, colorMode)}" class:new={itemChangeStatus[child.path] === 'new'} class:modified={itemChangeStatus[child.path] === 'modified'} class:removed={itemChangeStatus[child.path] === 'removed'}>
                                            <span class="column-item-icon">{child.type === 'dir' ? '🗂️' : '📄'}</span>
                                            <span class="column-item-name">{child.name}</span>
                                        </div>
                                    {/each}
                                {:else}
                                    {#each item.children as child (child.path)}
                                        <div class="tile-item nested-tile" on:click={() => handleItemClick(child)} on:contextmenu={e => handleRightClick(e, child)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, child)} title={child.name} style:background-color={getTileColor(child, colorMode)} class:new={itemChangeStatus[child.path] === 'new'} class:modified={itemChangeStatus[child.path] === 'modified'} class:removed={itemChangeStatus[child.path] === 'removed'}>
                                            <div class="tile-icon">{child.type === 'dir' ? '🗂️' : '📄'}</div>
                                            <div class="tile-name">{child.name}</div>
                                        </div>
                                    {/each}
                                {/if}
                             {/if}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {:else}
        {#if viewMode === 'list'}
            <div class="item-list">
                {#if nestedView && supportsRecursive}
                    {#if currentPath !== '/'}
                        <div class="item" on:click={() => handleItemClick({name: '..', type: 'dir'})} on:contextmenu={e => handleRightClick(e, {name: '..', type: 'dir'})} title="Parent Directory">
                            <span class="item-icon">🗂️</span>
                            <span class="item-name">..</span>
                        </div>
                    {/if}
                    {#each treeItems as item (item.path)}
                        <svelte:self treeNode={item} treeLevel={0} {viewMode} {colorMode} {getTileColor} {handleItemClick} {toggleNode} bind:expandedNodes {itemChangeStatus} {columnsEnabled} {nestedView} {consoleId} {handleRightClick} {handleDragStart} {connectionType}/>
                    {/each}
                {:else}
                    {#each items as item (item.name)}
                        <div class="item" on:click={() => handleItemClick(item)} on:contextmenu={e => handleRightClick(e, item)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, item)} title={item.name} style="color: {getTileColor(item, colorMode)}" class:new={itemChangeStatus[item.name] === 'new'} class:modified={itemChangeStatus[item.name] === 'modified'} class:removed={itemChangeStatus[item.name] === 'removed'}>
                            <span class="item-icon">{item.type === 'dir' ? '🗂️' : '📄'}</span>
                            <span class="item-name">{item.name}</span>
                            <span class="item-size">{#if item.type === 'file' && item.size >= 0}{item.size}{/if}</span>
                        </div>
                    {/each}
                {/if}
            </div>
        {:else if viewMode === 'tiles'}
            <div class="tile-grid">
                {#if nestedView && supportsRecursive}
                    {#if currentPath !== '/'}
                        <div class="tile-item" on:click={() => handleItemClick({name: '..', type: 'dir'})} on:contextmenu={e => handleRightClick(e, {name: '..', type: 'dir'})} title="Parent Directory" style:background-color={getTileColor({name: '..', type: 'dir'}, colorMode)}>
                            <div class="tile-icon">🗂️</div>
                            <div class="tile-name">..</div>
                        </div>
                    {/if}
                     {#each treeItems as item (item.path)}
                        {#if item.type === 'file'}
                             <div class="tile-item" on:click={() => handleItemClick(item)} on:contextmenu={e => handleRightClick(e, item)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, item)} title={item.name} style:background-color={getTileColor(item, colorMode)} class:new={itemChangeStatus[item.path] === 'new'} class:modified={itemChangeStatus[item.path] === 'modified'} class:removed={itemChangeStatus[item.path] === 'removed'}>
                                <div class="tile-icon">📄</div>
                                <div class="tile-name">{item.name}</div>
                            </div>
                        {:else if item.type === 'dir'}
                            <div class="nested-dir-container" on:contextmenu={e => handleRightClick(e, item)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, item)} title={item.name} style:border-color={getTileColor(item, colorMode)} class:new={itemChangeStatus[item.path] === 'new'} class:modified={itemChangeStatus[item.path] === 'modified'} class:removed={itemChangeStatus[item.path] === 'removed'}>
                                <div class="nested-dir-name" style:background-color={getTileColor(item, colorMode)} style:cursor="pointer" on:click={() => handleItemClick(item)}>{item.name}</div>
                                <div class="nested-dir-content-grid">
                                    {#if item.children && item.children.length > 0}
                                        {#each item.children as child (child.path)}
                                            <svelte:self treeNode={child} treeLevel={treeLevel + 1} {viewMode} {colorMode} {getTileColor} {handleItemClick} {toggleNode} bind:expandedNodes {itemChangeStatus} {columnsEnabled} {nestedView} {consoleId} {handleRightClick} {handleDragStart} {connectionType}/>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                        {/if}
                     {/each}
                {:else}
                    {#each items as item (item.name)}
                        <div class="tile-item" on:click={() => handleItemClick(item)} on:contextmenu={e => handleRightClick(e, item)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, item)} title={item.name} style:background-color={getTileColor(item, colorMode)} class:new={itemChangeStatus[item.name] === 'new'} class:modified={itemChangeStatus[item.name] === 'modified'} class:removed={itemChangeStatus[item.name] === 'removed'}>
                            <div class="tile-icon">{item.type === 'file' ? '📄' : '🗂️'}</div>
                            <div class="tile-name">{item.name}</div>
                        </div>
                    {/each}
                {/if}
            </div>
        {/if}
    {/if}

    {#if contextMenu.visible}
    <div class="context-menu" style="top: {contextMenu.y}px; left: {contextMenu.x}px;" on:click|stopPropagation>
        <button on:click={onAsk}>Ask...</button>
        {#if connectionType === 'skybridge' && contextMenu.item && contextMenu.item.type === 'dir'}
            <button on:click={onBoxThis}>Box this</button>
        {/if}
    </div>
    {/if}

    <WindowSettingsModal bind:show={showSettings} title="File Explorer Settings" {componentName} {x} {y} {width} {height} on:save={handleSaveComponentSettings}>
        <fieldset>
            <legend>Initial Directory</legend>
            <label><input type="radio" bind:group={settingsModel.usePwd} value={true}> Current working directory (.)</label>
            <label><input type="radio" bind:group={settingsModel.usePwd} value={false}> Specific path</label>
            {#if !settingsModel.usePwd}
            <div class="path-input-container"><input type="text" bind:value={settingsModel.path} placeholder="e.g., /home/user"></div>
            {/if}
        </fieldset>
    </WindowSettingsModal>
</div>
{:else}
    {#if viewMode === 'list'}
        <div class="tree-node-container" style="--level: {treeLevel}">
            <div class="item tree-item" on:click={() => { if (treeNode.type === 'dir') toggleNode(treeNode.path); else handleItemClick(treeNode); }} on:contextmenu={e => handleRightClick(e, treeNode)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, treeNode)} style="color: {getTileColor(treeNode, colorMode)}" class:new={itemChangeStatus[treeNode.path] === 'new'} class:modified={itemChangeStatus[treeNode.path] === 'modified'} class:removed={itemChangeStatus[treeNode.path] === 'removed'}>
                <span class="tree-node-expander">
                    {#if treeNode.type === 'dir' && treeNode.children.length > 0}
                        {expandedNodes.has(treeNode.path) ? '▼' : '►'}
                    {/if}
                </span>
                <span class="item-icon">{treeNode.type === 'dir' ? '🗂️' : '📄'}</span>
                <span class="item-name">{treeNode.name}</span>
                 {#if !(columnsEnabled && nestedView)}
                     <span class="item-size">{#if treeNode.type === 'file' && treeNode.size >= 0}{treeNode.size}{/if}</span>
                 {/if}
            </div>
            {#if treeNode.children && treeNode.children.length > 0 && expandedNodes.has(treeNode.path)}
                {#each treeNode.children as child}
                    <svelte:self treeNode={child} treeLevel={treeLevel + 1} {viewMode} {colorMode} {getTileColor} {handleItemClick} {toggleNode} bind:expandedNodes {itemChangeStatus} {columnsEnabled} {nestedView} {consoleId} {handleRightClick} {handleDragStart} {connectionType}/>
                {/each}
            {/if}
        </div>
    {:else if viewMode === 'tiles'}
        {#if treeNode.type === 'file'}
            <div class="tile-item nested-tile" on:click={() => handleItemClick(treeNode)} on:contextmenu={e => handleRightClick(e, treeNode)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, treeNode)} title={treeNode.name} style:background-color={getTileColor(treeNode, colorMode)} class:new={itemChangeStatus[treeNode.path] === 'new'} class:modified={itemChangeStatus[treeNode.path] === 'modified'} class:removed={itemChangeStatus[treeNode.path] === 'removed'}>
                <div class="tile-icon">📄</div>
                <div class="tile-name">{treeNode.name}</div>
            </div>
        {:else if treeNode.type === 'dir'}
            <div class="nested-dir-container" on:contextmenu={e => handleRightClick(e, treeNode)} draggable={connectionType === 'skybridge'} on:dragstart={e => handleDragStart(e, treeNode)} title={treeNode.name} style:border-color={getTileColor(treeNode, colorMode)} class:new={itemChangeStatus[treeNode.path] === 'new'} class:modified={itemChangeStatus[treeNode.path] === 'modified'} class:removed={itemChangeStatus[treeNode.path] === 'removed'}>
                <div class="nested-dir-name" style:background-color={getTileColor(treeNode, colorMode)} style:cursor="pointer" on:click={() => handleItemClick(treeNode)}>{treeNode.name}</div>
                <div class="nested-dir-content-grid">
                    {#if treeNode.children && treeNode.children.length > 0}
                        {#each treeNode.children as child (child.path)}
                            <svelte:self treeNode={child} treeLevel={treeLevel + 1} {viewMode} {colorMode} {getTileColor} {handleItemClick} {toggleNode} bind:expandedNodes {itemChangeStatus} {columnsEnabled} {nestedView} {consoleId} {handleRightClick} {handleDragStart} {connectionType}/>
                        {/each}
                    {/if}
                </div>
            </div>
        {/if}
    {/if}
{/if}