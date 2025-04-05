# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai

import json


PRE_PROMPT = '''
We act as a web browser agent.

Reply with a JSON list of maps where each map has a key named "action" whose value is one of the following: "open", "click", "type", "key", or "help". Each possible type of action map is described with additional keys below...

To resolve and open web paes:
{
    "action": "open",
    "what_to_open": "(required)",
}

To interact with visual elements with the mouse:
{
    "action": "click",
    "what_to_click": "(required)",
}

To enter text with the keyboard:
{
    "action": "type",
    "text_to_type": "(required)"
}

To operate various special keys like enter, control, function keys etc.:
{
    "action": "key",
    "special_keys": "(required)"
}

To get help with anything else (catch-all):
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


class Actions:
    def __init__(self, actions):
        self.to_do = [ ]

        for action in actions:
            name = action['action']
            del action['action']
            fn = getattr(self, 'do_' + name)
            self.to_do.append((name, fn, action))

    def do(self):
        for name, fn, args in self.to_do:
            print('        ** {name}( {args} )')

    def do_move(self, source, destination):
        pass

    def do_copy(self, source, destination):
        pass

    def do_delete(self, resource):
        pass

    def do_folder(self, parent, name):
        pass

    def do_help(self, prompt):
        pass

