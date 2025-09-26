# /bin/ls.py
**Description:** Lists the contents of a directory. If no directory is specified, it lists the contents of the current working directory (which is effectively `/` in iosk as all paths are relative to root).
**Usage:**
1. `/bin/ls.py` (lists contents of the current effective directory)
2. `/bin/ls.py <directory_path>` (lists contents of the specified directory)
**Examples:**
1. To list the top-level directories:
   `/bin/ls.py`
   **Output:** `bin/	dev/	doc/	etc/	home/	sbin/	src/	var/`
2. To list the contents of the `/home/beta` directory:
   `/bin/ls.py /home/beta`
   **Output:** `modified.txt	my_patch.diff	original.txt`
**Error Handling:**
- If the specified path does not exist:
  `/bin/ls.py /nonexistent/path`
  **Output:** `!! ls: path does not exist: /nonexistent/path`
**Status:** Working.
