# Proposal: A Versatile `ask` Command for IOSK

**Status**: Now implementing...

### Introduction

The `ask` command is a cornerstone of the SideKick toolset, providing a simple, direct interface to an AI model. To fully integrate this capability into the IOSK environment, we propose a new `/bin/ask.py` command that merges the simplicity of the original `ask` with the powerful, context-aware features of IOSK, such as user-specific banking, preamble/postamble scripting, and direct device interaction.

This command will serve as the primary mechanism for one-shot, non-interactive AI queries. It creates a clear distinction between the ongoing, conversational nature of the main chat environment and the transactional, command-like utility of asking a single, focused question. It allows users and other AI agents to leverage the rich context of an IOSK user (their banked memory, environment variables) without polluting or being influenced by their recent chat history.

### Core Functionality

*   **One-Shot Queries**: Executes a single request-response cycle with an AI agent.
*   **Context-Aware Responses**: Leverages a user's `.skrc` file to load environment variables and "banked" core memory, providing user-specific context to the AI.
*   **Flexible Agent Targeting**: Allows the user to specify which AI device to use and which user's context to run under.
*   **File and Directory Attachments**: Supports attaching the content of a single file (`-f`) or an entire directory tree (`-p`) to the prompt.
*   **Result Post-Processing**: Can extract code blocks from the AI's response and save them directly to a file (`-e`).

### Command Syntax and Options

The command will follow a familiar structure, with a prompt as the final argument.

**Usage:** `ask [options] <prompt>`

**Options:**

*   `-h`, `--help`: Displays the help message for the `ask` command.
*   `-f <file>`: Attaches the contents of the specified `<file>` to the prompt. Cannot be used with `-p`.
*   `-p <directory>`: Packages the contents of the specified `<directory>` and attaches it to the prompt. Cannot be used with `-f`.
*   `-e <lang> <file>`: After receiving a response, extracts the first markdown code block of type `<lang>` and saves it to `<file>`.
*   `-u <user>`: Executes the request within the context of `<user>`. This will run the user's `/home/<user>/.skrc` file to load their environment and banks. If `-d` is not specified, it will use the device associated with that user's currently logged-in session. The command will fail if the user is not logged in.
*   `-d <device>`: Specifies the exact device to use for the query (e.g., `openai/gpt-4o`, `google/gemini-2.5-pro`). If `-u` is not specified, the device's default handle will be used as the username.
*   `-1`: A shortcut for `-d google/gemini-2.0-flash`.
*   `-2`: A shortcut for `-d google/gemini-2.5-flash` (This is the default model if no other is specified).
*   `-3`: A shortcut for `-d google/gemini-2.5-pro`.

### Implementation Strategy

#### 1. Filesystem Changes

To separate the prompting logic for interactive chat and one-shot `ask` commands, the preamble and postamble scripts will be reorganized:

*   Move `/sbin/preamble` to `/etc/chat/preamble`.
*   Move `/sbin/postamble` to `/etc/chat/postamble`.
*   Create a new file, `/etc/ask/preamble`, with content tailored for direct questions:
    ```skrip
    #!/bin/skrip
    This is a one-shot request to an expert AI assistant.
    I must provide a direct, concise, and accurate answer to the user's prompt.
    I will use markdown for formatting if it improves clarity.
    ```
*   Create a new file, `/etc/ask/postamble`, to reinforce the directive:
    ```skrip
    #!/bin/skrip
    Remember: Do not engage in conversational chat.
    Fulfill the user's request as directly as possible.
    ```

#### 2. Command Logic (`/iosk/bin/ask.py`)

The `iocall` function in this new file will be responsible for the entire workflow:

1.  **Argument Parsing**: Parse the `argv` list to identify all options and separate them from the core `<prompt>` string.
2.  **User/Device Resolution**:
    *   **Default**: If no `-u` or `-d` is given, default to device `google/gemini-2.5-flash` with a temporary user context.
    *   **`-d` only**: Use the specified device with its default username (e.g., `openai-gpt-4o`).
    *   **`-u` only**: Find the specified user in `io.os.users`. If found, use their associated device. If not found, error out.
    *   **`-u` and `-d`**: Use the specified device with the specified user's context.
3.  **Context Creation and Priming**:
    *   Create a new, temporary, non-interactive `Context` (`ask_io`) forked from the system context.
    *   Set the `ask_io.user` and `ask_io.dev` based on the resolution step.
    *   Execute the system `/etc/skrc`.
    *   If a user context was specified (`-u`), execute that user's `/home/<user>/.skrc` to load their specific environment and banks into `ask_io.banks`.
4.  **Prompt Construction**: Assemble the final prompt string by concatenating the output of:
    *   `/etc/ask/preamble` (executed within `ask_io`).
    *   The contents of `ask_io.banks` (formatted as a "CORE MEMORY" block).
    *   The user-provided `<prompt>` string.
    *   The content of the attached file (`-f`) or packaged directory (`-p`), if any.
    *   `/etc/ask/postamble` (executed within `ask_io`).
5.  **AI Interaction**:
    *   Directly invoke the AI's `trip` function (from the appropriate device module, e.g., `sk.iosk.dev.google.trip`) with the constructed prompt. This bypasses the `Engagement` class and its chat-oriented loop, performing a single, synchronous-style request.
6.  **Output Handling**:
    *   Print the AI's text response to the user's console.
    *   If the `-e` option was used, scan the response for the specified code block, save it to the target file, and notify the user.

### Use Case Scenarios

1.  **Simple Question (Default Model)**:
    `$ ask "What is the capital of Mongolia?"`
    *Uses `gemini-2.5-flash` to provide the answer.*

2.  **Code Review with File Context**:
    `$ ask -f /home/beta/utils.py "Review this Python code for potential bugs."`
    *Uploads `utils.py` and includes its content in the prompt to the default AI.*

3.  **Task with User-Specific Context**:
    `$ ask -u alpha "Based on my banked rules for project titan, what is the next logical step?"`
    *Loads `alpha`'s banks from their `.skrc`, then asks the AI associated with `alpha`'s session for advice.*

4.  **Targeting a Specific, Powerful Model**:
    `$ ask -3 -p /home/beta/project-src "Provide a technical summary of this project."`
    *Packages the source directory, then sends it to the `gemini-2.5-pro` model for a detailed analysis.*

5.  **Code Generation and Saving**:
    `$ ask -e python /home/beta/new_script.py "Write a python script that lists all files in the current directory."`
    *The AI generates the script, and the `ask` command automatically extracts the python code block and saves it to `new_script.py`.*

### Benefits

*   **Powerful Integration**: Seamlessly combines the simplicity of a one-shot `ask` command with the contextual power of `iosk`'s user banks and environment.
*   **Clear Separation of Concerns**: Differentiates between interactive chat and transactional AI tasks, preventing `ask` queries from cluttering a user's chat history.
*   **Enhanced Automation**: Provides a scriptable, command-line tool for other agents and skrips to use when they need to query an AI with specific context, without needing to join the chat.
*   **Fine-Grained Control**: Gives users precise control over which AI model and user context to use for any given task.

