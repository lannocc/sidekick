# /bin/detach.py
**Description:** Detaches a previously attached device from the user, removing its presence from the chat.
**Usage:** `/bin/detach.py <handle>`
**Example:**
If the `/dev/dummy.py` device was attached, its (default) handle in the chat is `dummy`. To detach it:
`/bin/detach.py dummy`
**Output:** Upon successful detachment, a message like ":: dummy has left the chat" is displayed, and the device's handle is removed from the `users currently online` list.
**Status:** Working.
