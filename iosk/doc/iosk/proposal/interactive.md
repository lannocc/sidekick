# Proposal: A Rich Interactive Console Experience

### Introduction

The current IOSK console provides a basic, line-by-line interactive experience for the superuser. While functional, it suffers from several usability limitations common to simple `input`/`print` loops:

1.  **Input Interruption**: Asynchronous output, such as a chat message from another user or a system notification, is printed directly to the console, interrupting and overwriting whatever the user is currently typing.
2.  **Lack of Standard Features**: The console does not support common shell features that users expect, most notably the ability to navigate command history using the up and down arrow keys.
3.  **Inefficient Layout**: The entire screen scrolls as a single unit, making it difficult to reference previous output while composing a new command.

This proposal outlines a plan to replace the current console with a modern, full-screen, rich interactive experience. The new console will feature a fixed input prompt at the bottom of the screen and a separate, scrollable region for all system and chat output. This will be achieved by integrating the `prompt_toolkit` library, a powerful tool designed specifically for building advanced, asynchronous command-line interfaces.

### Core Concepts

1.  **Full-Screen Application Layout**: Instead of treating the terminal as a simple line-based stream, we will manage the entire screen as a dedicated application space. Using `prompt_toolkit`'s layout engine, we can divide the screen into two primary components:
    *   **Output Pane**: A large, scrollable window at the top that displays all command output, system messages, and incoming chat.
    *   **Input Buffer**: A fixed, single- or multi-line input area at the bottom where the user types their commands. This area will remain static and focused, regardless of activity in the output pane.

2.  **Asynchronous I/O Handling**: A key requirement is handling asynchronous output without disrupting the user. `prompt_toolkit` is designed to work seamlessly with `asyncio`. The new console implementation will run an application loop that can simultaneously:
    *   Await user input from the keyboard in the input buffer.
    *   Receive data from other parts of the IOSK system (e.g., chat messages) and render it into the output pane, triggering a screen redraw without disturbing the input buffer's content or cursor position.

3.  **Integrated History Management**: The `prompt_toolkit` library has built-in support for command history. We will connect its `History` object directly to the `io.history` list that already exists in the user's `Context`. This makes implementing history navigation via the up and down arrow keys a trivial configuration step.

4.  **Extensible Key Bindings**: This implementation immediately provides standard key bindings. It also creates a foundation for easily adding more advanced shell features in the future, such as `Ctrl+C` for graceful interruption, `Ctrl+D` for logout, and `Tab` for command/path auto-completion.

### Implementation Strategy

The majority of this work will be isolated to `dev/console.py`, treating the console as the pluggable device it is, with minimal changes required in the kernel.

#### 1. Add Dependency

First, `prompt_toolkit` must be added as a new dependency to the project.

#### 2. Rearchitect `dev/console.py`

The current `aioconsole`-based implementation will be replaced with a new class-based approach that encapsulates the `prompt_toolkit` application.
```python
# A conceptual sketch for the new dev/console.py

import asyncio
from prompt_toolkit import Application
from prompt_toolkit.layout import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory

# This queue will bridge async output from the kernel to the UI
output_queue = asyncio.Queue()

# The global iorecv and iosend functions will interact with an instance
# of this RichConsole class.
console_app = None

async def iosend(io, data):
    """Called by the kernel to display output."""
    await output_queue.put(data)

async def iorecv(io):
    """Called by the kernel to get user input."""
    global console_app
    if not console_app:
        # One-time setup
        console_app = RichConsole(io.history)
        asyncio.create_task(console_app.run())

    return await console_app.get_input()

class RichConsole:
    def __init__(self, command_history_list):
        self.history = InMemoryHistory()
        for cmd in command_history_list:
            self.history.append_string(cmd)

        self.input_buffer = Buffer(history=self.history, multiline=False)
        self.output_buffer = [] # A simple list to hold lines of output
        self.input_future = None

        # 1. Define the Layout
        self.layout = HSplit([
            Window(content=FormattedTextControl(self._get_output_text)),
            Window(height=1, char='-'),
            Window(height=1, content=BufferControl(buffer=self.input_buffer)),
        ])

        # 2. Define Key Bindings
        kb = KeyBindings()
        @kb.add('c-c')
        @kb.add('c-d')
        def _(event):
            # Handle Ctrl-C/Ctrl-D for exit
            event.app.exit(result=None)

        @kb.add('enter')
        def _(event):
            text = self.input_buffer.text
            self.history.append_string(text)
            self.input_buffer.reset()
            if self.input_future and not self.input_future.done():
                self.input_future.set_result(text)

        # 3. Create the Application Instance
        self.app = Application(layout=self.layout, key_bindings=kb, full_screen=True)

    def _get_output_text(self):
        # This function provides the content for the top pane
        return '\n'.join(self.output_buffer)

    async def run(self):
        """The main UI loop for the console."""
        # Task to consume from the output_queue and update the UI
        async def output_consumer():
            while True:
                data = await output_queue.get()
                self.output_buffer.extend(data.splitlines())
                # Limit scrollback if needed
                if len(self.output_buffer) > 1000:
                    self.output_buffer = self.output_buffer[-1000:]
                self.app.invalidate() # Trigger a redraw

        output_task = asyncio.create_task(output_consumer())

        # Run the prompt_toolkit application
        await self.app.run_async()

        # Cleanup
        output_task.cancel()

    async def get_input(self):
        """Waits for the user to press Enter."""
        self.input_future = asyncio.get_event_loop().create_future()
        prompt_text = f"[{console_app.app.current_buffer.name}] >> " # Example prompt
        # The actual prompt is managed visually by the layout
        result = await self.input_future
        return result
```

#### 3. Kernel Integration

The `IOSK.interactive` loop in `src/iosk/kernel.py` requires almost no changes. It will continue to call `io.input()` and `io.print()`, but these calls will now be routed through our new `prompt_toolkit` implementation in `dev/console.py` when the user is `root` on `/dev/console`. The initial setup of the `RichConsole` application will be triggered by the first call to `iorecv`.

### Benefits

*   **Greatly Improved Usability**: The console becomes a professional, non-disruptive workspace. Users will no longer lose their work-in-progress commands when an asynchronous message arrives.
*   **Expected Shell Features**: History navigation is a fundamental quality-of-life feature that makes the shell significantly more efficient to use.
*   **Strong Foundation for Future UI Enhancements**: This architecture makes it straightforward to add more advanced features later, such as:
    *   Auto-completion for commands, arguments, and file paths.
    *   Syntax highlighting for the command line.
    *   Status bars for displaying system information.
*   **Architectural Purity**: This change is almost entirely contained within the `/dev/console.py` device driver, reinforcing the modular design of IOSK where devices are pluggable components.

By implementing this proposal, we will elevate the IOSK console from a simple proof-of-concept to a powerful and user-friendly interface suitable for serious interactive use.

