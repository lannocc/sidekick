# /bin/rm.py
**Description:** Removes a specified file from the filesystem. It does not support removing directories.
**Usage:** `/bin/rm.py <file_path>`
**Example (successful file removal):**
Suppose you want to remove `/home/beta/my_file.txt`.
First, create the file: `$ touch /home/beta/my_file.txt`
Then, remove it: `$ rm /home/beta/my_file.txt`
**Output:** `:: file removed`
After successful execution, `/home/beta/my_file.txt` will no longer exist.

**Example (attempted directory removal):**
Suppose you have a directory `/home/beta/my_directory`.
First, create the directory: `$ mkdir /home/beta/my_directory`
Then, attempt to remove it with `rm`: `$ rm /home/beta/my_directory`
**Output:** `!! exception calling rm`
This shows that `rm.py` cannot remove directories and will raise an exception if attempted. Use `rmdir` for removing empty directories.
**Status:** Working for files, but explicitly fails for directories (which is expected for a basic `rm` command).
