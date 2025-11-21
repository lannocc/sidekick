# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..ai import google as ai
from ..action import ActionsBase
from .common import create_action_prompter


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


class Actions(ActionsBase):
    def do_move(self, context, source, destination, quiet=False, chatter=False):
        pass # FIXME

    def do_copy(self, context, source, destination, quiet=False, chatter=False):
        pass # FIXME

    def do_delete(self, context, resource, quiet=False, chatter=False):
        pass # FIXME

    def do_folder(self, context, parent, name, quiet=False, chatter=False):
        pass # FIXME


prompt_for_action = create_action_prompter(PRE_PROMPT, META_PROMPT, Actions)