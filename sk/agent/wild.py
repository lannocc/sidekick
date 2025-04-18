# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..action import ActionsBase
from ..util import play_scratch, play_thinking

import json


PRE_PROMPT = '''
Reply with a JSON list of maps where each map has a key named "action" whose value is one of the following: "prompt", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

To prompt the AI system for something:
{
    "action": "prompt",
    "prompt_for_ai": "(required)"
}

To get help with anything else (catch-all pass-through to another handler):
{
    "action": "help",
    "prompt": "(required)"
}
'''


META_PROMPT = '''
Take the following prompt and select one or more actions from the list of available actions to handle the prompt or a section of it, in the appropriate sequential order.

PROMPT:
'''


def prompt_for_action(text):
    print(f'      >> {text}')

    actions = ai.prompt_for_json(PRE_PROMPT + META_PROMPT + text)
    print(f'      << {actions}')

    actions = Actions(json.loads(actions))
    return actions


class Actions(ActionsBase):
    def do_prompt(self, prompt_for_ai):
        play_thinking()
        reply = ai.prompt_for_text(prompt_for_ai)
        print(f'   <<< {reply}')
        return True

    def do_help(self, prompt):
        play_scratch()
        play_scratch()
        play_scratch()
        return False

