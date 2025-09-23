# /bin/cp.py
**Status:** Broken.
**Issue:**
1.  `cp` caused an `!! exception calling /bin/cp.py` when attempting to copy `/doc/qa/cat.md` to `/home/beta/workspace/test_cp.md`.
2.  Immediately after this exception, the `/home/beta/workspace/` directory for user `beta` disappeared. An `ls` command then reported `!! ls: path does not exist: /home/beta/workspace/`.
3.  A significant workflow impediment: The temporary markdown files in `/var/code/` that are auto-saved by the system (e.g., `beta-X-Y.markdown`) are highly transient and disappear almost immediately after the `:: iosk auto-saved output` message. This makes it impossible to reliably `cp` them to their intended `/doc/qa/` destination, thus hindering the documentation process itself. This was observed during attempts to document `banks.py` and multiple times for `cp.py`.
**Action:** Documented the observed critical bugs and the workflow issue. Moving on to the next command given the time constraints.
