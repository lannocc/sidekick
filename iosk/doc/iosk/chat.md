## AIMessenger Class

The `AIMessenger` class manages AI interactions within the IOSK system. It handles user connections, message routing, and AI engagements. It utilizes the `Engagement` class to handle the interaction with each user.

**Initialization:**

*   `__init__(self, iosk)`:
    *   Initializes the `AIMessenger` with an IOSK instance (`iosk`).
    *   Sets `iosk.chat` to `self` to establish a bidirectional link.
    *   Sets `self.os` to the IOSK instance, `self.me` to `None`, and initializes an empty `engagements` dictionary, which stores `Engagement` objects for connected users.

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
    *   `dev`: Optional device name. If None, defaults to the local console (`self.os.CONSOLE_DEV`).
    *   A connection message is constructed and (if chat is enabled) sent to other users.
    *   If `dev` is provided (i.e., it's a bot), an `Engagement` object is created and stored in `self.engagements`.
    *   Calls `self.os.login` to authenticate the user and establish an I/O stream, passing the `Engagement.ioset` method as an `io_callback` if an engagement was created.
    *   If successful, creates an asyncio task that runs the interactive loop (`self.os.interactive(io)`) and handles disconnection (by calling `self.leave`).
    *   If an engagement is created, an additional asyncio task is started for the `engage()` method of the engagement, initiating the AI's interaction loop.
    *   Returns the I/O stream (`Context` object) or `None` if login failed.

*   `async leave(self, io)`:
    *   Disconnects a user from the chat.
    *   `io`: The I/O stream associated with the user.
    *   If the user has an active engagement, `self.engagements[io.user].enabled` is set to `False` to stop its loop, and the engagement is removed from `self.engagements`.
    *   Constructs a disconnection message and sends it to other users (if chat is enabled).
    *   Calls `self.os.logout` to terminate the I/O stream.

*   `async send(self, from_user, msg, sys=False)`:
    *   Sends a message to all other users in the chat.
    *   `from_user`: The username of the sender.
    *   `msg`: The message to send.
    *   `sys`: Optional boolean to indicate if the message is from the system (if `True`, the username and timestamp are not prepended).
    *   If not a system message, the current timestamp and sender's username are prepended.
    *   Iterates through all users in `self.os.users` and prints the message to their I/O streams, excluding the sender.

---

## Engagement Class

The `Engagement` class represents an active engagement with an AI user. It manages the interaction flow, buffers output, and handles code block extraction and execution. It uses a prompt-reply cycle with the AI.

**Constants:**

*   `CODE`: (int) A class-level counter for generated code files, incremented during code block handling to ensure unique filenames.
*   `SECS_IDLE_BEFORE_TRIP`: (float) Number of seconds of inactivity after new output before the AI is prompted.
*   `SECS_NOISY_WAIT_REPLY`: (float) Maximum number of seconds after the last AI trip to always prompt the AI, even if there's no new explicit output.
*   `SECS_QUIET_IDLE_POLL`: (float) Number of seconds of inactivity before polling the AI when there is no new output but we want to check for potential replies.
*   `PREAMBLE`: (str) Path to a system script (`/sbin/preamble`) whose output is injected at the beginning of the AI's prompt.
*   `POSTAMBLE`: (str) Path to a system script (`/sbin/postamble`) whose output is injected at the end of the AI's prompt.
*   `CODEBLOCK_REGEX`: (re.Pattern) A regular expression used to match Markdown code blocks (e.g., ````python...````). It is configured to be "greedy" (`.*`), meaning it will match until the *last* closing triple backtick found, allowing for multi-block text that the AI might generate before finishing.

**Initialization:**

*   `__init__(self, user)`:
    *   Initializes the `Engagement` with the username (`user`).
    *   Sets `self.enabled` to `True`, indicating the engagement is active.
    *   Initializes `self.buf` (a temporary buffer for new output awaiting its next trip), `self.last_buf` (timestamp of last buffer append), `self.trip` (the async function for sending prompts to the AI model), and `self.inbuf` (buffer for incoming AI replies).
    *   `self.io` is set to `None` initially and populated by `ioset`.
    *   Sets `self.waiting` to `False`, indicating it is not currently waiting for an AI response.
    *   Note: The actual chat history for prompt construction is stored and managed within `self.io.session`.

**Methods:**

*   `append(self, text, trip)`:
    *   Appends `text` to `self.buf` (if `self.buf` is already active, otherwise initializes it), buffering new output until the `engage` loop decides it's time to prompt the AI.
    *   `text`: The text to append.
    *   `trip`: The asynchronous function (representing an AI model call) to be invoked when a prompt is constructed.
    *   Stores the `trip` function and updates `self.last_buf` with the current time.

*   `input(self)`:
    *   Retrieves the content of `self.inbuf` (the raw reply from the AI).
    *   If `self.inbuf` contains data, it processes the text to extract and save any Markdown code blocks using `_handle_code_blocks_`.
    *   Clears `self.inbuf`.
    *   Returns the (potentially modified) input buffer content.

*   `async ioset(self, io)`:
    *   Sets the `Context` object (`io`) for the engagement. This links the engagement to a specific user's I/O stream, which includes their chat session (`io.session`), environment, and file system access.

*   `async engage(self)`:
    *   The main asynchronous loop for managing the AI engagement.
    *   It periodically checks for:
        *   New buffered output in `self.buf` (indicating recent activity) and if enough `SECS_IDLE_BEFORE_TRIP` has passed, or if `SECS_NOISY_WAIT_REPLY` has elapsed since the last trip.
        *   Idle time (`SECS_QUIET_IDLE_POLL`) when there's no new output, to actively poll the AI for a response.
    *   If a prompt is to be constructed:
        1.  It uses `io.stage_pre()` to capture the output of `/sbin/preamble` and `io.stage_post()` for `/sbin/postamble`.
        2.  It constructs the full prompt by combining:
            *   Output from `PREAMBLE`.
            *   Data from `self.io.banks` (core memory), if any, formatted as "CORE RULES/MEMORY".
            *   The entire chat history from `self.io.session`.
            *   Output from `POSTAMBLE`.
            *   A prompt string like `[user] >> `.
        3.  Sets `self.waiting = True` to prevent re-triggering while awaiting a reply.
        4.  Invokes `self.trip(prompt)` (the AI model call) with retries for potential overload exceptions.
        5.  Upon receiving a `reply`, it appends a newline and stores it in `self.inbuf`.
        6.  Resets `self.waiting = False`.

*   `_handle_code_blocks_(self, text)`:
    *   Scans the input `text` (AI's reply) for Markdown code blocks using `CODEBLOCK_REGEX`.
    *   **Crucially, it processes only the *first* detected code block per `input()` call.**
    *   For each identified code block:
        *   Generates a unique filename using the user's name, system boot number, context ID, and a class-level `CODE` counter (e.g., `/var/code/alpha-1-3-1.py`).
        *   Saves the extracted code to this unique file on the host filesystem.
        *   Modifies the `text` by replacing the original code block with a truncated version (if longer than 10 lines) and appends a message indicating the file path where the code was saved (e.g., `<< [iosk] auto-saved markdown block 1 to /var/code/alpha-1-3-1.py`). This allows the user to see a concise version of the code block in the chat history while knowing the full code is saved.
    *   Returns the `text` with code blocks processed and modified.

