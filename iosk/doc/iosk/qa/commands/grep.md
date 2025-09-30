# grep

## Purpose
The `grep` command searches for patterns in files or standard input. It prints lines that match a specified pattern. It is a powerful utility for finding specific information within text files and streams.

## Usage
`grep [OPTIONS] PATTERN [FILE...]`
`grep --help`

## Options
*   `-i`, `--ignore-case`: Ignore case distinctions in PATTERN.
*   `-v`, `--invert-match`: Invert the sense of matching, to select non-matching lines.
*   `-n`, `--line-number`: Prefix each line of output with the 1-based line number within its input file.
*   `-l`, `--files-with-matches`: Suppress normal output; instead print the name of each input file from which output would normally have been printed.
*   `-c`, `--count`: Suppress normal output; instead print a count of matching lines for each input file.
*   `-r`, `-R`, `--recursive`: Read all files under each directory, recursively.
*   `--help`: Display this help message and exit.

## Examples

### 1. Basic recursive search for a pattern
Searches for the string 'def' in all files within the `/bin` directory and its subdirectories.

```bash
grep -r 'def' /bin
```

Expected output (truncated, showing typical lines):
```
/bin/date.py:async def iocall(io, argv):
/bin/touch.py:async def iocall(io, argv):
/bin/system.py:async def iocall(io, argv):
...
```

### 2. Case-sensitive search
Searching for 'DEF' in `/bin/date.py` (case-sensitive) should yield no results if the pattern is 'def'.

```bash
grep 'DEF' /bin/date.py
```

Expected output: (no output, indicating no match)

### 3. Case-insensitive search (`-i`)
Searches for 'DEF' in `/bin/date.py`, ignoring case.

```bash
grep -i 'DEF' /bin/date.py
```

Expected output:
```
/bin/date.py:async def iocall(io, argv):
```

### 4. Invert match (`-v`)
Prints lines from `/bin/date.py` that *do not* contain 'async def'.

```bash
grep -v 'async def' /bin/date.py
```

Expected output (truncated):
```
/bin/date.py:from datetime import datetime
/bin/date.py:
/bin/date.py:    """Display the current date and time.
...
```

### 5. Line number (`-n`)
Searches for 'def' in `/bin/date.py` and prefixes matching lines with their 1-based line number.

```bash
grep -n 'def' /bin/date.py
```

Expected output:
```
/bin/date.py:3:async def iocall(io, argv):
```

### 6. Files with matches (`-l`)
Recursively searches for 'async def' in `/bin` and prints only the names of files that contain a match.

```bash
grep -r -l 'async def' /bin
```

Expected output (truncated):
```
/bin/date.py
/bin/touch.py
/bin/system.py
...
```

### 7. Count matching lines (`-c`)
Counts the number of lines containing 'async def' in `/bin/date.py`.

```bash
grep -c 'async def' /bin/date.py
```

Expected output:
```
/bin/date.py:1
```

### 8. Combined options: Line number and ignore case (`-n -i`)
Searches for 'DEF' in `/bin/date.py`, ignoring case, and shows the line number of matches.

```bash
grep -n -i 'DEF' /bin/date.py
```

Expected output:
```
/bin/date.py:3:async def iocall(io, argv):
```

### 9. Combined options: Recursive search and count (`-r -c`)
Recursively searches for 'iocall' in `/bin` and prints the count of matching lines for each file.

```bash
grep -r -c 'iocall' /bin
```

Expected output (truncated):
```
/bin/date.py:2
/bin/touch.py:2
/bin/system.py:2
...
```
