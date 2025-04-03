# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai

import json


PRE_PROMPT = '''
Reply with a JSON list of maps where each map has a key named "action" whose value is one of the following: "move", "copy", "delete", "folder", or "help". Each possible type of action map is described with additional keys below...

To move a file or folder:
{
    "action": "move",
    "source": "(required)",
    "destination": "(required)"
}

To copy a file or folder:
{
    "action": "copy",
    "source": "(required)",
    "destination": "(required)"
}

To delete a file or folder:
{
    "action": "delete",
    "resource": "(required)"
}

To create a new folder:
{
    "action": "folder",
    "parent": "(required)"
    "name": "(required)"
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

