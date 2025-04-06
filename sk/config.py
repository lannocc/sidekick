# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import os


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
assert GEMINI_API_KEY

GEMINI_MODEL = 'gemini-2.0-flash'
GEMINI_TIMEOUT = 60 # wait up to 60 seconds (file uploads, etc.)

CHROME_PROFILE = 'Default'

