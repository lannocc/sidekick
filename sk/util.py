# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import CHROME_PROFILE

from sys import stdout
import os
import subprocess
import platform
import tempfile
import time
import re


CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w*?)\n(?P<code>.*?)\n```',
                             re.DOTALL)

BYTES_SEPARATOR = '\n____________/=='


def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    stdout.flush()


def delay(sec, quiet=False):
    if not quiet: print_flush(f'{sec}(s) delay', end='')
    for i in range(sec):
        if not quiet: print_flush('.', end='')
        time.sleep(1)
    if not quiet: print()


def open_browser(url):
    if platform.system() == 'Windows':
        chrome_path_candidates = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expanduser(
                r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
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
    from PIL import ImageGrab

    fd, file = tempfile.mkstemp(prefix='sidekick-shot-', suffix='.png')
    shot = ImageGrab.grab()
    play_shot()
    w,h = shot.size
    shot.save(file)
    shot.close()

    return file, w, h


'''
def extract_and_save_region(file, x, y, w, h):
    img = cv2.imread(file)
    if img is None:
        raise FileNotFoundError(f"Image not found at '{file}'")

    ext = file.split('.')[-1]
    fd, name = tempfile.mkstemp(prefix='sidekick-region-', suffix=f'.{ext}')
    roi = img[y:y+h, x:x+w]
    cv2.imwrite(name, roi)

    return name
'''


def get_ignore_set(path):
    name = os.path.join(path, '.skignore')

    if os.path.isfile(name):
        with open(name, 'r') as file:
            ignore = file.readlines()
        ignore = [ line[:-1] for line in ignore ]
    else:
        ignore = [ ]

    return set(ignore)


def is_ignorable_path(item, ignores=[ ]):
    return item.startswith('.') \
                or item.endswith('~') \
                or item == '__pycache__' \
                or item in ignores


def get_directory_tree_as_text(path, indent='', markdown=False, count=False):
    import tiktoken

    text = ''
    items = os.listdir(path)
    ignores = get_ignore_set(path)

    for i, item in enumerate(sorted(items)):
        if is_ignorable_path(item, ignores):
            continue

        full_path = os.path.join(path, item)

        if i < len(items) - 1: # not last item
            prefix = '* ' if markdown else '├── '
            new_indent = indent + ('    ' if markdown else '│   ')

        else: # last item in list
            prefix = '* ' if markdown else '└── '
            new_indent = indent + '    '

        suffix = ''
        if os.path.isdir(full_path):
            suffix = os.sep

        elif markdown:
            item = f'[{item}]({full_path})'

        text += indent + prefix + item + suffix + '\n'

        if os.path.isdir(full_path):
            text += get_directory_tree_as_text(full_path, new_indent,
                                               markdown=markdown)

    if count:
        data = text + get_directory_contents_as_text(path)
        data_bytes = data.encode('utf-8')

        text +=  BYTES_SEPARATOR
        text += f'\nTotal Bytes: {len(data_bytes):,}'
        tokens = tiktoken.get_encoding('cl100k_base').encode(data)
        text += f'\nEst. Tokens: {len(tokens):,}'

    return text


def get_directory_contents_as_text(path):
    from binaryornot.check import is_binary

    text = ''
    items = os.listdir(path)
    ignores = get_ignore_set(path)

    for i, item in enumerate(sorted(items)):
        if is_ignorable_path(item, ignores):
            continue

        full_path = os.path.join(path, item)

        if os.path.isdir(full_path):
            text += get_directory_contents_as_text(full_path)

        else:
            hint = 'python' if item.endswith('.py') else \
                   'svelte' if item.endswith('.svelte') else \
                   'markdown' if item.endswith('.md') else \
                   'rst' if item.endswith('.rst') else \
                   'html' if item.endswith('.html') else \
                   'css' if item.endswith('.css') else \
                   'javascript' if item.endswith('.js') else \
                   'json' if item.endswith('.json') else \
                   'config' if item.endswith('.conf') \
                        or item.endswith('.theme') else \
                   'bat' if item.endswith('.bat') else \
                   'shell' if item.endswith('.sh') else \
                   'bash' if item.endswith('.bash') else \
                   'text' if item.endswith('.txt') else None

            if not hint:
                if is_binary(full_path): continue # not text
                else: hint = ''

            text += f'\n>>> BEGIN FILE {full_path}:\n'
            text += f'```{hint}\n'
            with open(full_path, 'r') as file:
                text += file.read()
                #text += '\n'
            text += '```\n'
            text += '<<< END FILE\n\n'

    return text


def package_directory(path, label='project'):
    fd, name = tempfile.mkstemp(prefix='sidekick-package-', suffix='.txt')

    with open(name, 'w', encoding='utf-8') as file:
        file.write(f'Our {label} is laid out as given in the following file '
                    'hierarchy:\n\n')
        file.write(f'{path}{os.sep}\n')

        tree = get_directory_tree_as_text(path, count=True)
        sep = tree.index(BYTES_SEPARATOR)
        counts = tree[sep+len(BYTES_SEPARATOR):]
        tree = tree[:sep]

        file.write(tree)
        file.write('\n\n')
        file.write('The contents of each file are given in succession below...'
                   '\n\n')
        file.write(get_directory_contents_as_text(path))

    return name, counts


def get_md_code_block(language, text):
    matches = CODEBLOCK_REGEX.finditer(text)

    for match in matches:
        lang = match.group('language')
        if language is not None and lang != language: continue

        code = match.group('code')
        return code


def play(file_path):
    from playsound3 import playsound

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

