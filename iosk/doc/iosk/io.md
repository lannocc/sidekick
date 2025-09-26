## Context Class Summary

The `Context` class manages the state and environment for a conversation or interaction within a system. It handles input/output, logging, session management, environment variables, command aliases, and memory (banks). It appears to be designed to handle multi-user scenarios or bots on a simulated operating system called `iosk_unix`.

Here's a breakdown of the class and its methods:

**Class Attributes:**

*   `CID`: (int) A class-level counter used to assign unique IDs to `Context` instances.
*   `CHATTER`: (str) A class-level constant representing the base directory for "chatter" logs, which likely contains the conversations of each context.
*   `CODE`: (str) A class-level constant representing a directory potentially used for storing code or configurations.
*   `STAGE_PRE`: (int) Constant representing the "pre" stage where output is captured to a string buffer before being released.
*   `STAGE_BANK`: (int) Constant representing the "bank" stage for capturing output to a string buffer when writing to core memory.
*   `STAGE_NORMAL`: (int) Constant representing the normal stage where output is sent directly to the user/log.
*   `STAGE_POST`: (int) Constant representing the "post" stage for capturing output to a string buffer after the primary interaction.

**Instance Attributes:**

*   `cid`: (int) A unique identifier for the `Context` instance, assigned from `Context.CID`.
*   `os`: (iosk_unix) An instance of the `iosk_unix` class, representing the underlying operating system interface.
*   `dev`: (str) The path or identifier of the device (e.g., console, model) used for communication.
*   `log`: (file handle or None) An optional file handle for logging interactions. If `None`, logging is disabled.
*   `parent`: (Context or None) A reference to the parent `Context` instance if this is a forked context. `None` if it's a root context.
*   `chatter`: (file handle) A file handle for a chatter log file specific to this context.
*   `user`: (str or None) The username associated with this context.
*   `su`: (bool) `True` if the user associated with this context has superuser privileges (e.g., connected via the console).
*   `base`: (bool) `True` if this is the root `Context` of a user session, indicating it's the main process.
*   `bot`: (bool) `True` if the context represents a bot user. This flag likely affects how input and output are handled.
*   `session`: (StringIO) A `StringIO` object used to store the entire chat history, particularly when the context represents a bot.
*   `banks`: (dict) A dictionary representing the "core memory" or data storage available to the context, key-value pairs where keys are strings identifying bank and account (e.g., "bank1 acct1") and values are the stored data.
*   `env`: (dict) A dictionary storing environment variables specific to this context. Child contexts can inherit and override these.
*   `pwd`: (str or None) The current working directory of this context in the virtual filesystem (e.g., `/home/user`).
*   `aliases`: (dict) A dictionary storing command aliases defined for this user/session (e.g., `{'ll': 'ls -l'}`).
*   `history`: (list) A list storing the command history for the current session.
*   `stage`: (int) The current processing stage (e.g., `STAGE_NORMAL`, `STAGE_PRE`, `STAGE_BANK`, `STAGE_POST`). Controls where output is directed.
*   `pre`: (StringIO or None) A `StringIO` object used to buffer output during the `STAGE_PRE` stage.
*   `post`: (StringIO or None) A `StringIO` object used to buffer output during the `STAGE_POST` stage.
*   `banking`: (tuple or None) A tuple storing information during `STAGE_BANK`: (bank name, account name, StringIO).

**Methods:**

*   `__init__(self, iosk_unix, dev_path, log_file=None)`:
    *   Constructor. Initializes the `Context` with the `iosk_unix` instance, device path, and optional log file.
    *   Assigns a unique `cid`.
    *   Creates and opens the `chatter` log file.
    *   Initializes other attributes like `user`, `su`, `base`, `bot`, `session`, `banks`, `env`, `pwd`, `aliases`, `history`, and `stage`.

