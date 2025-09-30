# /bin/system.py
**Description:** Executes a command in the underlying host system, mapping iosk paths to host equivalents and running in the host equivalent of the current working directory.
**Usage:** `system <command> [args...]`
**Example 1:** `system echo "Hello from host"`
**Output 1:** `:: Executing host command: echo 'Hello from host' (in cwd: /home/shawn/sidekick/iosk/doc/iosk/qa/commands)`
            `--- Host STDOUT ---`
            `Hello from host`
            `:: system command 'echo' completed successfully.`
**Example 2:** `system pwd`
**Output 2:** `:: Executing host command: pwd (in cwd: /home/shawn/sidekick/iosk/doc/iosk/qa/commands)`
            `--- Host STDOUT ---`
            `/home/shawn/sidekick/iosk/doc/iosk/qa/commands`
            `:: system command 'pwd' completed successfully.`
**Status:** Working.
