# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from datetime import datetime, date
from os import makedirs
from os.path import join, isdir, exists
from io import StringIO
import sys


def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


class Context:
    CID = 0 # next "chatter" id
    CHATTER = '/var/cache/chatter'
    CODE = '/var/code'

    STAGE_PRE = -2
    STAGE_BANK = -1
    STAGE_NORMAL = 0
    STAGE_POST = 1

    def __init__(self, iosk_unix, dev_path, log_file=None):
        self.cid = Context.CID
        Context.CID += 1

        self.os = iosk_unix # running system
        self.dev = dev_path # device name path
        self.log = log_file # opened file handle
        self.parent = None  # parent Context

        chatter = join(self.CHATTER, str(self.os.BOOT), str(self.cid))
        self.chatter = open(self.os.box(chatter), 'w')

        self.user = None
        self.su = False # superuser privileges?
        self.base = False # True if this is the root Context
        self.bot = False # True if this is a bot user
        self.session = StringIO() # the chat history
        self.banks = { } # core memory
        self.env = {} # environment variables
        self.pwd = None # current working directory, virtual path (e.g., /home/user)
        self.aliases = {} # Aliases for the current user/session
        self.history = [] # Command history for the current session

        self.caching_token_total = 0
        self.full_token_total = 0
        self.initial_static_tokens = 0

        self.stage = self.STAGE_NORMAL
        self.pre = None
        self.post = None
        self.banking = None
        self.preamble_cache = None

        self.stdin = None
        self.stdout = None

    def fork(self):
        child = Context(self.os, self.dev, self.log)
        child.parent = self

        child.user = self.user
        child.bot = self.bot
        child.preamble_cache = self.preamble_cache

        # Inherit I/O streams from parent by default
        child.stdin = self.stdin
        child.stdout = self.stdout

        # Inherit environmental properties from the parent context.
        # This is crucial for commands in pipelines to know the CWD.
        child.pwd = self.pwd
        # Use a copy so child modifications don't affect the parent.
        child.env = self.env.copy()
        child.aliases = self.aliases.copy()

        # Share the parent's banks dictionary by reference.
        child.banks = self.banks

        return child

    def environ(self):
        """
        Retrieves the complete environment for this context.
        It traverses up the parent chain, merging environment dictionaries,
        with child values overriding parent values.
        """
        # Build the hierarchy from root to current context
        hierarchy = []
        ctx = self
        while ctx:
            hierarchy.insert(0, ctx)
            ctx = ctx.parent

        # Merge environments, parents first, so children override
        full_env = {}
        for ctx_in_chain in hierarchy:
            full_env.update(ctx_in_chain.env)

        return full_env

    async def print(self, text, indicator='='):
        if self.log and self.stage == self.STAGE_NORMAL and not self.stdout:
            self._log_(indicator)
            #self.log.write('<< ')

        await self.output(text)
        await self.output('\n')

    async def comment(self, text):
        if self.base and self.bot:
            self.session.write(text + '\n')


    async def input(self, prompt=None):
        #if prompt and not self.bot:
        #    await self.os.send(self, self.dev, prompt)

        data = await self.os.recv(self, self.dev, prompt=prompt)

        if data:
            if self.log:
                self._log_('I') # log timestamped when input received
                #if prompt: self.log.write(prompt)
                self.log.write(data)
                self.log.write('\n')
                self.log.flush()

            if self.base and self.bot:
                if prompt: self.session.write(prompt)
                self.session.write(data)
                self.session.write('\n')
                self.session.flush()

        return data

    async def output(self, text):
        if text is None: return

        if self.stdout:
            # If stdout is a custom stream (file, StringIO), write to it.
            # This bypasses the normal async output to the device.
            self.stdout.write(text)
            return

        if self.stage == self.STAGE_PRE:
            self.pre.write(text)
            return

        elif self.stage == self.STAGE_BANK:
            self.banking[1].write(text)
            if self.bot: return

        elif self.stage == self.STAGE_POST:
            self.post.write(text)
            return

        self.chatter.write(text)

        if self.log:
            if text == '\n':
                ltext = text
            else:
                s = (len(f'{self.os.BOOT}/{self.cid}') - 3) * ' '
                ltext = text.replace('\n',
                                     f'\n===    ...       ...    [...{s}] =.= ')
            self.log.write(ltext)
            self.log.flush()

        if self.base and self.bot:
            self.session.write(text)
            self.session.flush()

        await self.os.send(self, self.dev, text)

    async def error(self, args):
        await self.print(args, indicator='E')

    def stage_pre(self):
        self.pre = StringIO()
        self.stage = self.STAGE_PRE

    def stage_bank(self, key):
        self.banking = (key, StringIO())
        self.stage = self.STAGE_BANK

    def stage_normal(self):
        if self.banking:
            key = self.banking[0]
            sio = self.banking[1]
            sio.seek(0)
            data = sio.read()
            self.banking = None
            self.banks[key] = data

        self.stage = self.STAGE_NORMAL

    def stage_post(self):
        self.post = StringIO()
        self.stage = self.STAGE_POST

    def _log_(self, indicator='='):
        assert len(indicator) == 1
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        i = indicator
        self.log.write(f'=== {now} [{self.os.BOOT}/{self.cid}] ={i}= ')


class Capture:
    logs = { } # opened file handles keyed by path

    @classmethod
    def log(cls, iosk, path, mkdirs=False):
        if mkdirs:
            folder = iosk.box(path)
            if not exists(folder):
                makedirs(folder)

            elif not isdir(folder):
                raise ValueError(f'path exists but not a folder: {folder}')

        today = date.today().strftime('%Y-%m-%d')
        file_path = iosk.box(join(path, f'{today}.log'))

        if file_path in cls.logs:
            return cls.logs[file_path]

        else:
            file = open(file_path, 'a')
            cls.logs[file_path] = file
            return file

