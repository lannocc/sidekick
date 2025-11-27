<!--
  Copyright (C) 2025 LANNOCC
  @%@~LICENSE~@%@
-->
<script>
    export let board_type;
    export let board_config;

    let containerEl;
    let previewScale = 1;
    let previewDesktop = { width: 0, height: 0, top: 0, left: 0 };

    $: if (board_type === 'dash' && board_config && containerEl) {
        const savedDesktopWidth = board_config.desktop?.width || 1920;
        const savedDesktopHeight = board_config.desktop?.height || 1080;
        const scaleX = containerEl.clientWidth / savedDesktopWidth;
        const scaleY = containerEl.clientHeight / savedDesktopHeight;
        previewScale = Math.min(scaleX, scaleY) * 0.95;
        const scaledWidth = savedDesktopWidth * previewScale;
        const scaledHeight = savedDesktopHeight * previewScale;
        previewDesktop = {
            width: scaledWidth, height: scaledHeight,
            left: (containerEl.clientWidth - scaledWidth) / 2,
            top: (containerEl.clientHeight - scaledHeight) / 2
        };
    }
</script>

<style>
    .board-container { width: 100%; height: 100%; overflow: hidden; background-color: rgba(0,0,0,0.15); border-radius: 5px; }
    .panel-image { width: 100%; height: 100%; object-fit: cover; }

    /* Mini Window/Tabs Styles */
    .mini-window { display: flex; flex-direction: column; width: 100%; height: 100%; font-size: 10px; }
    .mini-title-bar { flex-shrink: 0; display: flex; background-color: rgba(0,0,0,0.2); overflow: hidden; height: 20px; }
    .mini-tab { padding: 0 5px; color: rgba(255, 255, 255, 0.7); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 80px; border-right: 1px solid rgba(0,0,0,0.3); line-height: 20px; }
    .mini-tab.active { font-weight: bold; color: white; background-color: rgba(255,255,255,0.1); }
    .mini-content { flex-grow: 1; }

    /* Mini Dash Styles (from Dash.svelte) */
    .preview-screen { position: absolute; background-color: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 4px; }
    .preview-window { position: absolute; background-color: rgba(52, 152, 219, 0.5); border: 1px solid rgba(41, 128, 185, 0.8); border-radius: 2px; box-sizing: border-box; overflow: hidden; display: flex; flex-direction: column; }
    .preview-title-bar { display: flex; flex-shrink: 0; background-color: rgba(0,0,0,0.2); overflow: hidden; align-items: center; height: 14px; }
    .preview-tab { padding: 0 3px; font-size: 9px; line-height: 14px; color: rgba(255, 255, 255, 0.8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70px; border-right: 1px solid rgba(41, 128, 185, 0.4); text-shadow: 0 0 2px rgba(0,0,0,0.6); }
    .preview-tab.active { font-weight: bold; color: white; background-color: rgba(255,255,255,0.1); }
</style>

<div class="board-container" bind:this={containerEl}>
    {#if board_type === 'image' && board_config?.url}
        <img src={board_config.url} alt="Box Panel Content" class="panel-image"/>
    {:else if (board_type === 'window' || board_type === 'tabs') && board_config?.tabs}
        {@const group = board_config}
        <div class="mini-window">
            <div class="mini-title-bar">
                {#each group.tabs as tab (tab.originalId)}
                    <div class="mini-tab" class:active={tab.originalId === group.activeTabId} title={tab.title}>
                        {tab.title}
                    </div>
                {/each}
            </div>
            <div class="mini-content" />
        </div>
    {:else if board_type === 'dash' && board_config?.windowGroups && previewDesktop.width > 0}
         <div class="preview-screen" style:width="{previewDesktop.width}px" style:height="{previewDesktop.height}px" style:top="{previewDesktop.top}px" style:left="{previewDesktop.left}px">
            {#each (board_config.windowGroups || []) as group}
                {@const isMaximized = group.maximized}
                <div class="preview-window" title={group.tabs.map(t => t.title).join(' | ')} style:left="{isMaximized ? 0 : (group.x * previewScale)}px" style:top="{isMaximized ? 0 : (group.y * previewScale)}px" style:width="{isMaximized ? '100%' : Math.max(20, group.width * previewScale)}px" style:height="{isMaximized ? '100%' : Math.max(16, group.height * previewScale)}px">
                    <div class="preview-title-bar">
                        {#each group.tabs as tab (tab.originalId)}
                            <div class="preview-tab" class:active={tab.originalId === group.activeTabId} title={tab.title}>
                                {tab.title}
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>