*   `fork(self)`:
    *   Creates a new `Context` instance that inherits some properties from the current context. This is useful for handling separate threads or processes within the same user session.
    *   The child context inherits the `user` and `bot` status from its parent.
    *   The `parent` attribute of the child is set to the current (parent) `Context`.

*   `environ(self)`:
    *   Retrieves the complete environment for this context.
    *   It traverses up the parent chain, merging environment dictionaries, with child values overriding parent values. This means local `env` settings take precedence over those in parent contexts.

*   `async print(self, text, indicator='=')`:
    *   Prints the given `text` to the output, prefixed with an optional `indicator`.
    *   Writes a timestamped entry to the `log` file (if open and in `STAGE_NORMAL`).
    *   Calls `await self.output(text)` to actually send the output and writes a newline.

*   `async comment(self, text)`:
    *   Writes a comment to the `session` history. It only writes comments if it's the base (root) context *and* a bot.
    *   This seems to be used for internal tracking or annotation.

*   `async input(self, prompt=None)`:
    *   Receives input from the user/device.
    *   Sends a `prompt` to the device if provided *and* if it's not a bot.
    *   Receives data from the device using `await self.os.recv()`.
    *   Logs the received data to the `log` file (if open) with an 'I' indicator.
    *   Appends the prompt and input to the session log (if the current context is base and bot).
    *   Returns the received data.

*   `async output(self, text)`:
    *   Sends the given `text` to the output device, handling different `stage` scenarios.
    *   If `stage` is `STAGE_PRE`, writes to the `self.pre` buffer.
    *   If `stage` is `STAGE_BANK`, writes to the `self.banking[2]` buffer (which is the `StringIO` for the bank); if it's a bot, it returns without further processing.
    *   If `stage` is `STAGE_POST`, writes to the `self.post` buffer.
    *   Otherwise (normal stage), writes to `self.chatter`, the log file (if open, with multiline formatting), and sends it to the device using `await self.os.send()`.
    *   Writes to the `session` history if it's a bot and the base context.

*   `async error(self, args)`:
    *   Prints an error message to the output, using an error indicator.

*   `stage_pre(self)`:
    *   Sets the stage to `STAGE_PRE` and creates the string buffer for output capture (`self.pre`).

*   `stage_bank(self, bank, acct)`:
    *   Sets the stage to `STAGE_BANK`, stores the bank and account names and initializes a `StringIO` buffer (`self.banking[2]`).

*   `stage_normal(self)`:
    *   Sets the stage back to `STAGE_NORMAL`.
    *   If previously in `STAGE_BANK`, retrieves the buffered data from the `StringIO` object, stores the data in the `self.banks` dictionary (keyed by "bank acct"), and clears the `self.banking` tuple.

*   `stage_post(self)`:
    *   Sets the stage to `STAGE_POST` and creates the string buffer for output capture (`self.post`).

*   `_log_(self, indicator='=')`:
    *   A private helper method that writes a timestamped log entry to the `log` file, using the given `indicator`.

**Capture Class:**

The `Capture` class handles managing log files. It provides a mechanism to open and reuse log files based on a given path.

*   `logs` (dict): A dictionary that stores opened file handles, keyed by file path. This avoids reopening the same log file multiple times.

*   `log(cls, iosk, path, mkdirs=False)`:
    *   A class method that retrieves a log file handle for the specified path.
    *   If `mkdirs` is `True`, it creates the directory if it doesn't exist.
    *   It formats the log filename with today's date.
    *   It reuses an existing log file handle if the file is already open.
    *   If the file is not yet open, it opens the file in append mode (`'a'`) and stores the file handle in the `logs` dictionary.
    *   Returns the file handle.

**Overall Purpose:**

The `Context` class provides a structured way to manage the state and behavior of interactions within a system, particularly for bot interactions. It isolates the environment for each user or thread, manages input and output, handles logging, manages environment variables and command aliases, and provides a simple form of memory (banks). The stage system allows for delayed processing of output. The `Capture` class assists with managing log files used by multiple Contexts.
