# Proposal: Codebase Refactoring for Maintainability

**Author:** LANNOCC
**Date:** November 19, 2025
**Status:** Implemented

## 1. Introduction & Motivation

Our codebase has grown to support a rich set of features, but this growth has introduced areas of redundancy and structural complexity. To ensure the long-term health, maintainability, and ease of comprehension of our project—both for human developers and AI agents—a focused refactoring effort is necessary.

This proposal outlines a series of refactoring tasks aimed at improving code structure, reducing duplication, and enhancing clarity. **Crucially, none of the proposed changes will alter the existing functionality of the application.** The sole purpose is to improve the internal quality of the code, making it more robust and easier to build upon in the future.

## 2. Python Backend Refactoring (`sk/`)

### 2.1. Agent Module Consolidation

**Problem:**
The agent modules in `sk/agent/` (`browser.py`, `control.py`, `speech.py`, etc.) contain significant boilerplate repetition.
1.  Each module defines a `prompt_for_action` function that is nearly identical, only differing in the `PRE_PROMPT` and `META_PROMPT` variables it uses.
2.  The `do_help` method within each module's `Actions` class is identical, delegating to `agent.just_do_it`.

**Proposed Solution:**
1.  **Create a common agent helper.** A new file, `sk/agent/common.py`, will be created. It will contain a helper function:
    ```python
    # in sk/agent/common.py
    def create_action_prompter(pre_prompt, meta_prompt):
        def prompt_for_action(text, quiet=False, chatter=False):
            if not quiet: print(f'      >> {text}')
            actions = ai.prompt_for_json(pre_prompt + meta_prompt + text, chatter=chatter)
            if not quiet: print(f'      << {actions}')
            # The 'Actions' class will be resolved in the local scope of the calling module.
            return Actions(actions)
        return prompt_for_action
    ```
    Each agent module will then import and use this factory to generate its `prompt_for_action` function, eliminating ~8 lines of duplicated code per module.

2.  **Move `do_help` to a base class.** The `ActionsBase` class in `sk/action/__init__.py` will be augmented with the generic `do_help` implementation. All agent `Actions` classes already inherit from it, so they will gain this method automatically and it can be removed from each agent file.

### 2.2. AI Provider Abstraction

**Problem:**
The files `sk/ai/google.py` and `sk/ai/openai.py` provide parallel APIs. The main command logic in `sk/cmd.py` contains conditional logic (`if use_openai: ... else: ...`) to select which provider's functions to call. This will become more complex with the streaming functions planned in the "CoolStream" proposal.

**Proposed Solution:**
Create a unified AI client that abstracts the provider-specific implementation. A new file, `sk/ai/client.py`, will be introduced.

```python
# in sk/ai/client.py
from . import google, openai

class AIClient:
    def __init__(self, use_openai=False):
        self.provider = openai if use_openai else google

    def prompt_for_text(self, *args, **kwargs):
        return self.provider.prompt_for_text(*args, **kwargs)

    def prompt_for_json(self, *args, **kwargs):
        return self.provider.prompt_for_json(*args, **kwargs)

    # ... other methods like prompt_with_file_for_text ...
```

The `ask_question` function in `sk/cmd.py` will be simplified to instantiate this single client:
`ai_client = AIClient(use_openai=use_openai)`
All subsequent calls will be to `ai_client.prompt_for_text(...)`, removing the `if/else` blocks.

### 2.3. `sk/cmd.py` Decomposition

**Problem:**
The `sk/cmd.py` file has become a monolithic entity responsible for:
1.  Complex command-line argument parsing for `sk`, `ask`, and `task`.
2.  The complete implementation logic for `ask_question` and `do_task`.
3.  The implementations for all `sk` subcommands (`tree`, `ask`, `task`, etc.).

Furthermore, `ask_question` and `do_task` share nearly identical setup code for handling attachments (`-s`, `-a`, package paths).

