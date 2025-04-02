# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .util import print_flush

print = print_flush


def main(args):
    print('SIDEKICK: ', end='')

    '''
    cmd = args[0] if args else 'help'
    args = args[1:]

    if cmd in SET:
        cmd = SET[cmd]
        print(cmd[1])
        cmd[0](args)

    else:
        print(f'unknown command: {cmd}')
        print('Try `ask help` for a list of commands.')
    '''

    if not args:
        print('need a prompt')
        return

    while args and args[0].startswith('-'):
        op = args[0]
        args = args[1:]

        if op in OPTIONS:
            op = OPTIONS[op]
            print(op[1])
            op[0](None)

        else:
            print(f'unknown option: {op}')
            return


def help(args):
    print('AI SideKick')
    print()
    print('USAGE:')
    print('   sk [options]')
    print('   ask [options] <question-prompt>')
    print('   task [options] <command-prompt>')
    print()
    #print('The following commands are available:')
    #for name, cmd in SET.items():
    #    print(f'   {name} - {cmd[1]}')


def version(args):
    from . import __version__
    print(f'Installed version is {__version__}')



OPTIONS = {
    '-h': (help,
        'help for this program'),
    '-v': (version,
        'version information'),
}

