# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..util import print_flush, open_browser

from PIL import ImageGrab
import pyautogui

import json
import subprocess
import time


PRE_PROMPT = '''
We act as a web browser agent.

Reply with a JSON list of maps where each map has a key named "action" whose value is one of the following: "open", "click", "type", "key", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

To resolve and open web paes:
{
    "action": "open",
    "prompt_to_open": "(required)",
}

To interact with visual elements with the mouse:
{
    "action": "click",
    "prompt_to_click": "(required)",
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
    return actions


def resolve_url(text):
    print(f'            @ {text}')

    prompt = 'Return simply the likely URL for the given site, or the word ' \
            + f"FAIL if the URL isn't known for this site: {text}"
    url = ai.prompt_for_text(prompt)
    if url.upper().startswith('FAIL'):
        print(f'            -!! {url}')
        #return None
        print(f' ***CONTINUIING ANYWAY***')
        return text

    else:
        print(f'            --> {url}')
        return url


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
            print(f'        ** {name}( {args} )')
            ok = fn(**args)
            if not ok:
                print(f'!!! action FAIL did not return True !!!')
                return False

        return True

    def do_open(self, prompt_to_open):
        url = resolve_url(prompt_to_open)
        if not url:
            return False

        proc = open_browser(url)
        print(f'   # opened pid {proc.pid}')

        print_flush('5(s) delay', end='')
        for i in range(5):
            print_flush('.', end='')
            time.sleep(1)

        return True

    def do_click(self, prompt_to_click):
        file = '/tmp/sidekick-shot.png'

        shot = ImageGrab.grab()
        w,h = shot.size
        shot.save(file)
        shot.close()

        '''
        prompt = 'Return a JSON map with the single key named "midpoint" and ' \
                + 'value is the [X,Y] coordinates for the midpoint of the ' \
                + f'region described as "{prompt_to_click}", or set midpoint ' \
                + f'JSON false if "{prompt_to_click}" cannot be found. The ' \
                + f'attached image is {w} px wide and {h} px high and 0,0 is ' \
                + 'the top-left position.'
        '''

        prompt = 'Return a JSON map with the single key named "bounding_box" ' \
                + 'and value is the bounding box of the region described as ' \
                + f'"{prompt_to_click}", or set bounding_box to JSON false if '\
                + f'"{prompt_to_click}" cannot be found. The image is a ' \
                + 'full-screen screenshot so start at 0,0 on the top left ' \
                + 'and do not ignore upper menu bars or other blank regions. ' \
                + 'Be sure to return of the form { "bounding_box": ' \
                + '[y1,x1,y2,x2] } or { "bounding_box": false }'

        print(f'   >>> {prompt}')
        box = ai.prompt_with_file_for_json(file=file, prompt=prompt, retries=2)
        print(f'   <<< {box}')

        box = json.loads(box)

        if 'bounding_box' in box and box['bounding_box']:
            box = box['bounding_box']
            y1,x1,y2,x2 = box
            # gemini bounding box training assumes 1000x1000 image
            x1 = x1 * w / 1000
            x2 = x2 * w / 1000
            y1 = y1 * h / 1000
            y2 = y2 * h / 1000
            pyautogui.moveTo(x1 + (x2-x1)/2, y1 + (y2-y1)/2, duration=5)

        else:
            print(f'            !,!= {box} (coordinates)')
            return None

        print_flush('5(s) delay', end='')
        for i in range(5):
            print_flush('.', end='')
            time.sleep(1)

        pyautogui.click()

        print_flush('5(s) delay', end='')
        for i in range(5):
            print_flush('.', end='')
            time.sleep(1)

        return True

    def do_type(self, text_to_type):
        print('FIXME do_type()') # FIXME

    def do_key(self, special_keys):
        print('FIXME do_key()') # FIXME

    def do_help(self, prompt):
        print('FIXME do_help()') # FIXME

