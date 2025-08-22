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

    if args:
        if len(args) != 2:
            print('2 arguments required: <root> <handle>')
            return

        root = args[0]
        handle = args[1]

    else:
        print('  >> Filesystem Root: ', end='')
        root = input()
        #if not root: return

        print('  >> Chat Handle (super): ', end='')
        handle = input()
        #if not handle: return

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
        try:
            await chat.start(handle=handle)
            io = await unix.start()
            results = await asyncio.gather(chat.run(), unix.run(io))
            #print(f'results: {results}')

        except asyncio.exceptions.CancelledError:
            print('Cancelled') # ^CCancelled

    print('GO!!')
    asyncio.run(async_run())


def console(args=sys.argv[1:]):
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
            await asyncio.gather(unix.run(), unix.login('root'))

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
            io = await unix.start()
            await unix.run(io)
            #print(f'results: {results}')

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

