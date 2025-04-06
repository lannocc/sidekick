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
    opts = False

    while args and args[0].startswith('-'):
        op = args[0]
        args = args[1:]

        if op in OPTIONS:
            opts = True
            op = OPTIONS[op]
            print(op[1])
            op[0](None)

            if op[0] is help or op[0] is version:
                return

        else:
            print(f'unknown option: {op}')
            return

    # prompt mode
    if task or ask:
        if not args:
            print('need a prompt')
            return

        if len(args) > 1: prompt = ' '.join(args)
        else: prompt = args[0]

        if task: do_task(prompt)
        else: ask_question(prompt)

        return

    # command mode
    cmd = args[0] if args else 'help'
    args = args[1:]

    if cmd not in COMMANDS:
        if cmd is None:
            print('need an option or command')
            help(args)

        else:
            print(f'unknown command: {cmd}')
            print('Try `sk help` for a list of commands.')

        return

    cmd = COMMANDS[cmd]
    print(cmd[1])
    cmd[0](args)


def ask_question(prompt):
    from . import ai

    print('Ask a Question')
    print()
    print(f' >> {prompt}')
    print()

    answer = ai.prompt_for_text(prompt)
    print(f' << {answer}')
    print()


def do_task(prompt):
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
    print('     sk [options] <command> [args...]')
    print('    ask [options] <question-prompt>')
    print('   task [options] <command-prompt>')
    print()
    print('Use `sk` for sidekick commands, `ask` questions, `task` for tasks.')
    print()
    print('The following general options are available:')
    for name, opt in OPTIONS.items():
        print(f'   {name} :: {opt[1]}')


def version(args):
    from . import __version__
    print(f'Installed version is {__version__}')


def help_cmds(args):
    print('AI SideKick')
    print()
    print('COMMAND USAGE:')
    print('   sk [options] <command> [args...]')
    print()
    print('The following commands are available:')
    for name, cmd in COMMANDS.items():
        print(f'   {name} :: {cmd[1]}')


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
        'general help for sidekick options'),
    '-v': (version,
        'version information'),
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

