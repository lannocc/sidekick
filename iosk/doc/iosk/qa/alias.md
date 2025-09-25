# /bin/alias.py
**Description:** Manages shell aliases. Allows defining, listing, and undefining command shortcuts. Currently has known quoting and expansion issues when defining aliases with complex arguments or variables, particularly when multiple layers of expansion are involved or when special characters (like spaces) are used without proper handling by the underlying parser.
**Usage:**
  - `alias`: Lists all current aliases.
  - `alias <name>=<value>`: Defines a new alias or updates an existing one.
  - `alias -u <name>`: Undefines an alias.
**Example:**
  - `alias ll='ls -l'`
  - `alias mycd='cd /home/beta'`
  - `alias`
  - `alias -u mycd`
**Status:** Working (with caveats - alias quoting and expansion issues exist but are not a high priority to resolve immediately given the parser proposal's status).
