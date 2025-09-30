# /bin/tokens.py
**Description:** Calculates the total bytes and estimates tokens for the current session context that would be sent to an AI model. This includes the preamble, banked memory, chat history, and postamble.
**Usage:**
  - `tokens`
  - `/bin/tokens.py`
  - `tokens --help`
**Options:**
  - `--help`: Display the help message for the `tokens` command.
**Example:**
To see the current session context size:
  - `tokens`
**Output:**
The command will output the total bytes and an estimate of the tokens for the current session. For example:
  - `Total Bytes: 12,637`
  - `Est. Tokens: 3,045`
**Status:** Working.
