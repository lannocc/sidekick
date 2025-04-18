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

