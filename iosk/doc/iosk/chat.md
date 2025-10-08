## AIMessenger Class

The `AIMessenger` class manages AI interactions within the IOSK system. It handles user connections, message routing, and AI engagements. It utilizes the `Engagement` class to handle the interaction with each user.

**Initialization:**

*   `__init__(self, iosk)`:
    *   Initializes the `AIMessenger` with an IOSK instance (`iosk`).
    *   Sets `iosk.chat` to `self` to establish a bidirectional link.
    *   Sets `self.os` to the IOSK instance, `self.me` to `None`, `self.device` to `None`, and initializes an empty `engagements` dictionary, which stores `Engagement` objects for connected users.

**Methods:**

*   `async start(self, handle=None, device=None)`:
    *   Starts the AI messenger.
    *   Takes an optional `handle` (username), which defaults to 'root'.
    *   Takes an optional `device` path (e.g., `/dev/terminal`).
    *   Prints a welcome message and sets `self.me` to the username and `self.device` to the device path.
    *   Returns the username.

*   `async run(self)`:
    *   Main entry point to run the messenger once it's started (after `start`).
    *   Waits for `self.os.ready` to be set (indicating the OS is ready).
    *   Checks if `self.os.halt` is set; if so, returns immediately.
    *   Calls `self.join(self.me, dev=self.device)` to connect the super-user to the chat.
    *   Enters the interactive loop using `self.os.interactive(io)`, processing user input.
    *   In a `finally` block, ensures `self.leave(io)` is called to disconnect the user.

*   `async _setup_chat_context(self, io)`:
    *   A private helper method called upon user join to prepare their session context.
    *   **Preamble Caching**: Executes the `/etc/chat/preamble` script and caches its output in `io.preamble_cache` to avoid re-execution on every AI trip.
    *   **Initial Token Calculation**: Calculates the number of tokens for the static parts of the AI prompt (the cached preamble and any banked memory). This initial count is stored in `io.initial_static_tokens` and initializes the session's running total in `io.caching_token_total`.

