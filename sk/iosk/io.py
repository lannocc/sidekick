# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from datetime import datetime, date
from os import makedirs
from os.path import join, isdir, exists
from io import StringIO


class Context:
    CID = 0 # next "chatter" id
    CHATTER = '/var/cache/chatter'

    STAGE_PRE = -1
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
        self.base = False # True if this is the root Context
        self.bot = False # True if this is a bot user
        self.session = StringIO() # the chat history
        self.sess_prompt = False # true if last session write() was prompt

        self.stage = self.STAGE_NORMAL
        self.pre = None
        self.post = None

    def fork(self):
        child = Context(self.os, self.dev, self.log)
        child.parent = self
        child.user = self.user
        child.bot = self.bot
        return child

    async def print(self, text, indicator='='):
        if self.log and self.stage == self.STAGE_NORMAL:
            self._log_(indicator)
            #self.log.write('<< ')

        await self.output(text)
        await self.output('\n')

    async def comment(self, text):
        if self.base and self.bot:
            self.session.write(text + '\n')

    async def input(self, prompt=None):
        if prompt and not self.bot:
            await self.os.send(self, self.dev, prompt)

        data = await self.os.recv(self, self.dev)

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
        if self.stage == self.STAGE_PRE:
            self.pre.write(text)
            return

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

    def stage_normal(self):
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

