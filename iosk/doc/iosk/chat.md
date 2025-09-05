## AIMessenger Class

The `AIMessenger` class manages AI interactions within the IOSK system. It handles user connections, message routing, and AI engagements.  It utilizes the `Engagement` class to handle the interaction with each user.

**Initialization:**

*   `__init__(self, iosk)`:
    *   Initializes the `AIMessenger` with an IOSK instance (`iosk`).
    *   Sets `iosk.chat` to `self` to establish a bidirectional link.
    *   Sets `self.me` to `None` and initializes an empty `engagements` dictionary, which stores `Engagement` objects for connected users.

**Methods:**

*   `async start(self, handle=None)`:
    *   Starts the AI messenger.
    *   Takes an optional `handle` (username). Defaults to 'root' if not provided.
    *   Prints a welcome message and sets `self.me` to the username.
    *   Returns the username.

*   `async run(self)`:
    *   Main entry point to run the messenger once it's started (after `start`).
    *   Waits for `self.os.ready` to be set (indicating the OS is ready).
    *   Checks if `self.os.halt` is set; if so, returns immediately.
    *   Calls `self.join(self.me)` to connect the super-user to the chat.
    *   Enters the interactive loop using `self.os.interactive(io)`, processing user input.
    *   In a `finally` block, ensures `self.leave(io)` is called to disconnect the user.

*   `async join(self, name, dev=None)`:
    *   Allows a user to join the chat from a specific device (or locally).
    *   `name`: The username to connect as.
    *   `dev`: Optional device name. If None, defaults to the local console.
    *   Logs a connection message to the chat.
    *   If `dev` is provided, creates an `Engagement` object and stores it in `self.engagements` (indicating an AI is actively engaging).
    *   Calls `self.os.login` to authenticate the user and establish an I/O stream.
    *   If successful, creates an asyncio task that runs the interactive loop (`self.os.interactive(io)`) and handles disconnection (by calling `self.leave`).
    *   If an engagement is created, also start an asyncio task for the `engage()` method of the engagement.
    *   Returns the I/O stream or `None` if login failed.

*   `async leave(self, io)`:
    *   Disconnects a user from the chat.
    *   `io`: The I/O stream associated with the user.
    *   If the user has an active engagement, disables it and removes it from `self.engagements`.
    *   Logs a disconnection message to the chat.
    *   Calls `self.os.logout` to terminate the I/O stream.

*   `async send(self, from_user, msg, sys=False)`:
    *   Sends a message to all other users in the chat.
    *   `from_user`: The username of the sender.
    *   `msg`: The message to send.
    *   `sys`: Optional boolean to indicate if the message is from the system (avoids prepending the username to the message).
    *   Iterates through all users in `self.os.users` and prints the message to their I/O streams, excluding the sender.

---

## Engagement Class

The `Engagement` class represents an active AI engagement with a user. It manages the interaction flow, buffers output, and handles code block extraction and execution. It uses a prompt-reply cycle with the AI.

**Constants:**

*   `CODE`: A class-level counter for generated code files.  Incremented during code block handling.
*   `SECS_IDLE_BEFORE_TRIP`:  Number of seconds of inactivity before prompting the AI when there is new output.
*   `SECS_NOISY_WAIT_REPLY`: Number of seconds after last trip to always prompt the AI.
*   `SECS_QUIET_IDLE_POLL`: Number of seconds of inactivity before polling the AI when there is no new output.
*   `PREAMBLE`: Path to preamble script to be injected to the prompt.
*   `POSTAMBLE`: Path to postamble script to be injected to the prompt.
*   `CODEBLOCK_REGEX`: A regular expression to match code blocks enclosed in triple backticks.

**Initialization:**

*   `__init__(self, user)`:
    *   Initializes the `Engagement` with the username (`user`).
    *   Sets `self.enabled` to `True`, indicating the engagement is active.
    *   Initializes buffer attributes for handling output (`self.buf`, `self.last_buf`), AI trip data (`self.trip`), input (`self.inbuf`),  and the I/O stream (`self.io`).
    *   Sets `self.waiting` to `False`, indicating it is not currently waiting for an AI response.

**Methods:**

*   `append(self, text, trip)`:
    *   Appends text to the output buffer.
    *   `text`: The text to append.
    *   `trip`: A function (presumably an AI model call) to be called when the buffer is ready to be processed.
    *   Stores the `trip` function for later use.
    *   Updates `self.last_buf` with the current time.

*   `input(self)`:
    *   Retrieves the input buffer, processes code blocks, and clears the input buffer.
    *   Returns the input buffer after processing.

*   `async ioset(self, io)`:
    *   Sets the I/O stream for the engagement.
    *   `io`: The I/O stream.

*   `async engage(self)`:
    *   Main loop for managing the AI engagement.
    *   Polls for buffered output or idle time.
    *   Constructs a prompt, including preamble, history, core rules and postamble,  and sends it to the AI using the `trip` function.
    *   Handles AI responses and updates the input buffer.

*   `read_history(self)`:
    *   Placeholder function to read the chat history.  Currently does nothing.

*   `_handle_code_blocks_(self, text)`:
    *   Extracts and saves code blocks from the input text to separate files.
    *   `text`: The input text.
    *   Uses the `CODEBLOCK_REGEX` to find code blocks.
    *   For each code block:
        *   Generates a unique file name.
        *   Saves the code to the file.
        *   Replaces the code block in the input text with a message indicating the file path.
    *   Returns the modified text.

