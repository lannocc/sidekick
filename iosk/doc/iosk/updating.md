## Updating work [DONE]

UPDATE: Alpha has now finished all this work and is ready for beta to qa test.

Now that the kernel's `call` method properly parses the command line into an `argv` list using `shlex`, nearly every command that accepts arguments needs to be updated to handle a list of strings (`argv`) instead of a single raw string (`args`).

Based on the file contents, here is a breakdown of the commands that still need to be updated, categorized by the type of change required.

---

### Summary
Excluding `echo.py` and `skrip.py` which you noted are updated, **almost every other command in `/bin` needs to be modified**. The change is consistent: update the `iocall` signature from `iocall(io, args)` to `iocall(io, argv)` and replace manual string parsing with direct list access.

---

### Category 1: Commands Using `args.split(' ')`

These commands are the most common and straightforward to fix. They manually split the argument string, which is now unnecessary and incorrect.

**Files to Update:**
- `ask.py` [DONE]
- `attach.py` [DONE]
- `bank.py` [DONE]
- `cp.py` [DONE]
- `diff.py` [DONE]
- `export.py` [DONE]
- `head.py` [DONE]
- `history.py` [DONE]
- `ls.py` [DONE]
- `mv.py` [DONE]
- `patch.py` [DONE]
- `search.py` [DONE]
- `su.py` [DONE]
- `tail.py` [DONE]
- `tree.py` [DONE]

**Required Change:**
The primary change is to remove the `args.split(' ')` line and use the `argv` list directly. The signature of `iocall` must also be changed.

**Example (`cp.py`):**

**Before:**
```python
async def iocall(io, args):
    # ...
    args = args.split(' ')
    if len(args) != 2:
        await io.error('!! cp needs 2 arguments: <source> <destination>')
        return

    source = args[0]
    destination = args[1]
    # ...
```

**After:**
```python
async def iocall(io, argv):
    # ...
    if len(argv) != 2:
        await io.error('!! cp needs 2 arguments: <source> <destination>')
        return

    source = argv[0]
    destination = argv[1]
    # ...
```

### Category 2: Commands Expecting a Single String Argument

These commands expect the entire `args` string to be a single entity, like a filename. They will now receive a list containing that filename as the first element.

**Files to Update:**
- `cat.py` [DONE]
- `describe.py` [DONE]
- `detach.py` [DONE]
- `get.py` [DONE]
- `rm.py` [DONE]
- `rmdir.py` [DONE]
- `touch.py` [DONE]
- `wc.py` [DONE]

**Required Change:**
Instead of using `args` directly, they need to access the first element of the `argv` list, `argv[0]`, after ensuring the list is not empty.

**Example (`cat.py`):**

**Before:**
```python
async def iocall(io, args):
    # ...
    if not args:
        await io.error('!! cat: filename required')
        return

    try:
        content = await io.os.get(io, args)
    # ...
```
**After:**
```python
async def iocall(io, argv):
    # ...
    if not argv:
        await io.error('!! cat: filename required')
        return

    filename = argv[0]
    try:
        content = await io.os.get(io, filename)
    # ...
```

### Category 3: Commands with Unique or Complex Parsing

These commands have more specific string manipulation that will break and needs to be refactored to work with a list.

**Files to Update:**

- **`alias.py`** [DONE]: The logic `if '=' in args:` and `args.split('=', 1)` needs to be changed to inspect `argv[0]` for the `'='`.
- **`mkdir.py`** [DONE]: The check `if args.startswith('-p ')` must be changed to check if `argv[0] == '-p'`.
- **`ll.py`** [DONE]: The f-string `f'ls -l {args}'` will now incorrectly print the list representation (e.g., `ls -l ['/home']`). It must be changed to `f"ls -l {' '.join(argv)}"`.
- **`su.py`** [DONE]: The logic `args.index(' ')` and string slicing is now incorrect. It should use `user = argv[0]` and pass `argv[1:]` to the subsequent command.

### Category 4: Commands Needing `--help` Check Update

These commands don't take functional arguments but have a check for `--help` that will fail because it's checking for a substring in what is now a list.

**Files to Update:**
- `date.py` [DONE]
- `users.py` [DONE]
- `whoami.py` [DONE]

**Required Change:**
The check `if '--help' in args:` should be changed to `if '--help' in argv:`.
