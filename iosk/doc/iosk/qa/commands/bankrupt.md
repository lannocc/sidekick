# /bin/bankrupt.py
**Description:** Clears all loaded banks from core memory.
**Usage:** `bankrupt`

**Test Case:**
1.  Load a bank: `$ bank role devops`
2.  Verify it's loaded: `$ banks` shows `/bank/role/devops`.
3.  Clear banks: `$ bankrupt`
4.  **Output:** `:: cleared 1 bank`
5.  Verify banks are cleared: `$ banks` shows `:: 0 banks loaded`.

**Status:** Working.

