## To-Do

### Core Systems & Kernel Enhancements

1.  **Implement the Daemon System**
    As detailed in `doc/iosk/proposal/daemons.md`, implementing an event-driven AI agent system is the highest priority for making IOSK a truly proactive and intelligent OS. This involves adding an event dispatcher to the kernel (`fire_event`), creating the daemon configuration file (`/etc/daemons.conf`), and developing the first daemon to handle the `POST_CODE_SAVE` event for automatic file organization. This feature is foundational to the project's long-term vision.

2.  **Fix Critical Bugs and Inconsistencies**
    The `doc/iosk/testing.md` document lists several outstanding issues that impact usability. A concerted effort should be made to fix the system hang caused by `ask`, the argument-handling exceptions in `help`, the inconsistent error messages from `mkdir`, and the non-standard behavior of `touch`. Resolving these will stabilize the core user experience.

3.  **Implement Pipes and Redirection**
-    Building on an advanced shell parser, the next logical step is to support standard UNIX-style pipes (`|`) and output redirection (`>`, `>>`). This would enable chaining commands together (e.g., `$ ls /bin | search .py`) and saving command output to files, dramatically increasing the composability and power of the command-line environment for both human and AI users.

4.  NO: **Bank Persistence Across Sessions** [DO NOT DO]
    Currently, the "bank" or core memory system is ephemeral and exists only for the duration of a user session. To make this a true persistence mechanism, we need to serialize a user's `io.banks` dictionary to a file (e.g., `/var/banks/<user>.bank`) upon logout or shutdown, and reload it upon login. This would allow AI agents to retain critical context and "memories" across reboots.

    LANNOCC: NO we will not persist banks this way. Users are "pre-banked" based on their .skrc file in their home directory which runs through various banks. This is a hidden file so it's not normally noticed.

5.  **User Home Directory Auto-Creation**
    The login process in the kernel should be enhanced to automatically create a home directory (`/home/<user>`) for a user if one does not already exist. This process could also populate the new directory with a default `.skrc` file, providing a smoother onboarding experience for new users and a clear place for them to store personal configurations.

6.  **Filesystem Event API (`inotify` equivalent)** [MAYBE]
    To make the OS more reactive, we should introduce a kernel API that allows processes or daemons to "watch" files and directories for changes (creation, modification, deletion). An AI agent could use this to monitor a log file for new error entries, or a developer could have a skrip that automatically runs tests whenever a source file in their workspace is saved. This goes beyond the proposed daemon system by allowing for fine-grained, real-time filesystem monitoring.

7.  NO: **Structured "System Call" API for Agents** [DO NOT DO]
    While parsing command-line output from AIs works, it can be brittle. We should introduce an alternative, parallel interface for AI agents: a structured "syscall" API. Instead of returning the text string `$ mv fileA fileB`, an agent could return a JSON object like `{"syscall": "move", "args": {"source": "/path/A", "dest": "/path/B"}}`. The kernel would interpret this directly, bypassing the shell parser. This would be far more robust and allow for more complex, error-free interactions between agents and the OS.

    LANNOCC: Actually this is somewhat contrary to a core principle of iosk which is that the AI agents are using the system the same way a human would; they are all treated the same as users.

### New Commands

8.  **`ps` - Process Status** [MAYBE]
    Introduce a `ps` command to list "processes" running within IOSK. A process could be defined as an active user session, an attached AI agent, or a long-running skrip launched in the background. This command would provide visibility into system activity and a way to identify agents for management.

9. **`kill` - Terminate Process** [MAYBE]
    Paired with `ps`, a `kill` command is needed to terminate these processes. This would be essential for managing stuck or misbehaving AI agents without having to detach them, or for stopping a skrip that is caught in an infinite loop.

10. **`grep` - Advanced Text Search**
    The current `search` command is useful but basic. A `grep` command should be added that provides full regular expression support, along with standard options like inverting matches (`-v`) and recursive directory searching (`-r`). This is a cornerstone utility for any UNIX-like environment.

