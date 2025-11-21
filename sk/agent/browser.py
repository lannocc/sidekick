# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..ai import google as ai
from ..action import ActionsBase, FileResult
from ..util import print_flush, delay, open_browser, take_screenshot#, \
                   #extract_and_save_region
from ..util import play_ding, play_click, play_scratch, play_key, play_typing
from .common import create_action_prompter

import pyautogui

import subprocess


#We act as a web browser agent.
PRE_PROMPT = '''
Reply with a JSON list of maps for a web browser agent, where each map has a key named "action" whose value is one of the following: "open", "click", "type", "key", or "help". Each possible type of action map is described with additional keys below (be descriptive or verbatim if possible for the additional prompt key values)...

To resolve and open web pages:
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
    "text_to_type": "(either text_to_type or text_from_ai must be present)",
    "text_from_ai": "(either text_to_type or text_from_ai must be present)",
    "where_to_focus": "(optional, description of screen area)"
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
Take the following prompt and select one or more actions from the list of available actions to handle the prompt or a section of it, in the appropriate sequential order. Use the actions to operate a search engine if necessary to look something up.

PROMPT:
'''


def resolve_url(text, quiet=False, chatter=False):
    if not quiet: print(f'            @ {text}')

    '''
    prompt = 'Return simply a likely URL for this description, or the word ' \
            + f"FAIL if a good URL isn't known for this: {text}"
    url = ai.prompt_for_text(prompt, chatter=chatter)
    if url.upper().startswith('FAIL'):
        print(f'            -!! {url}')
        #return None
        print(f' ***CONTINUING ANYWAY***')
        return text

    else:
        print(f'            --> {url}')
        return url
    '''

    pre = 'Reply with a JSON map with the following keys:\n' \
          '{\n' \
          '    "output": str,\n' \
          '    "is_url": bool\n' \
          '}\n\n' \
          'The JSON map should be a reply to the following prompt:\n\n'

    reply = { 'is_url': False }
    tries = 0

    while not reply['is_url']:
        if tries > 3:
            print(f'            -!! 3 tries @ {text}')
            return None

        prompt = 'Give a URL or other possible suggestion for: '
        reply = ai.prompt_for_json(pre + prompt + text, chatter=chatter)

        tries += 1

    url = reply['output']
    if not quiet: print(f'            --> {url}')
    return url


def get_screen_region(region_description, chatter=False):
    file, w, h = take_screenshot()

    prompt = 'Return a JSON map with the single key named "bounding_box" ' \
            + 'and value is the bounding box for the most likely clickable ' \
            + f'area for "{region_description}", or set bounding_box to JSON ' \
            + f'false if "{region_description}" cannot be found. The image ' \
            + 'is a full-screen screenshot so start at 0,0 on the top left ' \
            + 'and do not ignore upper menu bars or other blank regions. ' \
            + 'Be sure to return of the form { "bounding_box": ' \
            + '[y1,x1,y2,x2] } or { "bounding_box": false }'

    box = ai.prompt_with_file_for_json(file=file, prompt=prompt, retries=2,
                                       chatter=chatter)

    if not ('bounding_box' in box and box['bounding_box']):
        print(f'            !,!= {box} (coordinates)')
        return None

    box = box['bounding_box']
    y1,x1,y2,x2 = box
    #big = abs(x2-x1) > 25 or abs(y2-y1) > 25

    # gemini bounding box training assumes 1000x1000 image
    x1 = int(x1 * w / 1000)
    x2 = int(x2 * w / 1000)
    y1 = int(y1 * h / 1000)
    y2 = int(y2 * h / 1000)
    #print(f'#### {x1,y1}   {x2,y2}')

    '''
    if big:
        cw = x2 - x1
        ch = y2 - y1

        file = extract_and_save_region(file, x1, y1, cw, ch)

        prompt = 'Return a JSON map with the single key named "bounding_box" ' \
                + 'and value is the bounding box of the region that is most ' \
                + 'likely to be clickable, or set bounding_box to JSON false ' \
                + 'if that cannot be found. The image is from a portion of a ' \
                + 'web page. Be sure to return of the form { "bounding_box": ' \
                + '[y1,x1,y2,x2] } or { "bounding_box": false }'

        box = ai.prompt_with_file_for_json(file=file, prompt=prompt,
                                           chatter=chatter)

        if 'bounding_box' in box and box['bounding_box']:
            box = box['bounding_box']
            cy1,cx1,cy2,cx2 = box

            # gemini bounding box training assumes 1000x1000 image
            cx1 = int(cx1 * cw / 1000)
            cx2 = int(cx2 * cw / 1000)
            cy1 = int(cy1 * ch / 1000)
            cy2 = int(cy2 * ch / 1000)
            #print(f'##c# {cx1,cy1}   {cx2,cy2}')

            x2 = x1 + cx2
            x1 += cx1
            y2 = y1 + cy2
            y1 += cy1
    '''

    #print(f'##f# {x1,y1}   {x2,y2}')
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

    play_click()
    pyautogui.click()


class Actions(ActionsBase):
    def do_open(self, context, what_to_open, quiet=False, chatter=False):
        url = resolve_url(what_to_open, quiet=quiet)
        if not url: return None

        proc = open_browser(url)
        if not quiet: print(f'   # opened pid {proc.pid}')

        delay(10, quiet=quiet)
        file, w, h = take_screenshot()

        return FileResult(file)

    def do_click(self, context, what_to_click, quiet=False, chatter=False):
        region = get_screen_region(what_to_click, chatter=chatter)
        if not region: return None

        mouse_click_region(region)

        delay(7, quiet=quiet)
        file, w, h = take_screenshot()

        return FileResult(file)

    def do_type(self, context, text_to_type=None, text_from_ai=None,
                where_to_focus=None, quiet=False, chatter=False):
        if not (text_to_type or text_from_ai):
            print(' !! need text_to_type or text_from_ai !!')
            return None

        if text_to_type and text_from_ai:
            print(' !! cannot have both text_to_type and text_from_ai !!')
            return None

        if where_to_focus:
            region = get_screen_region(where_to_focus, chatter=chatter)
            if not region: return None

            mouse_click_region(region)

            delay(1, quiet=quiet)

        if text_from_ai:
            if where_to_focus:
                where_to_focus = 'in the area that is described by ' \
                                       f'"{where_to_focus}" '
            else:
                where_to_focus = ''

            prompt = f'Give me something to type in the web browser ' \
                     f'{where_to_focus}for this prompt: {text_to_type}'

            text_to_type = ai.prompt_for_text(prompt, chatter=chatter)

        if not quiet: print(f'    TYPING: {text_to_type}')
        play_typing()
        pyautogui.write(text_to_type, interval=0.2)

        delay(3, quiet=quiet)
        file, w, h = take_screenshot()

        return FileResult(file)

    def do_key(self, context, special_keys, quiet=False, chatter=False):
        for key in special_keys.split(' '):
            play_key()
            pyautogui.press(key)

            delay(1, quiet=quiet)

        delay(7, quiet=quiet)
        file, w, h = take_screenshot()

        return FileResult(file)


prompt_for_action = create_action_prompter(PRE_PROMPT, META_PROMPT, Actions)