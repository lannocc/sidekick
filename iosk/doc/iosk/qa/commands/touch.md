# /bin/touch.py
**Description:** Creates a new, empty file at the specified path. It does not update the timestamp of existing files.
**Usage:** `/bin/touch.py <file_path>`
**Example 1 (Success):**
`$ touch /home/beta/new_file.txt`
**Output:** `:: file created`

**Example 2 (File Exists):**
`$ touch /home/beta/new_file.txt` (run a second time)
**Output:** `!! touch: cannot create file: /home/beta/new_file.txt`

**Example 3 (Invalid Path):**
`$ touch /home/beta/no_such_dir/another_file.txt`
**Output:** `!! exception calling touch`

**Status:** Working as a file creation utility. It differs from standard UNIX `touch` as it will not update the modification time of an existing file; instead, it errors.
