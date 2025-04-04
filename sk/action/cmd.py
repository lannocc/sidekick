# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush

print = print_flush


def main(args):
    print('SIDEKICK ACTION: ', end='')

    cmd = args[0] if args else 'help'
    args = args[1:]

    if cmd in SET:
        cmd = SET[cmd]
        print(cmd[1])
        cmd[0](args)

    else:
        print(f'unknown command: {cmd}')
        print('Try `sk action help` for a list of commands.')


def help(args):
    print()
    print('USAGE:')
    print('   sk action <command>')
    print()
    print('The following commands are available:')
    for name, cmd in SET.items():
        print(f'   {name} - {cmd[1]}')


def prompt(args):
    from ..agent.cmd import list_agents

    if args:
        if len(args) < 2:
            print('at least 2 arguments required: <agent> <prompt>')
            return

        agent = args[0]
        prompt = ' '.join(args[1:])

    else:
        if not list_agents([ ]): return
        print('  >> Agent: ', end='')
        agent = input()
        if not agent: return

        print('  >> Prompt: ', end='')
        prompt = input()
        if not prompt: return

    from ..agent import prompt_for_agent, SET as AGENTS
    found = None
    for sagent, desc in AGENTS:
        name = sagent.__name__.split('.')[-1]
        if name == agent:
            found = sagent
            break

    if not found:
        print('!! agent not found')
        return

    sagent.prompt_for_action(prompt)


def list_actions(args):
    from ..agent.cmd import list_agents

    if args:
        if len(args) != 1:
            print('1 argument required: <agent>')
            return

        agent = args[0]

    else:
        if not list_agents([ ]): return
        print('  >> Agent: ', end='')
        agent = input()
        if not agent: return

    from ..agent import SET as AGENTS
    found = None
    for sagent, desc in AGENTS:
        name = sagent.__name__.split('.')[-1]
        if name == agent:
            found = sagent
            break

    if not found:
        print('!! agent not found')
        return

    print('FIXME') # FIXME



SET = {
    'help': (help,
        'help for action commands'),
    'prompt': (prompt,
        'prompt agent to decide on action(s) to take'),
    'list': (list_actions,
        'list available agent actions'),
}

