# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..ai import google as ai
from ..action import ActionsBase
from ..util import print_flush, delay, play_scratch
from .common import create_action_prompter



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


class Actions(ActionsBase):
    def do_delay(self, context, seconds_to_wait, quiet=False, chatter=False):
        delay(int(seconds_to_wait), quiet=quiet)
        return context.last_result

    def do_loop(self, context, prompt_to_repeat, times_to_loop, quiet=False,
                chatter=False):
        from . import just_do_it

        for x in range(int(times_to_loop)):
            if not quiet: print(f'   /-\\ LOOP {x+1} of {times_to_loop} /-\\')
            result = just_do_it(context, prompt_to_repeat, quiet=quiet,
                                chatter=chatter)
            if result is None: return None

            delay(4, quiet=quiet)

        return result


prompt_for_action = create_action_prompter(PRE_PROMPT, META_PROMPT, Actions)