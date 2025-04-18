# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..action import ActionsBase
from ..util import print_flush, play_scratch


import json
import time


PRE_PROMPT = '''
Reply with a JSON list of maps for a timing control agent, where each map has a key named "action" whose value is one of the following: "delay", "loop", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

To sleep or wait for some time to pass:
{
    "action": "delay",
    "seconds_to_wait": "(required)"
}

To do something more than once:
{
    "action": "loop",
    "prompt_to_repeat": "(required)",
    "times_to_loop": "(required)"
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


def delay(sec):
    print_flush(f'{sec}(s) delay', end='')
    for i in range(sec):
        print_flush('.', end='')
        time.sleep(1)
    print()


class Actions(ActionsBase):
    def do_delay(self, seconds_to_wait):
        delay(int(seconds_to_wait))
        return True

    def do_loop(self, prompt_to_repeat, times_to_loop):
        from . import just_do_it

        for x in range(int(times_to_loop)):
            print(f'   /-\\ LOOP {x+1} of {times_to_loop} /-\\')
            ok = just_do_it(prompt_to_repeat)
            if not ok: return False

            delay(4)

        return True

    def do_help(self, prompt):
        play_scratch()
        from . import just_do_it
        return just_do_it(prompt)

