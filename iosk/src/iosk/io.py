# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from datetime import datetime, date
from os import makedirs
from os.path import join, isdir, exists
from io import StringIO
import sys

try:
    import tiktoken
except ImportError:
    tiktoken = None


def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


class HistoryEntry:
    """Represents a discrete, numbered entry in the session history."""
    def __init__(self, number, content_str):
        self.number = number
        self.content = content_str
        self.byte_count = len(content_str.encode('utf-8'))
        self.line_count = content_str.count('\n')

        self.token_count = 0
        if tiktoken:
            try:
                # Use a global encoder instance if available for performance
                encoding = tiktoken.get_encoding('cl100k_base')
                self.token_count = len(encoding.encode(content_str))
            except Exception:
                # If encoding fails, token_count remains 0
                pass


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
        self.paused = False # True if the bot's engagement is paused
        self.login_time = None

        # --- History Proposal Implementation ---
        # self.session = StringIO() # REPLACED
        self.session_history = []
        self.prompt_number = 1
        self.rolling_config = {'enabled': False, 'mode': None, 'limit': 0}
        # --- End Implementation ---

        self.banks = { } # core memory
        self.env = {} # environment variables
        self.pwd = None # current working directory, virtual path (e.g., /home/user)
        self.aliases = {} # Aliases for the current user/session
        self.history = [] # Command history for the current session

        # Add color tracking
        self.user_colors = {} # How this user sees other users' colors
        self.color_idx = 0    # Index for assigning next default color

        self.caching_token_total = 0
        self.full_token_total = 0
        self.initial_static_tokens = 0

        self.stage = self.STAGE_NORMAL
        self.pre = None
        self.post = None
        self.banking = None
        self.preamble_cache = None

        # Added for token telemetry proposal
        self.token_stats = {
            'cumulative_input_tokens': 0, 'cumulative_input_bytes': 0,
            'cumulative_output_tokens': 0, 'cumulative_output_bytes': 0,
            'last_trip_input_tokens': 0, 'last_trip_input_bytes': 0,
            'last_trip_output_tokens': 0, 'last_trip_output_bytes': 0,
            'banked_tokens': 0, 'banked_bytes': 0,
            'history_tokens': 0, 'history_bytes': 0,
            'caching_context_tokens': 0, 'caching_context_bytes': 0
        }

        self.stdin = None
        self.stdout = None

    # --- History Proposal Methods ---

    def add_history_entry(self, content: str):
        """
        Creates a HistoryEntry, adds it to the session, increments the prompt
        number, updates token counts, and applies the rolling cutoff.
        This is the sole entry point for adding to the session history.
        """
        if not content:
            return

        entry = HistoryEntry(self.prompt_number, content)
        self.session_history.append(entry)
        self.prompt_number += 1

        # Incrementally update token stats for efficiency
        self.token_stats['history_tokens'] += entry.token_count
        self.token_stats['history_bytes'] += entry.byte_count
        # The caching context also grows by the same amount.
        self.token_stats['caching_context_tokens'] += entry.token_count
        self.token_stats['caching_context_bytes'] += entry.byte_count

        self._apply_rolling_cutoff()

    def _apply_rolling_cutoff(self):
        """Checks and applies the rolling history cutoff if configured."""
        if not self.rolling_config.get('enabled'):
            return

        mode = self.rolling_config.get('mode')
        limit = self.rolling_config.get('limit', 0)

        if not mode or limit <= 0:
            return

        # Determine the current total based on the configured mode
        if mode == 'tokens':
            current_total = sum(e.token_count for e in self.session_history)
        elif mode == 'bytes':
            current_total = sum(e.byte_count for e in self.session_history)
        elif mode == 'lines':
            current_total = sum(e.line_count for e in self.session_history)
        elif mode == 'prompts':
            current_total = len(self.session_history)
        else:
            return  # Invalid mode

        if current_total <= limit:
            return

        # Prune oldest entries until the total is within the limit
        removed_count = 0
        while current_total > limit and self.session_history:
            entry_to_remove = self.session_history[0]
            if mode == 'tokens':
                current_total -= entry_to_remove.token_count
            elif mode == 'bytes':
                current_total -= entry_to_remove.byte_count
            elif mode == 'lines':
                current_total -= entry_to_remove.line_count
            elif mode == 'prompts':
                current_total -= 1

            self.session_history.pop(0)
            removed_count += 1

        if removed_count > 0:
            # A modification occurred, so trigger a full, accurate recalculation.
            self.recalculate_token_stats()

    def get_session_string(self) -> str:
        """Concatenates all history entries into a single string for AI context."""
        return "".join([entry.content for entry in self.session_history])

    def recalculate_token_stats(self):
        """
        Performs a full recalculation of all token and byte counts for the
        user's context (preamble, banks, and history).
        """
        banking_content = ""
        if self.banks:
            for _, data in self.banks.items():
                banking_content += '\n' + data + '\n'

        preamble_content = self.preamble_cache or ""
        history_content = self.get_session_string()
        caching_context_content = preamble_content + banking_content + history_content

        # Calculate byte counts (always possible)
        self.token_stats['history_bytes'] = len(history_content.encode('utf-8'))
        self.token_stats['banked_bytes'] = len(banking_content.encode('utf-8'))
        self.token_stats['caching_context_bytes'] = len(caching_context_content.encode('utf-8'))

        # Calculate token counts (if tiktoken is available)
        if tiktoken:
            try:
                encoding = tiktoken.get_encoding('cl100k_base')
                self.token_stats['history_tokens'] = len(encoding.encode(history_content))
                self.token_stats['banked_tokens'] = len(encoding.encode(banking_content))
                self.token_stats['caching_context_tokens'] = len(encoding.encode(caching_context_content))
            except Exception:
                # On failure, reset token counts to 0
                self.token_stats['history_tokens'] = 0
                self.token_stats['banked_tokens'] = 0
                self.token_stats['caching_context_tokens'] = 0
        else:
            self.token_stats['history_tokens'] = 0
            self.token_stats['banked_tokens'] = 0
            self.token_stats['caching_context_tokens'] = 0

    # --- End History Proposal Methods ---

    def fork(self):
        child = Context(self.os, self.dev, self.log)
        child.parent = self

        child.user = self.user
        child.bot = self.bot
        child.paused = self.paused
        child.login_time = self.login_time
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

        # --- BEGIN FIX ---
        # Share the parent's command history by reference so that commands
        # like 'history' can see the list from the main user session.
        child.history = self.history
        # --- END FIX ---

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
            # Comments for bots are now added as history entries.
            self.add_history_entry(text + '\n')


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

            # REMOVED: Writing to session buffer is now handled by command execution logic.
            # if self.base and self.bot:
            #     if prompt: self.session.write(prompt)
            #     self.session.write(data)
            #     self.session.write('\n')
            #     self.session.flush()

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

        # REMOVED: Writing to session buffer is now handled by higher-level logic.
        # if self.base and self.bot:
        #     self.session.write(text)
        #     self.session.flush()

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
        if i == 'I':
            self.log.write(f'=== {now} [{self.os.BOOT}/{self.cid}/{self.prompt_number}] ={i}= ')
        else:
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