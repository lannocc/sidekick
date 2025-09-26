import asyncio

from prompt_toolkit import Application
# CORRECT: Import Layout
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
# The 'Token' import is removed as it no longer exists in prompt-toolkit >= 3.0
# from prompt_toolkit.token import Token

# This queue will bridge async output from the kernel to the UI
output_queue = asyncio.Queue()

# The global iorecv and iosend functions will interact with an instance of this RichConsole class.
console_app_instance = None

async def iosend(io, data):
    """Called by the kernel to display output."""
    await output_queue.put(data)

async def iorecv(io, prompt=None):
    """Called by the kernel to get user input."""
    global console_app_instance
    if not console_app_instance:
        # One-time setup
        console_app_instance = RichConsole(io.history)
        # The run method is non-blocking and is launched as a background task.
        asyncio.create_task(console_app_instance.run())

    return await console_app_instance.get_input(prompt or "")

class RichConsole:
    def __init__(self, command_history_list):
        self.history = InMemoryHistory()
        for cmd in command_history_list:
            self.history.append_string(cmd)

        self.input_buffer = Buffer(history=self.history, multiline=False, accept_handler=self.accept_input)
        self.output_lines = []
        self.input_future = None
        self.current_prompt = ""

        # Style for the prompt
        style = Style.from_dict({
            'prompt': 'bold',
            'separator': 'fg:ansiblue',
        })

        # 1. Define the Layout
        # CORRECT: Define the input window separately so we can reference it for focus.
        input_window = Window(
            content=BufferControl(buffer=self.input_buffer),
            get_line_prefix=self._get_prompt_tokens,
            height=1
        )

        # Create the main container
        root_container = HSplit([
            # The output window (scrollable)
            Window(content=FormattedTextControl(self._get_output_text), wrap_lines=True),
            # A separator line
            Window(height=1, char='─', style='class:separator'),
            # The input window (fixed at the bottom)
            input_window,
        ])

        # CORRECT: Wrap the container in a Layout object and set the focus.
        self.layout = Layout(container=root_container, focused_element=input_window)


        # 2. Define Key Bindings
        kb = KeyBindings()
        @kb.add('c-c')
        @kb.add('c-d')
        def _(event):
            """ Handle Ctrl-C/Ctrl-D for exit/EOF """
            if self.input_future and not self.input_future.done():
                # If we're actively waiting for input, raise EOFError to allow a clean exit
                # from the kernel's interactive loop.
                self.input_future.set_exception(EOFError())
            else:
                # If not actively waiting for input, just exit the application.
                event.app.exit(result=None)

        # The 'enter' key is handled by the Buffer's accept_handler for cleaner logic.

        # 3. Create the Application Instance
        self.app = Application(layout=self.layout, key_bindings=kb, style=style, full_screen=True)

    def _get_output_text(self):
        # This function provides the content for the top output pane.
        # prompt-toolkit now expects a list of (style, text) tuples.
        # For simple unstyled text, you can either return a plain string
        # or a list like [("", line)] for each line.
        # A plain string is simpler and works fine here.
        return '\n'.join(self.output_lines)

    # CORRECTED: The signature for a `get_line_prefix` callable requires
    # line_number and wrap_count arguments.
    def _get_prompt_tokens(self, line_number, wrap_count):
        # This function provides the tokens for the input prompt.
        # The old Token object is replaced by a simple style string.
        # This string 'prompt' maps directly to the key in the Style.from_dict call.
        return [('class:prompt', self.current_prompt)]

    def accept_input(self, buff):
        """Callback executed when the user presses Enter."""
        text = self.input_buffer.text
        if self.input_future and not self.input_future.done():
            self.input_future.set_result(text)
        # History is managed by the Buffer, so we don't manually append.
        return True # Return True to keep the buffer for the next input.

    async def run(self):
        """The main UI loop for the console."""
        # This task consumes from the output_queue and updates the UI.
        async def output_consumer():
            while True:
                try:
                    data = await output_queue.get()
                    if not isinstance(data, str):
                        data = str(data)

                    self.output_lines.extend(data.splitlines())
                    # Limit scrollback history to prevent excessive memory use.
                    if len(self.output_lines) > 2000:
                        self.output_lines = self.output_lines[-2000:]

                    if self.app.is_running:
                        self.app.invalidate() # Trigger a UI redraw.

                    output_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception:
                    # Log errors if necessary, but don't crash the consumer task.
                    pass

        output_task = asyncio.create_task(output_consumer())

        try:
            # Run the prompt_toolkit application.
            await self.app.run_async()
        finally:
            # Cleanly shut down the consumer task when the app exits.
            output_task.cancel()

    async def get_input(self, prompt=""):
        """Waits for the user to press Enter and returns the input."""
        if self.input_future and not self.input_future.done():
            return await self.input_future

        self.current_prompt = prompt
        # FIX: Get the running loop from asyncio directly, not from the app object.
        self.input_future = asyncio.get_running_loop().create_future()

        # Trigger a redraw to make sure the new prompt is displayed.
        self.app.invalidate()

        try:
            result = await self.input_future
            return result
        finally:
            self.input_future = None

