# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..ai import google as ai


def create_action_prompter(pre_prompt, meta_prompt, actions_class):
    def prompt_for_action(text, quiet=False, chatter=False):
        if not quiet: print(f'      >> {text}')
        actions = ai.prompt_for_json(pre_prompt + meta_prompt + text,
                                     chatter=chatter)
        if not quiet: print(f'      << {actions}')
        return actions_class(actions)
    return prompt_for_action