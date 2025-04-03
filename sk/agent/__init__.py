# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from . import file
from . import wild

import json


SET = [
    (file, 'perform filesystem and git commands'),
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


META_PROMPT = '''
Take the following prompt and select one or more agents from the list of available agents to handle the prompt or a section of it, in the appropriate sequential order.

PROMPT:
'''


def prompt_for_agent(text):
    agents = ai.prompt_for_json(PRE_PROMPT + META_PROMPT + text)
    print(agents)

    for agent in json.loads(agents):
        name = agent['agent']
        prompt = agent['prompt']
        found = False
        to_do = [ ]

        for agent, desc in SET:
            if agent.__name__.split('.')[-1] == name:
                found = True
                to_do.append((name, agent, prompt))
                break

        assert found

        for name, agent, prompt in to_do:
            print()
            print(f'  ## {name} ##')
            agent.prompt_for_action(prompt)

