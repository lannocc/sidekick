# /bin/export.py
**Description:** Sets or displays environment variables.
With no arguments, `export` prints a list of all environment variables. Otherwise, it sets each `NAME` to `VALUE`.

**Usage:**
`/bin/export.py [NAME=VALUE] ...`
`/bin/export.py --help`

**Example 1: Displaying all currently set environment variables**
To see all environment variables currently set:
`$ export`
**Output (example):**
```
MY_VAR='Hello'
PATH='/bin'
```
(Note: The actual output will vary based on variables previously set.)

**Example 2: Setting a new environment variable**
To set an environment variable named `MY_VAR` with the value `Hello`:
`$ export MY_VAR=Hello`
To confirm it was set:
`$ export`
**Output (example):**
```
MY_VAR='Hello'
PATH='/bin'
```
(Note: Other variables might also be displayed.)

**Example 3: Modifying the PATH environment variable**
To change the system's `PATH` to include new directories:
`$ export PATH=/new/path/bin:/another/path`
To confirm the `PATH` has been updated:
`$ export`
**Output (example):**
```
MY_VAR='Hello'
PATH='/new/path/bin:/another/path'
```
(Note: Other variables might also be displayed.)

**Status:** Working.
