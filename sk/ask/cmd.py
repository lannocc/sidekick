# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush

print = print_flush


def main(args):
    print('SIDEKICK ASK: ', end='')

    cmd = args[0] if args else 'help'
    args = args[1:]

    if cmd in SET:
        cmd = SET[cmd]
        print(cmd[1])
        cmd[0](args)

    else:
        print(f'unknown command: {cmd}')
        print('Try `sk ask help` for a list of commands.')


def help(args):
    print()
    print('USAGE:')
    print('   sk ask <command>')
    print()
    print('The following commands are available:')
    for name, cmd in SET.items():
        print(f'   {name} - {cmd[1]}')


def prompt(args):
    if args:
        if len(args) < 1:
            print('at least 1 argument required: <prompt>')
            return

        prompt = ' '.join(args)

    else:
        print('  >> Prompt: ', end='')
        prompt = input()
        if not prompt: return

    from .. import ai
    reply = ai.prompt_for_text(prompt)
    print(f'  << {reply}')



def list_asks(args):
    print('  << Retrieving Ask History...')
    '''
    from . import SET as AGENTS

    for agent, desc in AGENTS:
        name = agent.__name__.split('.')[-1]
        print(f'    [{name}] {desc}')

    return len(AGENTS) > 0
    '''
    return False



SET = {
    'help': (help,
        'help for ask commands'),
    'prompt': (prompt,
        'ask a question'),
    #'list': (list_asks,
    #    'list ask history'),
}

