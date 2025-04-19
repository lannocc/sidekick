# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..action import ActionsBase, FileResult
from ..util import print_flush, play_scratch

import os
import shutil
import tempfile


PRE_PROMPT = '''
Reply with a JSON list of maps where each map has a key named "action" whose value is one of the following: "move", "copy", "delete", "folder", "read", "write", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

To move a file or folder:
{
    "action": "move",
    "source": "(required, absolute path)",
    "destination": "(required, absolute path)"
}

To copy a file or folder:
{
    "action": "copy",
    "source": "(required, absolute path)",
    "destination": "(required, absolute path)"
}

To delete a file or folder:
{
    "action": "delete",
    "resource": "(required, absolute path)"
}

To create a new folder:
{
    "action": "folder",
    "parent": "(required, absolute path)"
    "name": "(required, folder name)"
}

To read the contents of a file:
{
    "action": "read",
    "file_path": "(required, absolute path)"
}

To write content to a file:
{
    "action": "write",
    "file_path": "(required, absolute path)",
    "content": "(required, string to write)",
    "append": (optional, defaults to false, boolean: whether to append to the file or overwrite it)
}

To get help with anything else (catch-all pass-through to another handler):
{
    "action": "help",
    "prompt": "(required)"
}
'''


META_PROMPT = '''
Take the following prompt and select one or more actions from the list of available actions to handle the prompt or a section of it, in the appropriate sequential order.  Be sure to provide absolute paths for file operations.  Use the previous result file if necessary for the current prompt. If the prompt requires a file as the *end* result, create one in /tmp and populate it if the environment offers this directory, and return it as a `FileResult`, otherwise indicate this inability to the user. If the user does not supply full paths to files, reply only with a prompt action to the AI system explaining this and providing context as to what the user asked. Assume that the agent is capable of looking up the information it may need.

PROMPT:
'''


def prompt_for_action(text):
    print(f'      >> {text}')

    actions = ai.prompt_for_json(PRE_PROMPT + META_PROMPT + text)
    print(f'      << {actions}')

    actions = Actions(actions)
    return actions


class Actions(ActionsBase):
    def do_move(self, context, source, destination):
        try:
            shutil.move(source, destination)
            print(f'   # moved {source} to {destination}')
            return FileResult(destination)
        except Exception as e:
            print(f'   !!! move failed: {e}')
            return None

    def do_copy(self, context, source, destination):
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            print(f'   # copied {source} to {destination}')
            return FileResult(destination)
        except Exception as e:
            print(f'   !!! copy failed: {e}')
            return None

    def do_delete(self, context, resource):
        try:
            if os.path.isdir(resource):
                shutil.rmtree(resource)
            else:
                os.remove(resource)
            print(f'   # deleted {resource}')
            return context.last_result # keep previous result

        except Exception as e:
            print(f'   !!! delete failed: {e}')
            return None

    def do_folder(self, context, parent, name):
        path = os.path.join(parent, name)
        try:
            os.makedirs(path, exist_ok=True)
            print(f'   # created folder {path}')
            return FileResult(path)
        except Exception as e:
            print(f'   !!! folder creation failed: {e}')
            return None

    def do_read(self, context, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f'   # read {file_path}')
            return content # return the string, not a FileResult

        except Exception as e:
            print(f'   !!! read failed: {e}')
            return None

    def do_write(self, context, file_path, content, append=False):
        mode = 'a' if append else 'w'
        try:
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            print(f'   # wrote to {file_path} (append={append})')
            return FileResult(file_path)
        except Exception as e:
            print(f'   !!! write failed: {e}')
            return None


    def do_help(self, context, prompt):
        play_scratch()
        from . import just_do_it
        return just_do_it(context, prompt)

