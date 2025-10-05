async def iocall(io, argv):
    """Send file contents or piped data as a message to the chat.

    Usage: send [-u <user>]... <file>...
           ... | send [-u <user>]...
           send --help

    Reads the contents of one or more files, or reads from standard input,
    and sends the result as a raw text message.

    By default, the message is broadcast to other users in the current chat.
    If the -u option is used, the message is sent as a direct message to
    the specified user(s) instead.

    Options:
      -u <user>   Send a direct message to a specific user. This option can
                  be used multiple times to specify multiple recipients.
      --help      Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not io.os.chat:
        await io.error("!! send: not connected to a chat session.")
        return False

    recipients = []
    file_args = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '-u':
            i += 1
            if i >= len(argv):
                await io.error("!! send: -u option requires a username.")
                return False
            recipients.append(argv[i])
        elif arg.startswith('-'):
            await io.error(f"!! send: unknown option: {arg}")
            return False
        else:
            file_args.append(arg)
        i += 1

    content = ""

    # Case 1: File arguments
    if file_args:
        all_content = []
        for filename in file_args:
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

    # Construct the final message
    final_message = content
    if recipients:
        dm_prefix = ' '.join([f'@{user}' for user in recipients])
        final_message = f'{dm_prefix} {content}'

    # Send the content to the chat.
    # The chat.send method handles routing for both broadcast and direct messages.
    await io.os.chat.send(io.user, final_message)

    # For broadcast messages, print a local confirmation.
    # For direct messages, the chat.send method prints its own confirmation to the sender.
    if not recipients:
        await io.print(":: content sent to chat.")

    return True

