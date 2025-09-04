# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .util import print_flush, package_directory, take_screenshot

print = print_flush


def main(args, called=''):
    quiet = '-q' in args
    chatter = '-c' in args
    if not quiet: print('SIDEKICK: ', end='')

    task = called.endswith('task')
    ask = not task and called.endswith('ask')

    shot = False
    file = None
    pkg = None

    # options
    while args and args[0].startswith('-'):
        op = args[0]
        args = args[1:]

        if op in OPTIONS:
            ops = OPTIONS[op]

            if ops[0] is help or ops[0] is version:
                print(ops[1])
                ops[0](None)
                return

            elif op == '-s':
                shot = True

            elif op == '-f':
                if args:
                    file = args[0]
                    args = args[1:]

                if not file:
                    print(f'!!! need a filename to upload')
                    return

            elif op == '-p':
                if args:
                    pkg = args[0]
                    args = args[1:]

                if not pkg:
                    print(f'!!! need a directory path to package')
                    return

        else:
            print(f'!!! unknown option: {op}')
            return

    # prompt mode
    if task or ask:
        #if not args:
        #    print('need a prompt')
        #    return

        if len(args) > 1: prompt = ' '.join(args)
        elif args: prompt = args[0]
        else: prompt = None

        if task: do_task(prompt, shot=shot, file=file, package=pkg, quiet=quiet,
                         chatter=chatter)
        else: ask_question(prompt, shot=shot, file=file, package=pkg,
                           quiet=quiet, chatter=chatter)

        return

    # command mode
    cmd = args[0] if args else None #'help'
    args = args[1:]

    if cmd not in COMMANDS:
        if cmd is None:
            print('!!! need an option or command')
            #help(args)

        else:
            print(f'!!! unknown command: {cmd}')

        if not quiet: print('Try `sk help` for a list of commands.')

        return

    cmd = COMMANDS[cmd]
    if not quiet: print(cmd[1])
    cmd[0](args)


def ask_question(prompt=None, shot=False, file=None, package=None, quiet=False,
                 chatter=False):
    from . import ai

    if not quiet:
        print('Ask a Question')
        print()

    if shot or file or package:
        if sum([ 1 for item in [ shot, file, package ] if item ]) > 1:
            print('!!! only one of screenshot OR file OR package at a time !!!')
            return

        if shot:
            file, w, h = take_screenshot()
            if not quiet: print(f'SAVED SCREENSHOT to: {file}')

        elif package:
            file = package_directory(package)
            if not quiet: print(f'PACKAGED DIRECTORY to: {file}')

    if prompt:
        print(f' >> {prompt}')

    else:
        print(' >> ', end='')
        prompt = input()

    if not prompt:
        return

    if file:
        answer = ai.prompt_with_file_for_text(prompt, file, chatter=chatter)

    else:
        answer = ai.prompt_for_text(prompt, chatter=chatter)

    print()
    print(f' << {answer}')
    print()


def do_task(prompt=None, shot=False, file=None, package=None, quiet=False,
            chatter=False):
    from . import agent
    from .action import Context
    from .util import play_error, play_success

    if not quiet:
        print('Perform a Task')
        print()

    if shot or file or package:
        if sum([ 1 for item in [ shot, file, package ] if item ]) > 1:
            print('!!! only one of screenshot OR file OR package at a time !!!')
            return

        if shot:
            file, w, h = take_screenshot()
            if not quiet: print(f'SAVED SCREENSHOT to: {file}')

        elif package:
            file = package_directory(package)
            if not quiet: print(f'PACKAGED DIRECTORY to: {file}')

    if prompt:
        if not quiet: print(f' >> {prompt}')

    else:
        print(' >> ', end='')
        prompt = input()

    if not prompt:
        return

    if not quiet: print()
    context = Context(file)

    try:
        result = agent.just_do_it(context, prompt, quiet=quiet, chatter=chatter)

        if result is not None:
            play_success()
            return result

        else:
            play_error()
            return None

    except Exception as e:
        play_error()
        raise e


