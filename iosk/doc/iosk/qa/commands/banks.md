# /bin/banks.py
**Description:** Lists the keys of all memory banks currently loaded in the session.
**Usage:** `banks`

**Test Case 1: No banks loaded**
- **Command:** `$ banks`
- **Output:** `:: 0 banks loaded`

**Test Case 2: After loading banks**
- **Commands:**
    ```bash
    $ bank role sveltepyguy
    $ bank tone formal
    ```
- **Command:** `$ banks`
- **Output:**
    ```
    /bank/role/sveltepyguy
    /bank/tone/formal
    :: 2 banks loaded
    ```

**Status:** Working.

