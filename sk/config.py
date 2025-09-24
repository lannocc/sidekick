# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@
"""Global configuration options."""

from appdirs import AppDirs

from os import getenv, mkdir, makedirs
from os.path import join, exists
import logging


DIRS = AppDirs('SIDEKICK', 'LANNOCC')
if not exists(DIRS.user_data_dir): makedirs(DIRS.user_data_dir)


def get(name):
    name = join(DIRS.user_data_dir, name)
    if not exists(name): return None
    with open(name, 'r') as file:
        return file.read().strip()


_level = get('logging')
logging.basicConfig(
        level=getattr(logging, _level) if _level else logging.WARN,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


GEMINI_API_KEY = getenv('GEMINI_API_KEY')
#assert GEMINI_API_KEY

GEMINI_MODEL_QUICK_1 = 'gemini-2.0-flash'
GEMINI_MODEL_QUICK_2 = 'gemini-2.5-flash'
GEMINI_MODEL_SMART = 'gemini-2.5-pro'
GEMINI_TIMEOUT_HTTP = 7 * 60 * 1000 # wait up to 7 minutes (file uploads, etc.)

CHROME_PROFILE = 'Default'

TICKET_DB_HOST = get('ticket_db_host')
TICKET_DB_USER = get('ticket_db_user')
TICKET_DB_PASS = get('ticket_db_pass')

