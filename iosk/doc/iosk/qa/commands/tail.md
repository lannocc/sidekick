# /bin/tail.py
**Description:** Displays the last part (tail) of files. By default, it outputs the last 10 lines.
**Usage:** `/bin/tail.py [-n num_lines] file`
**Arguments:**
*   `file`: The path to the file to display.
*   `-n num_lines`: (Optional) Specifies the number of lines to output from the end of the file.

**Examples:**

1.  **Display the last 10 lines of a file (default behavior):**
    $ tail /home/beta/test_tail_file.txt

    This is line 6.
    This is line 7.
    This is line 8.
    This is line 9.
    This is line 10.
    This is line 11.
    This is line 12.
    This is line 13.
    This is line 14.
    This is line 15.

2.  **Display the last 5 lines of a file:**
    $ tail -n 5 /home/beta/test_tail_file.txt

    This is line 11.
    This is line 12.
    This is line 13.
    This is line 14.
    This is line 15.

**Status:** Working.

