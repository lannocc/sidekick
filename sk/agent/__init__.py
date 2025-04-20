# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from . import control
from . import file
from . import browser
from . import speech
from . import wild
#from ..util import play_error


SET = [
    (control, 'basic timing control like waiting, looping, scheduling'),
    (file, 'perform filesystem and git commands'),
    (browser, 'access the Internet and interact with the screen, mouse, and '
                +'keyboard'),
    (speech, 'talk aloud or say something'),
    (wild, 'catch-all for anything not understood or handled by the others'),
]


PRE_PROMPT = '''
Reply with a JSON list of maps where each map has values for these 2 keys:
    "agent" :: name of the agent
    "prompt" :: prompt for the agent

The available agents are:
'''
for agent, desc in SET:
    name = agent.__name__.split('.')[-1]
    PRE_PROMPT += f'    "{name}" :: {desc}\n'
PRE_PROMPT += '''
All agents automatically receive an attachment with the result of the previous
agent.
'''


META_PROMPT = '''
Take the following prompt and select one or more agents from the list of available agents to handle the prompt or a section of it, in the appropriate sequential order. If the same agent would be called more than once consecutively then just call it once and it will handle the rest. Sometimes only one agent is needed. Assume the agents are capable of looking up the information they may need. Evaluate control logic first and pass in what it is controlling verbatim so it can do its own agent selection.

PROMPT:
'''


def prompt_for_agent(text, attachment=None, exclude=None, quiet=False,
                     chatter=False):
    attach = '\nWe will also have a file attachment that will get passed to ' \
             'the first agent.\n' \
             if attachment else ''
    exclude = f'\nThe agent choice of "{exclude}" is currently unavailable.\n' \
            if exclude else ''
    agents = ai.prompt_for_json(PRE_PROMPT + attach + exclude + META_PROMPT
                                + text, chatter=chatter)
    if not quiet: print(agents)
    to_do = [ ]

    for agent in agents:
        name = agent['agent']
        prompt = agent['prompt']
        found = False

        for agent, desc in SET:
            if agent.__name__.split('.')[-1] == name:
                found = True
                to_do.append((name, agent, prompt))
                break

        assert found

    return to_do


def just_do_it(context, text, for_help=False, quiet=False, chatter=False):
    agents = prompt_for_agent(text, attachment=context.last_result, quiet=quiet,
                              chatter=chatter)

    if for_help and agents[0][1].__name__ == context.last_agent.__name__:
        agents = prompt_for_agent(text, attachment=context.last_result,
                                  exclude=agents[0][1].__name__.split('.')[-1],
                                  quiet=quiet, chatter=chatter)

    for name, agent, prompt in agents:
        if not quiet:
            print()
            print(f'~~{name}~~')
        context.last_agent = agent

        actions = agent.prompt_for_action(prompt, quiet=quiet, chatter=chatter)
        result = actions.do(context, quiet=quiet, chatter=chatter)

        if result is None:
            print('!!! the agent failed to do actions !!!')
            #play_error()
            return None

    return result

