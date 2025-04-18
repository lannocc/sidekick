# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..action import ActionsBase
from ..util import print_flush, open_browser, take_screenshot
from ..util import play_ding, play_click, play_scratch, play_key, play_typing

import pyautogui

import json
import subprocess
import time


#We act as a web browser agent.
PRE_PROMPT = '''
Reply with a JSON list of maps for a web browser agent, where each map has a key named "action" whose value is one of the following: "open", "click", "type", "key", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

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
    "text_to_type": "(required)",
    "prompt_where_to_focus": "(optional, description of screen area)"
}

To operate various special keys like enter, control, function keys etc.:
{
    "action": "key",
    "special_keys": "(required, one or more key names separated by space)"
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


def resolve_url(text):
    print(f'            @ {text}')

    prompt = 'Return simply a likely URL for this description, or the word ' \
            + f"FAIL if a good URL isn't known for this: {text}"
    url = ai.prompt_for_text(prompt)
    if url.upper().startswith('FAIL'):
        print(f'            -!! {url}')
        #return None
        print(f' ***CONTINUIING ANYWAY***')
        return text

    else:
        print(f'            --> {url}')
        return url


def get_screen_region(region_description):
    file, w, h = take_screenshot()

    '''
    prompt = 'Return a JSON map with the single key named "midpoint" and ' \
            + 'value is the [X,Y] coordinates for the midpoint of the ' \
            + f'region described as "{region_description}", or set midpoint ' \
            + f'JSON false if "{prompt_to_click}" cannot be found. The ' \
            + f'attached image is {w} px wide and {h} px high and 0,0 is ' \
            + 'the top-left position.'
    '''

    prompt = 'Return a JSON map with the single key named "bounding_box" ' \
            + 'and value is the bounding box of the region described as ' \
            + f'"{region_description}", or set bounding_box to JSON false if '\
            + f'"{region_description}" cannot be found. The image is a ' \
            + 'full-screen screenshot so start at 0,0 on the top left ' \
            + 'and do not ignore upper menu bars or other blank regions. ' \
            + 'Be sure to return of the form { "bounding_box": ' \
            + '[y1,x1,y2,x2] } or { "bounding_box": false }'

    #print(f'   >>> {prompt}')
    box = ai.prompt_with_file_for_json(file=file, prompt=prompt, retries=2)
    #print(f'   <<< {box}')

    box = json.loads(box)

    if not ('bounding_box' in box and box['bounding_box']):
        print(f'            !,!= {box} (coordinates)')
        return None

    box = box['bounding_box']
    y1,x1,y2,x2 = box
    # gemini bounding box training assumes 1000x1000 image
    x1 = x1 * w / 1000
    x2 = x2 * w / 1000
    y1 = y1 * h / 1000
    y2 = y2 * h / 1000

    return x1,y1,x2,y2


def mouse_click_region(region):
    x1, y1, x2, y2 = region

    pyautogui.moveTo(x1, y1, duration=1)
    play_ding()
    pyautogui.moveTo(x1, y2, duration=.1)
    play_ding()
    pyautogui.moveTo(x2, y2, duration=.1)
    play_ding()
    pyautogui.moveTo(x2, y1, duration=.1)
    play_ding()
    pyautogui.moveTo(x1, y1, duration=.1)
    play_ding()

    pyautogui.moveTo(x1 + (x2-x1)/2, y1 + (y2-y1)/2, duration=1)

    #print_flush('5(s) delay', end='')
    #for i in range(5):
    #    print_flush('.', end='')
    #    time.sleep(1)
    #print()

    play_click()
    pyautogui.click()


def delay(sec):
    print_flush(f'{sec}(s) delay', end='')
    for i in range(sec):
        print_flush('.', end='')
        time.sleep(1)
    print()


class Actions(ActionsBase):
    def do_open(self, prompt_to_open):
        url = resolve_url(prompt_to_open)
        if not url:
            return False

        proc = open_browser(url)
        print(f'   # opened pid {proc.pid}')

        delay(10)
        return True

    def do_click(self, prompt_to_click):
        region = get_screen_region(prompt_to_click)
        if not region: return False

        mouse_click_region(region)

        delay(7)
        return True

    def do_type(self, text_to_type, prompt_where_to_focus=None):
        if prompt_where_to_focus:
            region = get_screen_region(prompt_where_to_focus)
            if not region: return False

            mouse_click_region(region)

            delay(1)

        play_typing()
        pyautogui.write(text_to_type, interval=0.2)

        delay(3)
        return True

    def do_key(self, special_keys):
        for key in special_keys.split(' '):
            play_key()
            pyautogui.press(key)

            delay(1)

        delay(7)
        return True

    def do_help(self, prompt):
        play_scratch()
        from . import just_do_it
        return just_do_it(prompt)

