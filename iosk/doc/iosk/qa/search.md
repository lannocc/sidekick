usage: search [-i] [-n] [-l] [-c] term [path ...]
Search for a term within text files.
Options:
  -i        Case-insensitive search
  -n        Show line numbers (with normal output)
  -l        List filenames with matches (suppress matched lines)
  -c        Print count of matches per file
  --help    Show this help
Notes:
  - No quoting is supported; term cannot contain spaces.
  - If no paths are provided, defaults to /home/<user> if it exists; otherwise "/".