*   `async join(self, name, dev=None)`:
    *   Allows a user to join the chat from a specific device (or locally).
    *   `name`: The username to connect as.
    *   `dev`: Optional device name. If None, defaults to the local console (`self.os.CONSOLE_DEV`).
    *   If `dev` is provided (i.e., it's a bot), an `Engagement` object is created and stored in `self.engagements`.
    *   Calls `self.os.login` to authenticate the user and establish an I/O stream (`Context`), passing the `Engagement.ioset` method as an `io_callback` if an engagement was created.
    *   After a successful login, it calls `_setup_chat_context` to prepare the user's session.
    *   If an engagement is created, it starts two asyncio tasks: one for the user's interactive loop (`self.os.interactive(io)`) and another for the AI's interaction loop (`engage()`).
    *   Returns the I/O stream (`Context` object) or `None` if login failed.

*   `async leave(self, io)`:
    *   Disconnects a user from the chat.
    *   `io`: The I/O stream associated with the user.
    *   If the user has an active engagement, `self.engagements[io.user].enabled` is set to `False` to stop its loop, and the engagement is removed.
    *   Constructs a disconnection message and sends it to other users.
    *   Calls `self.os.logout` to terminate the I/O stream.

*   `async send(self, from_user, msg, sys=False)`:
    *   Sends a message to other users. This method now supports both broadcast messages and direct messages (DMs).
    *   `from_user`: The username of the sender.
    *   `msg`: The message to send.
    *   `sys`: Boolean, if `True` the message is from the system.
    *   **Direct Messages**: If the message starts with one or more `@username` handles, it is treated as a DM.
        *   The message is sent only to the specified recipients.
        *   The sender receives a confirmation copy (e.g., `[me -> alpha, beta] << ...`).
        *   If the recipient is the console user (`/dev/console`), the terminal bell is rung (`\a`).
        *   **Sleep Interruption**: If a DM is sent to a user currently executing a `sleep` command, that user's `sleep` process is cancelled, and they receive a notification that their sleep was interrupted.
    *   **Broadcast Messages**: If not a DM, the message is sent to all other connected, un-paused users in the chat. The current timestamp and sender's username are prepended.

---

## Engagement Class

The `Engagement` class represents an active engagement with an AI user. It manages the interaction flow, buffers output, and handles code block extraction and execution. It uses a prompt-reply cycle with the AI.

**Constants:**

*   `CODE`: (int) A class-level counter for generated code files, incremented during code block handling to ensure unique filenames.
*   `SECS_IDLE_BEFORE_TRIP`: (float) Number of seconds of inactivity after new output before the AI is prompted.
*   `SECS_NOISY_WAIT_REPLY`: (float) Maximum number of seconds after the last AI trip to always prompt the AI, even if there's new explicit output.
*   `SECS_QUIET_IDLE_POLL`: (float) Number of seconds of inactivity before polling the AI when there is no new output but we want to check for potential replies.
*   `PREAMBLE`: (str) Path to a system script (`/etc/chat/preamble`) whose output is injected at the beginning of the AI's prompt.
*   `POSTAMBLE`: (str) Path to a system script (`/etc/chat/postamble`) whose output is injected at the end of the AI's prompt.
*   `CODEBLOCK_REGEX`: (re.Pattern) A regular expression used to match Markdown code blocks. It is configured to be "greedy" (`.*`), meaning it will match until the *last* closing triple backtick found, allowing for multi-block text that the AI might generate before finishing.

**Initialization:**

*   `__init__(self, user)`:
    *   Initializes the `Engagement` with the username (`user`).
    *   Sets `self.enabled` to `True`, `self.buf` (temporary output buffer), `self.trip` (AI model call function), `self.inbuf` (incoming AI reply buffer), and other state attributes.
    *   The actual chat history for prompt construction is stored and managed within `self.io.session`.

**Methods:**

*   `append(self, text, trip)`:
    *   Appends `text` to `self.buf`, buffering new output until the `engage` loop decides it's time to prompt the AI.
    *   `trip`: The asynchronous function (representing an AI model call) to be invoked.
    *   Stores the `trip` function and updates `self.last_buf`.

*   `input(self)`:
    *   Retrieves the content of `self.inbuf` (the raw reply from the AI).
    *   If `self.inbuf` contains data, it processes the text to extract and handle any Markdown code blocks using `_handle_code_blocks_`.
    *   Clears `self.inbuf` and returns the (potentially modified) content.

*   `async ioset(self, io)`:
    *   Sets the `Context` object (`io`) for the engagement, linking it to a user's I/O stream, session, environment, and file system access.

*   `async engage(self)`:
    *   The main asynchronous loop for managing the AI engagement. It periodically checks timing conditions to decide when to construct and send a prompt to the AI.
    *   If a prompt is to be constructed:
        1.  It constructs the full prompt by combining:
            *   The cached preamble from `self.io.preamble_cache`.
            *   Data from `self.io.banks` (core memory), formatted as "CORE RULES/MEMORY".
            *   The entire chat history from `self.io.session`.
            *   Output from the `POSTAMBLE` script.
            *   A final prompt string like `[user /path] >> `.
        2.  It calculates and updates running token totals for the session (`io.caching_token_total`, `io.full_token_total`).
        3.  Sets `self.waiting = True`.
        4.  **Token Rate Limiting**: Calls `self.io.os.await_device_readiness()` to proactively throttle the request or wait for a device cooldown to prevent API rate limit errors.
        5.  **Client Management**: Retrieves a cached or new AI client instance via `self.io.os.get_device_client()`.
        6.  **AI Trip with Retries**: Invokes `self.trip(client, prompt)` in a retry loop (up to 3 attempts).
            *   It specifically catches `429` rate limit errors, parses the suggested delay, and calls `self.io.os.enforce_cooldown()` to trigger a system-wide cooldown for that device before automatically retrying.
            *   Other exceptions are handled with a simple backoff before retrying.
        7.  **Tracing**: After the trip completes (successfully or not), it calls `self.io.os.log_trip_trace()` to log the prompt and reply for debugging and auditing.
        8.  Upon receiving a `reply`, it appends a newline and stores it in `self.inbuf`.
        9.  Resets `self.waiting = False`.

*   `async _handle_code_blocks_(self, text)`:
    *   Scans the input `text` for the first Markdown code block using `CODEBLOCK_REGEX`.
    *   **Intelligent `diff` Handling**:
        *   If the code block's language is `diff`, it extracts the target filename from the `--- a/path/to/file` line.
        *   It then automatically invokes the `/bin/patch` command with the target file and the saved diff content.
        *   The output of the `patch` command is printed directly to the local user's console, providing immediate feedback.
    *   **General Code Block Handling**:
        *   For any code block (including `diff`), it generates a unique filename in `/var/code/` and saves the extracted code.
        *   The original code block and an "auto-saved" message are printed to the *local user's console only*.
    *   **Crucially, the original code block (both `diff` and others) is then removed from the `text` before it is returned.** This prevents the code block from being broadcast to other users in the chat, who only see the command output or other text in the AI's reply.

