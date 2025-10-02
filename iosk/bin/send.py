async def iocall(io, argv):
    """Send file contents or piped data as a message to the chat (to all users).

    Usage: send <file>...
           ... | send
           send --help

    Reads the contents of one or more files, or reads from standard input,
    and broadcasts the result as a single raw text message to other users
    in the current chat session.

    The sender receives a confirmation and a copy of the sent content in
    their own session history.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not io.os.chat:
        await io.error("!! send: not connected to a chat session.")
        return False

    content = ""

    # Case 1: File arguments
    if argv:
        all_content = []
        for filename in argv:
            file_content = await io.os.get(io, filename)
            if file_content is None:
                # io.os.get already printed an error, so just abort.
                return False
            all_content.append(file_content)
        content = "".join(all_content)

    # Case 2: Piped input from stdin
    elif hasattr(io, 'stdin') and io.stdin:
        content = io.stdin.read()

    # Case 3: No input
    else:
        await io.error("!! send: requires file arguments or piped input.")
        return False

    if not content.strip():
        # Do not send empty or whitespace-only messages
        return True

    # Send the content to the chat
    await io.os.chat.send(io.user, content)

    # Print a confirmation to the sender, as they don't receive their own broadcast
    await io.print(":: content sent to chat.")

    # For the sender's own history, show them what was sent.
    #await io.print(f"--- You sent ---\n{content}\n----------------")

    return True