11. **`find` - Filesystem Search**
    To complement `grep`, a `find` command is needed for searching the filesystem based on metadata. Users should be able to find files by name (`-name "*.py"`), type (`-type d`), size (`-size +10k`), or modification time. This is a critical tool for file management and automation.

12. **`curl` - Web Content Fetcher**
    A `curl` or `wget` command would fundamentally expand IOSK's capabilities by allowing it to interact with the external internet. Agents could use it to download data, fetch API documentation, or pull in external scripts and tools. This opens the door for agents to solve a much wider class of problems by leveraging real-world, real-time information.

13. **`man` - Manual Page Reader** [MAYBE]
    The documentation in `/doc/qa` is a good start, but it's not easily accessible from the command line. A `man` command should be created to display formatted help pages for any given command (e.g., `$ man ls`). This command would look for a corresponding markdown file in a new `/doc/man/` directory and display it, making the system self-documenting.

14. NO: **`top` - System Activity Monitor** [DO NOT DO]
    A `top`-like command would provide a real-time dashboard of system activity. In the context of IOSK, it wouldn't monitor CPU/RAM in the traditional sense, but rather metrics like active user sessions, number of commands processed per second, AI token usage rates per device, and bank memory utilization. This would be invaluable for system administration and performance tuning.

    LANNOCC: Only the superuser has console so interactive commands are a VERY LOW priority.

15. **`chmod`/`chown` - Permission Management**
    As IOSK grows, a more formal permission system will be needed beyond the simple `su` check. Implementing basic `chmod` and `chown` commands, along with a simple read/write/execute permission model on files, would create a more secure and robust multi-user environment, preventing users and agents from modifying critical system files unintentionally.

16. **`zip`/`unzip` - Archive Management**
    For managing collections of files, `zip` and `unzip` commands are essential. This would allow users and agents to package entire projects into a single file for easy transfer or backup, and to decompress archives provided by others. This is a key utility for any development-oriented workflow.

### Documentation and Creative Initiatives

17. **Comprehensive Documentation Overhaul**
    A dedicated effort is needed to improve and centralize documentation. This includes creating `man` pages for every command, updating the core system architecture documents (`kernel.md`, `chat.md`, etc.) to reflect recent changes, and writing tutorials for common workflows, such as "Creating your first AI daemon."

18. **Interactive `skrip` Debugger (`skdb`)** [MAYBE]
    To aid in the development of more complex skrips and daemons, an interactive debugger is proposed. A command like `$ skdb /path/to/my.skrip` would launch the skrip in a controlled environment, allowing the developer to set breakpoints, step through lines of execution, and inspect the state of environment variables (`io.env`) and banks (`io.banks`).

19. **"The Gauntlet" - AI Self-Improvement Test Suite**
    Create a new directory, `/challenge`, containing a series of increasingly difficult problems that can only be solved through interacting with the IOSK environment. Challenges could range from "find the password hidden in the log files and write it to `/home/challenge/solution1.txt`" to "write a daemon that monitors `/var/tmp` and reorganizes files based on their content, then write a report on its actions." This would serve as a benchmark for AI agent capabilities and could even be used as a framework for an AI to attempt to improve its own problem-solving skrips over time.

20. **Intelligent `diff` Code Block Handling**
    **Description:** Enhance the `Engagement._handle_code_blocks_` method (in `src/iosk/chat.py`) to recognize and automatically apply `diff` code blocks.
    **Details:**
    *   When a Markdown code block is identified as a `diff` (e.g., ````diff`), the system should attempt to extract the target filename(s) from the `--- a/` and `+++ b/` lines within the diff content.
    *   If a clear target file is identified, the diff content should be temporarily saved to a `.diff` file in `/var/code/`.
    *   Immediately following this, the kernel should automatically invoke the `/bin/patch` command, passing the identified target file and the temporary diff file as arguments (e.g., `$ patch <target_file> <temp_diff_file>`).
    *   The output of the `patch` command should be injected directly into the user's session stream, providing immediate feedback on the patch operation.
    *   This prevents the AI from needing to explicitly issue a `$ patch` command after generating a diff, making AI interactions more seamless for applying proposed changes.
    **Impact:** Improves AI-driven workflows, especially for code review and automated corrections.

