# /bin/rmdir.py
**Description:** Removes an empty directory from the file system.
**Usage:** `/bin/rmdir.py <directory_path>`
**Example:**
First, create an empty directory:
`$ mkdir /home/beta/my_empty_directory`
Then, remove it:
`$ rmdir /home/beta/my_empty_directory`
**Output:** `:: directory removed` (upon successful removal of an empty directory)
Attempting to remove a non-empty directory results in an error. For instance, if `/home/beta/my_non_empty_directory` contains files, then `$ rmdir /home/beta/my_non_empty_directory` would output an error like `:: rmdir: /home/beta/my_non_empty_directory not empty`.
**Status:** Working.