def help(args):
    print('AI SideKick')
    print()
    print('GENERAL USAGE:')
    #print('     sk [options] <command> [args...]')
    print('    ask [options] <question-prompt>')
    print('   task [options] <command-prompt>')
    print()
    #print('Use `sk` for sidekick commands, `ask` questions, `task` for tasks.')
    print('Use `ask` to get a reply to a question or other prompt.')
    print('Use `task` to invoke our agents to do something useful.')
    print()
    print('The following general options are available:')
    for name, opt in OPTIONS.items():
        print(f'   {name} :: {opt[1]}')
    print()
    print('SEE ALSO:')
    print('     sk help')


def version(args):
    from . import __version__
    print(f'Installed version is {__version__}')


def help_cmds(args):
    print('SideKick AI Admin')
    print()
    print('COMMAND USAGE:')
    print('     sk [options] <command> [args...]')
    print()
    print('Use `sk` to command and evaluate at a modular level.')
    print()
    print('The following commands are available:')
    for name, cmd in COMMANDS.items():
        print(f'   {name} :: {cmd[1]}')
    print()
    print('SEE ALSO:')
    print('    ask -h')
    print('   task -h')


def agent(args):
    from .agent.cmd import main as agent_main

    agent_main(args)


def action(args):
    from .action.cmd import main as action_main

    action_main(args)


def ticket(args):
    from . import ticket

    if args:
        if len(args) != 1:
            print('1 argument required: <ticket-number>')
            return

        num = args[0]

    else:
        print('  >> Ticket Number: ', end='')
        num = input()
        if not num: return

        print('  <<')
        print()

    if num.upper().startswith('T'):
        num = num[1:]

    ticket.view(int(num))


def tree(args):
    from .util import get_directory_tree_as_text

    md = False
    count = False

    while args and args[0].startswith('-'):
        op = args[0]
        args = args[1:]

        if op == '-h':
            print()
            print('COMMAND USAGE:')
            #print('     sk [options] <command> [args...]')
            print('    sk [general-opts] tree [tree-opts] <directory>')
            print()
            print('The following tree command options are available:')
            print('   -h  :: help for tree command')
            print('   -md :: markdown compatible output')
            print('   -c  :: count bytes and tokens')
            print()
            print('See `sk -h` for general options.')
            return

        elif op == '-md':
            md = True

        elif op == '-c':
            count = True

        else:
            print(f'!!! unknown tree option: {op}')
            return

    if args:
        if len(args) != 1:
            print('1 argument required: <directory>')
            return

        path = args[0]

    else:
        print('  >> Directory: ', end='')
        path = input()
        if not path: return

        print('  <<')
        print()

    print(get_directory_tree_as_text(path, markdown=md, count=count))


'''
def ask(args):
    from .ask.cmd import main as ask_main

    ask_main(args)
'''


def iosk(args):
    from .iosk.cmd import main as iosk_main

    iosk_main(args)


OPTIONS = {
    '-h': (help,
        'general help for sidekick'),
    '-v': (version,
        'version information'),
    '-q': (None,
        'quiet operation (limited effect)'),
    '-c': (None,
        'print all chatter (even when quiet is enabled)'),
    '-s': (None,
        'take screenshot to use with prompt'),
    '-f': (None,
        'upload file with -f <filename>'),
    '-p': (None,
        'package directory text contents and upload with -p <directory>'),
}


COMMANDS = {
    'help': (help_cmds,
        'help for sidekick commands'),
    'ver': (version,
        'version information'),
    'agent': (agent,
        'agents'),
    'action': (action,
        'actions'),
    'ticket': (ticket,
        'view ticket'),
    'tree': (tree,
        'print a directory tree'),
    #'ask': (ask,
    #    'ask commands'),
    'iosk': (iosk,
        'iosk commands'),
}

