# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush as print

import sys


def main(args):
    print('IOSK: ', end='')

    cmd = args[0] if args else 'help'
    args = args[1:]

    if cmd in SET:
        cmd = SET[cmd]
        print(cmd[1])
        cmd[0](args)

    else:
        print(f'unknown command: {cmd}')
        print('Try `sk iosk help` for a list of commands.')


def help(args):
    print()
    print('USAGE:')
    print('   sk iosk <command>')
    print()
    print('The following commands are available:')
    for name, cmd in SET.items():
        print(f'   {name} - {cmd[1]}')


def run(args=sys.argv[1:]):
    import asyncio
    from asyncio.exceptions import CancelledError
    import aioconsole

    terminal_mode = False
    if '-t' in args:
        terminal_mode = True
        args.remove('-t')

    if args:
        if len(args) != 2:
            print('2 arguments required: <root> <handle>')
            return

        root = args[0]
        handle = args[1]

    else:
        print('  >> Filesystem Root: ', end='')
        root = input()
        if not root: return

        print('  >> Chat Handle (super): ', end='')
        handle = input()
        if not handle: return

    print('Preparing iosk UNIX... ', end='')
    from . import UNIX
    unix = UNIX(root=root)
    print('system loaded.')

    print('Preparing iosk AIM...', end='')
    from . import AIM
    chat = AIM(iosk=unix)
    print('chat loaded.')

    async def async_run():
        print()
        device = '/dev/terminal' if terminal_mode else None
        await unix.start()
        await chat.start(handle=handle, device=device)
        unix_task = asyncio.create_task(unix.run())
        chat_task = asyncio.create_task(chat.run())

        pending = {unix_task, chat_task}
        try:
            # Wait for the first of the main tasks to complete.
            # This handles both a user logging out (chat_task finishes)
            # and a system shutdown (both tasks finish).
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )

            # If the chat task is the one that finished (e.g., user typed '$ exit'),
            # the system is still running. We proceed to the post-logout prompt.
            if chat_task in done:
                print('\n:: Logged out from chat. System is still running.')
                print(':: Press Ctrl+D for graceful shutdown, or Ctrl+C for immediate exit.')

                # This loop now correctly waits for a final shutdown signal after logout.
                while not unix.halt.is_set():
                    await aioconsole.ainput(prompt="")

            # If we get here, either the user initiated a shutdown from the post-logout
            # prompt, or the unix_task finished because of a `$ shutdown` command.
            # In either case, we should signal a halt to ensure everything stops.
            unix.halt.set()

        except EOFError:  # User pressed Ctrl+D after logging out
            print('\n:: Shutdown initiated...')
            unix.halt.set()  # Signal the kernel to shut down
        except (KeyboardInterrupt, CancelledError):  # User pressed Ctrl+C
            # MODIFIED BEHAVIOR: Only shut down if the chat task is already done.
            if chat_task.done():
                print('\n:: Exiting immediately.')
                unix.halt.set()
            else:
                # The user is still logged in. The interrupt was likely handled
                # by the interactive prompt or a running command. Do nothing here.
                pass
        finally:
            # Clean up any lingering tasks upon exit
            for task in pending:
                if not task.done():
                    task.cancel()
            # Await the main unix_task to allow graceful shutdown to complete
            if not unix_task.done():
                await unix_task

    print('GO!!')

    try:
        asyncio.run(async_run())
    except (KeyboardInterrupt, CancelledError):
        pass # already handled


def console(args=sys.argv[1:]):
    import asyncio

    terminal_mode = False
    if '-t' in args:
        terminal_mode = True
        args.remove('-t')

    if args:
        if len(args) != 1:
            print('1 argument required: <root>')
            return

        root = args[0]

    else:
        print('  >> Filesystem Root: ', end='')
        root = input()
        #if not root: return

    print('Preparing iosk UNIX... ', end='')
    from . import UNIX
    unix = UNIX(root=root)
    print('system loaded.')

    async def async_run():
        print()
        try:
            device = '/dev/terminal' if terminal_mode else None
            await unix.start()
            await asyncio.gather(unix.run(), unix.login('root', device=device))

        except asyncio.exceptions.CancelledError:
            print('Cancelled') # ^CCancelled

    print('GO!!')
    asyncio.run(async_run())


def system(args=sys.argv[1:]):
    import asyncio

    if args:
        if len(args) != 1:
            print('1 argument required: <root>')
            return

        root = args[0]

    else:
        print('  >> Filesystem Root: ', end='')
        root = input()
        #if not root: return

    print('Preparing iosk UNIX... ', end='')
    from . import UNIX
    unix = UNIX(root=root)
    print('system loaded.')

    async def async_run():
        print()
        try:
            await unix.start()
            await unix.run()

        except asyncio.exceptions.CancelledError:
            print('Cancelled') # ^CCancelled

    print('GO!!')
    asyncio.run(async_run())


SET = {
    'help': (help,
        'help for iosk commands'),
    'run': (run,
        'launch iosk system locally and connect to the chat as superuser'),
    'shell': (console,
        'launch iosk system with interactive command shell console; no chat'),
    'system': (system,
        'launch iosk system only; no chat, no shell'),
}