**Proposed Solution:**
1.  **Move bigger subcommands to separate files.** The logic for bigger subcommand (`ask` and `task`) will be moved into its own file (e.g., `sk/ask.py`).
2.  **Extract attachment handling.** A new private helper function, `_prepare_prompt_and_attachment(...)`, will be created within `sk/cmd.py`. This function will encapsulate the shared logic for handling screenshots, file attachments, and directory packaging, returning the final `file` path and attachment content. Both `ask_question` and `do_task` will call this helper, reducing code duplication.

### 2.4. Utility Function Consolidation

**Problem:**
The `sk/util.py` file contains two functions, `get_directory_contents_as_text` and `package_directory`, that both contain nearly identical blocks of code for reading a file and formatting it into a `>>> BEGIN FILE...` block.

**Proposed Solution:**
Extract this common logic into a new, single helper function `_get_formatted_file_content(full_path)` within `sk/util.py`. Both `get_directory_contents_as_text` and `package_directory` will be updated to call this new helper function.

## 3. Svelte Frontend Refactoring (`sv/`)

### 3.1. Reusable Window Settings Modal

**Problem:**
The UI and logic for the "Default Window Position & Size" settings modal are duplicated across multiple components: `IoskConsole.svelte`, `IoskFileExplorer.svelte`, `WebBrowser.svelte`, `Settings.svelte`, and `Window.svelte`. This makes simple UI changes to the modal a tedious, multi-file effort.

**Proposed Solution:**
Create a new, reusable component: `sv/popup/WindowSettingsModal.svelte`.
-   This component will accept the `componentName` and current window geometry as props.
-   It will manage its own internal state for the form fields.
-   On "Save", it will use the `windowSettings` store directly to save the settings for the given component name and then dispatch a `close` event.
-   All components currently implementing this modal will be refactored to simply import and render `<WindowSettingsModal>` when needed, removing a significant amount of duplicated markup and logic from each file.

### 3.2. Centralized ANSI Parsing Utility

**Problem:**
The function to parse ANSI escape codes into HTML is implemented separately in `IoskConsole.svelte`, `IoskWatch.svelte`, and `IoskPrivateChat.svelte`.

**Proposed Solution:**
Create a new utility file, `sv/ansi.js` (or add to an existing util file). The `parseAnsi` function will be moved here. All components that need to render ANSI-formatted text will import this single, canonical function.

### 3.3. `IoskConsole.svelte` Component Decomposition

**Problem:**
The `IoskConsole.svelte` file is excessively large (over 700 lines), managing WebSocket state, the main terminal UI, and multiple complex pop-up menus (Rooms, Attach, User Context). This violates the single-responsibility principle and makes the component difficult to maintain.

**Proposed Solution:**
Break `IoskConsole.svelte` into smaller, focused components:
1.  **`RoomsMenu.svelte`**: A new component to encapsulate the UI and logic for displaying and joining rooms.
2.  **`AttachMenu.svelte`**: A new component to manage the device/user selection UI for the `$ attach` command.
3.  **`UserContextMenu.svelte`**: A new component to handle the right-click context menu on usernames in the participant list.

The main `IoskConsole.svelte` component will become a container that conditionally renders these new components, passing data via props and listening for events. This will dramatically simplify its script and markup.

### 3.4. Abstracting Console Connection Logic

**Problem:**
Multiple components that depend on an IOSK connection (`IoskFileExplorer`, `IoskFileViewer`, `IoskWatch`, etc.) contain similar reactive logic (`$: if (consoleConnection && $windows) { ... }`) to find a valid `consoleId` after a Dash restore if their original connection is lost.

**Proposed Solution:**
Create a new store in `sv/iosk.js`.
-   This store will listen to the `windows` store and maintain an internal map of all active, connected `IoskConsole` tabs.
-   It will expose a function, e.g., `findConsole(connectionDetails)`, that components can call.
-   The reactive blocks in each component will be replaced by a simpler call to this manager, centralizing the logic for finding a compatible, active console session.

## 4. Conclusion

This refactoring plan systematically addresses the key areas of redundancy and complexity in our codebase. By abstracting common patterns, decomposing large components, and centralizing shared logic, we can significantly improve the maintainability, readability, and overall quality of our project. These changes will provide a cleaner foundation for future development and make the entire system easier for both human and AI developers to understand and modify, all while preserving the current functionality for our users.

