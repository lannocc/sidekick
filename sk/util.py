# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import CHROME_PROFILE

from PIL import ImageGrab
from playsound3 import playsound
#import simpleaudio as sa

from sys import stdout
import os
import subprocess
import platform
import tempfile
#import time


def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    stdout.flush()


def open_browser(url):
    if platform.system() == 'Windows':
        chrome_path_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(
                r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]

        chrome_path = None
        for path in chrome_path_candidates:
            if os.path.exists(path):
                chrome_path = path
                break

    else:
        chrome_path = 'google-chrome'

    if not chrome_path:
        raise RuntimeError('Could not find Google Chrome')

    proc = subprocess.Popen([chrome_path,
                             f'--profile-directory={CHROME_PROFILE}',
                             '--start-fullscreen', '--new-window', url],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True)

    return proc


def take_screenshot():
    fd, file = tempfile.mkstemp(prefix='sidekick-shot-', suffix='.png')
    shot = ImageGrab.grab()
    play_shot()
    w,h = shot.size
    shot.save(file)
    shot.close()

    return file, w, h


def is_ignorable_path(item):
    return True \
            if item.startswith('.') \
            or item == 'build' or item == 'venv' or item == 'scripts' \
            or item == 'node_modules' \
            or item.endswith('.egg-info') or item.endswith('~') else False


def get_directory_tree_as_text(path, indent=''):
    text = ''
    items = os.listdir(path)

    for i, item in enumerate(sorted(items)):
        if is_ignorable_path(item):
            continue

        full_path = os.path.join(path, item)

        if i < len(items) - 1: # not last item
            prefix = "├── "
            new_indent = indent + "│   "

        else: # last item in list
            prefix = "└── "
            new_indent = indent + "    "

        suffix = ''
        if os.path.isdir(full_path):
            suffix = os.sep

        text += indent + prefix + item + suffix + '\n'

        if os.path.isdir(full_path):
            text += get_directory_tree_as_text(full_path, new_indent)

    return text


def get_directory_contents_as_text(path):
    text = ''
    items = os.listdir(path)

    for i, item in enumerate(sorted(items)):
        if is_ignorable_path(item):
            continue

        full_path = os.path.join(path, item)

        if os.path.isdir(full_path):
            text += get_directory_contents_as_text(full_path)

        else:
            hint = 'python' if item.endswith('.py') else \
                   'svelte' if item.endswith('.svelte') else \
                   'markdown' if item.endswith('.md') else \
                   'html' if item.endswith('.html') else \
                   'css' if item.endswith('.css') else \
                   'javascript' if item.endswith('.js') else \
                   'json' if item.endswith('.json') else \
                   'text' if item.endswith('.txt') else None

            if not hint: # not a text file
                continue

            text += f'\nFILE {full_path}:\n'
            text += f'```{hint}\n'
            with open(full_path, 'r') as file:
                text += file.read()
                #text += '\n'
            text += '```\n\n'

    return text


def package_directory(path, label='project'):
    fd, name = tempfile.mkstemp(prefix='sidekick-package-', suffix='.txt')

    with open(name, 'w', encoding='utf-8') as file:
        file.write(f'Our {label} is laid out as given in the following file '
                    'hierarchy:\n\n')
        file.write(f'{path}{os.sep}\n')
        file.write(get_directory_tree_as_text(path))
        file.write('\n\n')
        file.write('The contents of each file are given in succession below...'
                   '\n\n')
        file.write(get_directory_contents_as_text(path))

    return name


def play(file_path):
    '''
    system = platform.system()

    if system == 'Windows':
        import winsound
        winsound.PlaySound(file_path, winsound.SND_FILENAME)
        return

    elif system == 'Darwin':
        r = os.system(f'aplay "{file_path}"')

    elif system == 'Linux':
        try: r = os.system(f'aplay "{file_path}"')
        except: r = os.system(f'xdg-open "{file_path}"')

    if r != 0:
        raise RuntimeError(f'failed to play sound: {file_path}')
    '''

    playsound(file_path)

    #wave = sa.WaveObject.from_wave_file(file_path)
    #play = wave.play()
    #play.wait_done()


def play_error():
    #play('assets/beep.wav')
    #play('assets/beep1.wav')
    play('assets/beep2.wav')
    play('assets/beep2.wav')
    play('assets/beep2.wav')


def play_retry():
    play('assets/short_beep.wav')


def play_success():
    play('assets/good_bell.wav')


def play_shot():
    play('assets/shutter.wav')


def play_ding():
    play('assets/ding.wav')


def play_click():
    play('assets/mouse_click.wav')


def play_key():
    play('assets/key.wav')


def play_typing():
    play('assets/keys.wav')


def play_scratch():
    play('assets/scratch.wav')


def play_thinking():
    play('assets/three_tones.wav')

