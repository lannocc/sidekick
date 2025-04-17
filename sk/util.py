# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import CHROME_PROFILE

from sys import stdout
import os
import subprocess
import platform


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

