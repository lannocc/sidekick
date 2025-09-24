# /bin/skrip.py
**Description:** Executes a skrip file, processing normal text lines as output, ignoring comment lines (starting with '#'), and running command lines (starting with '$ '). Skrip files are typically identified by the `#!/bin/skrip` shebang.
**Usage:** `/bin/skrip.py <skrip_file_path>`
**Example:**
Suppose you have a skrip file `/home/beta/test.skrip` with the following content:
```skrip
#!/bin/skrip
# This is a comment within the skrip file.
Hello from a skrip file!
This line should also be printed.
$ echo "Running an echo command from skrip."
$ whoami
```
To execute this skrip file:
`/bin/skrip.py /home/beta/test.skrip`
**Output:**
The example execution will produce output similar to this:
```
Hello from a skrip file!
This line should also be printed.
"Running an echo command from skrip."
beta
```
**Status:** Working.
