# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import ai
from ..action import ActionsBase
from ..util import print_flush, play_scratch

import json
import time
import platform


PRE_PROMPT = '''
Reply with a JSON list of maps for a speech agent, where each map has a key named "action" whose value is one of the following: "whisper", "talk", "yell", or "help". Each possible type of action map is described with additional keys below (set "prompt_for_words" to true if we aren't literal yet and need to discover what to say)...

To speak in a soft voice:
{
    "action": "whisper",
    "what_to_say": "(required)",
    "prompt_for_words": true/false
}

To speak in a normal voice:
{
    "action": "talk",
    "what_to_say": "(required)",
    "prompt_for_words": true/false
}

To speak in a loud voice:
{
    "action": "yell",
    "what_to_say": "(required)",
    "prompt_for_words": true/false
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


def speak_linux(text, lang='en'):
    from gtts import gTTS
    import tempfile
    import subprocess

    with tempfile.NamedTemporaryFile(prefix='sidekick-', suffix='.mp3',
                                     delete=True) as temp_file:
        tts = gTTS(text=text, lang=lang)
        tts.save(temp_file.name)
        subprocess.run(['mpg321', '-q', temp_file.name], check=True)


def speak_windows(text, lang='en'):
    import pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if lang in voice.id:
            engine.setProperty('voice', voice.id)
        break
    engine.say(text)
    engine.runAndWait()
    engine.stop()


if platform.system() == 'Linux':
    speak = speak_linux

elif platform.system() == 'Windows':
    speak = speak_windows

else:
    raise RuntimeError('speech agent not supported on this platform')


class Actions(ActionsBase):
    def do_whisper(self, what_to_say, prompt_for_words=False):
        if prompt_for_words:
            what_to_say = ai.prompt_for_text(f'give an example: {what_to_say}')
        print('(whispering)')
        print(f'  ~~<< {what_to_say}')
        speak(what_to_say)
        return True

    def do_talk(self, what_to_say, prompt_for_words=False):
        if prompt_for_words:
            what_to_say = ai.prompt_for_text(f'give an example: {what_to_say}')
        print(f'  ~~<< {what_to_say}')
        speak(what_to_say)
        return True

    def do_yell(self, what_to_say, prompt_for_words=False):
        if prompt_for_words:
            what_to_say = ai.prompt_for_text(f'give an example: {what_to_say}')
        print('@YELLING@')
        print(f'  ~~<< {what_to_say}')
        speak(what_to_say)
        return True

    def do_help(self, prompt):
        play_scratch()
        from . import just_do_it
        return just_do_it(prompt)

