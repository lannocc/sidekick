# /bin/su.py
**Description:** Attempts to switch the current user identity to another user. This command requires super-user privileges.
**Usage:** `/bin/su.py [<username>]`
**Example:**
As a regular user (e.g., `beta`):
`/bin/su.py`
Output: `!! must be super-user to su`

`/bin/su.py alpha`
Output: `!! must be super-user to su`

These examples demonstrate that a non-super-user cannot use the `su` command. To successfully use `su`, the current user must have super-user privileges. When executed by a super-user without a username argument, it typically switches to the root user. When executed by a super-user with a username argument, it switches to the specified user.
**Status:** Working (functionality for super-users is assumed based on the explicit error for non-super-users).
