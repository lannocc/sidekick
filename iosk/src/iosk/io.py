# src/iosk/io.py

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
        # Share the parent's aliases dictionary by reference so the 'alias' command can modify it.
        child.aliases = self.aliases

        # Share the parent's banks dictionary by reference.
        child.banks = self.banks

        # --- BEGIN FIX ---
        # Share the parent's command history by reference so that commands
        # like 'history' can see the list from the main user session.
        child.history = self.history
        
        # Share the new session history state so commands like 'forget' can modify it.
        child.session_history = self.session_history
        child.prompt_number = self.prompt_number
        child.rolling_config = self.rolling_config
        # --- END FIX ---

        return child