# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .util import print_flush

print = print_flush


def main(args, called=''):
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

    task = called.endswith('task')
    ask = not task and called.endswith('ask')

    shot = False
    file = None

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
                    print(f'need a filename to upload')
                    return

        else:
            print(f'unknown option: {op}')
            return

    # prompt mode
    if task or ask:
        #if not args:
        #    print('need a prompt')
        #    return

        if len(args) > 1: prompt = ' '.join(args)
        elif args: prompt = args[0]
        else: prompt = None

        if task: do_task(prompt, shot=shot, file=file)
        else: ask_question(prompt, shot=shot, file=file)

        return

    # command mode
    cmd = args[0] if args else None #'help'
    args = args[1:]

    if cmd not in COMMANDS:
        if cmd is None:
            print('need an option or command')
            #help(args)

        else:
            print(f'unknown command: {cmd}')

        print('Try `sk help` for a list of commands.')

        return

    cmd = COMMANDS[cmd]
    print(cmd[1])
    cmd[0](args)


def ask_question(prompt=None, shot=False, file=None):
    from . import ai
    from .util import take_screenshot

    print('Ask a Question')
    print()

    if prompt:
        print(f' >> {prompt}')

    else:
        print(' >> ', end='')
        prompt = input()

    if not prompt:
        return

    print()

    if shot or file:
        if shot and file:
            print('!!! only screenshot OR file supported at this time !!!')
            return

        if shot:
            file, w, h = take_screenshot()

        answer = ai.prompt_with_file_for_text(prompt, file)

    else:
        answer = ai.prompt_for_text(prompt)

    print(f' << {answer}')
    print()


def do_task(prompt=None, shot=False, file=None):
    from . import agent

    print('Perform a Task')
    print()
    print(f' >> {prompt}')
    print()

    agents = agent.prompt_for_agent(prompt)

    for name, agent, prompt in agents:
        print()
        print(f'~~{name}~~')

        actions = agent.prompt_for_action(prompt)
        ok = actions.do()

        if not ok:
            print('!!! the agent failed to do actions !!!')
            return False

    return True


def help(args):
    print('AI SideKick')
    print()
    print('GENERAL USAGE:')
    #print('     sk [options] <command> [args...]')
    print('    ask [options] <question-prompt>')
    print('   task [options] <command-prompt>')
    print()
    #print('Use `sk` for sidekick commands, `ask` questions, `task` for tasks.')
    print('Use `ask` to get a reply to a question or other promot.')
    print('Use `task` to invoke our agents to do something.')
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


def ask(args):
    from .ask.cmd import main as ask_main

    ask_main(args)



OPTIONS = {
    '-h': (help,
        'general help for sidekick'),
    '-v': (version,
        'version information'),
    '-s': (None,
        'take screenshot to use with prompt'),
    '-f': (None,
        'upload file with -f <filename>'),
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
    'ask': (ask,
        'ask commands'),
}

