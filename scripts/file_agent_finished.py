# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..action import ActionsBase
from ..util import print_flush, play_scratch, play_error

import json
import os
import shutil


PRE_PROMPT = '''
Reply with a JSON list of maps where each map has a key named "action" whose value is one of the following: "move", "copy", "delete", "folder", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

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
    def do_move(self, source, destination):
        try:
            shutil.move(source, destination)
            print(f'   # Moved {source} to {destination}')
            return True
        except Exception as e:
            print(f'   !!! Failed to move {source} to {destination}: {e}')
            play_error()
            return False

    def do_copy(self, source, destination):
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination) # copy with metadata
            else:
                shutil.copytree(source, destination) # copy directory
            print(f'   # Copied {source} to {destination}')
            return True
        except Exception as e:
            print(f'   !!! Failed to copy {source} to {destination}: {e}')
            play_error()
            return False

    def do_delete(self, resource):
        try:
            if os.path.isfile(resource):
                os.remove(resource)
            else:
                shutil.rmtree(resource)
            print(f'   # Deleted {resource}')
            return True
        except Exception as e:
            print(f'   !!! Failed to delete {resource}: {e}')
            play_error()
            return False

    def do_folder(self, parent, name):
        try:
            path = os.path.join(parent, name)
            os.makedirs(path)
            print(f'   # Created folder {path}')
            return True
        except Exception as e:
            print(f'   !!! Failed to create folder {parent}/{name}: {e}')
            play_error()
            return False

    def do_help(self, prompt):
        play_scratch()
        from . import just_do_it
        return just_do_it(prompt)

