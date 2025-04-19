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
Take the following prompt and select one or more agents from the list of available agents to handle the prompt or a section of it, in the appropriate sequential order. Consecutive agents of the same type should be collapsed into a single prompt, so there should not be two of the same agent in a row. Sometimes only one agent is needed. Assume the agents are capable of looking up the information they may need. Evaluate control logic first and pass in what it is controlling verbatim so it can do its own agent selection.

PROMPT:
'''


def prompt_for_agent(text, attachment=None, exclude=None):
    attach = '\nWe will also have a file attachment that will get passed to ' \
             'the first agent.\n' \
             if attachment else ''
    exclude = f'\nThe agent choice of "{exclude}" is currently unavailable.\n' \
            if exclude else ''
    agents = ai.prompt_for_json(PRE_PROMPT + attach + exclude + META_PROMPT
                                + text)
    print(agents)
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

        '''
        for name, agent, prompt in to_do:
            print()
            print(f'  ## {name} ##')
            agent.prompt_for_action(prompt)
        '''

    return to_do


def just_do_it(context, text, for_help=False):
    agents = prompt_for_agent(text, attachment=context.last_result)

    if for_help and agents[0][1].__name__ == context.last_agent.__name__:
        agents = prompt_for_agent(text, attachment=context.last_result,
                                  exclude=agents[0][1].__name__.split('.')[-1])

    for name, agent, prompt in agents:
        print()
        print(f'~~{name}~~')
        context.last_agent = agent

        actions = agent.prompt_for_action(prompt)
        result = actions.do(context)

        if result is None:
            print('!!! the agent failed to do actions !!!')
            #play_error()
            return None

    return result

