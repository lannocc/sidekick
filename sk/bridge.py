# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import asyncio
import json
import os
import logging
import platform
import sys
import tiktoken
import sqlite3
import subprocess
import signal
from datetime import datetime
from . import config
from .util import get_directory_tree_as_text, get_directory_contents_as_text
from binaryornot.check import is_binary
import base64

# pty is not available on Windows
if platform.system() != 'Windows':
    import pty
    import fcntl
    import struct
    import termios
else:
    pty = None # Make it explicit

from websockets.server import serve
from websockets.exceptions import ConnectionClosed

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# --- Stylized Console Output ---

# ANSI color codes for stylized console output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[36m'
    YELLOW = '\033[33m'
    MAGENTA = '\033[35m'
    GREEN = '\033[32m'
    RED = '\033[31m'

def print_action(action, details=""):
    """Prints a formatted and stylized action line to the console."""
    if not sys.stdout.isatty(): # Don't use colors if not a TTY
        print(f"[SK-LOCAL] {action}: {details}")
        return

    timestamp = datetime.now().strftime('%H:%M:%S')
    # Using f-string for clear, colored output.
    print(f"{Colors.CYAN}[SK-LOCAL {timestamp}]{Colors.RESET} {Colors.BOLD}{Colors.MAGENTA}{action.ljust(14)}{Colors.RESET} {Colors.YELLOW}{details}{Colors.RESET}")

def print_startup_banner():
    """Prints a colorful startup banner."""
    if not sys.stdout.isatty():
        log.info(f"Starting SKYBRIDGE Local Server on ws://{HOST}:{PORT}")
        return
    print(f"\n{Colors.BOLD}{Colors.GREEN}--- SKYBRIDGE Local Server ---{Colors.RESET}")
    print(f"{Colors.CYAN}  Listening on: ws://{HOST}:{PORT}{Colors.RESET}")
    print(f"{Colors.YELLOW}  Press Ctrl+C to stop the server.{Colors.RESET}\n")

def print_shutdown_message():
    """Prints a colorful shutdown message."""
    if not sys.stdout.isatty():
        log.info("Server shutting down.")
        return
    print(f"\n{Colors.BOLD}{Colors.YELLOW}Shutting down server...{Colors.RESET}")

def print_stopped_message():
    """Prints a colorful server stopped message."""
    if not sys.stdout.isatty():
        log.info("Server stopped.")
        return
    print(f"{Colors.BOLD}{Colors.RED}Server stopped.{Colors.RESET}")

# --- End Stylized Console Output ---


PORT = 4210
HOST = '127.0.0.1'

ENCODING = tiktoken.get_encoding('cl100k_base')
running_asks = {}
WATCHERS = {} # path -> {'clients': set(), 'task': asyncio.Task, 'state': dict}
TAILERS = {}   # path -> {'clients': set(), 'task': asyncio.Task}


# --- SKYBRIDGE Globals ---
DB_CONN = None
CONNECTED_CLIENTS = set()
RUNNING_PROCESSES = {} # pid -> { 'process': Process, 'monitor_task': Task, ... }
# --------------------

def get_resolved_settings_sync(box_id, cursor):
    """
    Fetches the fully resolved settings for a box by traversing its parent chain.
    Settings from children override settings from parents.
    """
    box_ids_to_check = []
    current_id = box_id
    
    # Build the chain of inheritance from child up to the root (box 0)
    # Use a set to prevent infinite loops on malformed data, though FKs should prevent this.
    seen_ids = set()
    while current_id is not None and current_id not in seen_ids:
        box_ids_to_check.append(current_id)
        seen_ids.add(current_id)
        if current_id == 0:
            break
        cursor.execute("SELECT parent_box_id FROM box WHERE id = ?", (current_id,))
        row = cursor.fetchone()
        current_id = row['parent_box_id'] if row else None
        
    resolved_settings = {}
    
    # Iterate from the root down to the child, merging settings.
    for current_box_id in reversed(box_ids_to_check):
        # Get theme config
        cursor.execute("SELECT theme FROM config WHERE box_id = ?", (current_box_id,))
        theme_row = cursor.fetchone()
        theme_settings = json.loads(theme_row['theme']) if theme_row and theme_row['theme'] else {}
        
        # Get view settings
        cursor.execute("SELECT key, value FROM settings WHERE box_id = ?", (current_box_id,))
        view_settings = {}
        for row in cursor.fetchall():
            try:
                view_settings[row['key']] = json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                view_settings[row['key']] = row['value']
        
        # Merge theme and view for the current level
        current_level_settings = {**theme_settings, **view_settings}
        
        # Update the resolved settings. Keys in current_level_settings will
        # overwrite keys from parent levels.
        resolved_settings.update(current_level_settings)
        
    return resolved_settings

def _get_boxes_with_settings_info(cursor):
    """Helper to fetch all boxes and annotate them with settings status."""
    cursor.execute("SELECT id, name, type, context, x, y, scale, cover_panel_location, aspect_ratio, parent_box_id FROM box ORDER BY name")
    boxes_data = [dict(row) for row in cursor.fetchall()]
    boxes_with_settings_info = []
    for box in boxes_data:
        box_id = box['id']
        if box_id == 0:
            # The main desktop has custom settings if its theme config is not the default empty object.
            # We ignore view settings for this check as they are always present and represent user state.
            cursor.execute("SELECT theme FROM config WHERE box_id = 0")
            config_row = cursor.fetchone()
            box['has_custom_settings'] = config_row is not None and config_row['theme'] != '{}'
        else:
            # A box has custom settings if it has any entry in 'config' or 'settings' tables.
            cursor.execute("SELECT 1 FROM config WHERE box_id = ?", (box_id,))
            has_theme = cursor.fetchone() is not None
            cursor.execute("SELECT 1 FROM settings WHERE box_id = ?", (box_id,))
            has_view = cursor.fetchone() is not None
            box['has_custom_settings'] = has_theme or has_view
        boxes_with_settings_info.append(box)
    return boxes_with_settings_info

def init_db():
    """Initializes the SQLite database for SKYBRIDGE."""
    global DB_CONN
    db_path = os.path.join(config.DIRS.user_data_dir, 'skybridge.db')
    log.info(f"Using SKYBRIDGE database at {db_path}")
    DB_CONN = sqlite3.connect(db_path)
    DB_CONN.row_factory = sqlite3.Row  # Makes rows dict-like
    DB_CONN.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
    cursor = DB_CONN.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS box (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('local', 'iosk')),
            context TEXT NOT NULL,
            parent_box_id INTEGER,
            x INTEGER DEFAULT 100,
            y INTEGER DEFAULT 100,
            scale REAL DEFAULT 1.0,
            cover_panel_location TEXT,
            aspect_ratio REAL,
            FOREIGN KEY(parent_box_id) REFERENCES box(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS panel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            loc_x INTEGER NOT NULL,
            loc_y INTEGER NOT NULL,
            parent_loc_x INTEGER,
            parent_loc_y INTEGER,
            board_type TEXT NOT NULL CHECK(board_type IN ('empty', 'window', 'tabs', 'dash', 'image')),
            board_config TEXT, -- JSON blob for the BOARD configuration
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE,
            UNIQUE(box_id, loc_x, loc_y)
        );
    """)

    # Schema for settings table (pan/zoom, etc.) - key/value store
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            box_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (box_id, key),
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE
        );
    """)

    # New schema for config table (theming, etc.) - single JSON blob
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            box_id INTEGER PRIMARY KEY,
            theme TEXT NOT NULL,
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shortcut (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('file', 'dir')),
            path TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            scale REAL NOT NULL DEFAULT 1.0,
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE,
            UNIQUE(box_id, path)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            config TEXT NOT NULL, -- JSON blob of window group
            x REAL NOT NULL,
            y REAL NOT NULL,
            width REAL NOT NULL,
            height REAL NOT NULL,
            scale REAL NOT NULL DEFAULT 1.0,
            z_index INTEGER NOT NULL DEFAULT 0,
            original_group_id INTEGER,
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE
        );
    """)

    # New tables for ProcBox
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS iosk (
            box_id INTEGER PRIMARY KEY,
            mount_point TEXT,
            daemon_mode INTEGER NOT NULL DEFAULT 1,
            enable_stdin INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS process (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER,
            pid INTEGER NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'iosk',
            start_time TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('running', 'paused', 'stopped', 'error')),
            stdout_log_path TEXT NOT NULL,
            stderr_log_path TEXT NOT NULL,
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE SET NULL
        );
    """)


    # For new databases, create the default 'Main Desktop' box with id=0.
    # This is required for foreign key constraints and default settings.
    cursor.execute("INSERT OR IGNORE INTO box (id, name, type, context) VALUES (?, ?, ?, ?)",
                   (0, 'Main Desktop', 'local', '.'))

    # Set default values for the main desktop (box_id=0) if they don't exist
    default_settings = {'panX': 0, 'panY': 0, 'zoom': 1.0, 'windowPanX': 0, 'windowPanY': 0, 'windowZoom': 1.0}
    for key, value in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (box_id, key, value) VALUES (?, ?, ?)", (0, key, json.dumps(value)))

    DB_CONN.commit()
    log.info("SKYBRIDGE database initialized.")


async def broadcast_box_list():
    """Fetches all boxes and broadcasts them to all connected clients."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast box list.")
        return

    cursor = DB_CONN.cursor()
    boxes = _get_boxes_with_settings_info(cursor)
    message = json.dumps({'type': 'box_list', 'boxes': boxes})

    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting box_list to {len(CONNECTED_CLIENTS)} clients.")
        # Concurrently send the message to all clients.
        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])


async def broadcast_shortcut_list(box_id):
    """Fetches all shortcuts for a given box and broadcasts them."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast shortcut list.")
        return
    cursor = DB_CONN.cursor()
    cursor.execute("SELECT id, name, type, path, x, y, scale FROM shortcut WHERE box_id = ?", (box_id,))
    shortcuts = [dict(row) for row in cursor.fetchall()]
    message = json.dumps({'type': 'shortcut_list', 'shortcuts': shortcuts, 'box_id': box_id})
    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting shortcut_list for box {box_id} to {len(CONNECTED_CLIENTS)} clients.")
        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])

async def broadcast_backed_window_list(box_id):
    """Fetches all backed windows for a given box and broadcasts them."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast backed window list.")
        return
    cursor = DB_CONN.cursor()
    cursor.execute("SELECT id, config, x, y, width, height, scale, z_index, original_group_id FROM board WHERE box_id = ?", (box_id,))
    windows = [dict(row) for row in cursor.fetchall()]
    message = json.dumps({'type': 'backed_window_list', 'windows': windows, 'box_id': box_id})
    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting backed_window_list for box {box_id} to {len(CONNECTED_CLIENTS)} clients.")
        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])


async def broadcast_box_config(box_id):
    """Fetches the panel config for a box and broadcasts it to all clients."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast box config.")
        return

    cursor = DB_CONN.cursor()
    cursor.execute("SELECT id, box_id, loc_x, loc_y, parent_loc_x, parent_loc_y, board_type, board_config FROM panel WHERE box_id = ?", (box_id,))
    panels = []
    for row in cursor.fetchall():
        panel = dict(row)
        try:
            if panel['board_config']:
                panel['board_config'] = json.loads(panel['board_config'])
        except json.JSONDecodeError:
            log.warning(f"Could not decode board_config for panel at ({panel['loc_x']},{panel['loc_y']}) in box {box_id}")
            panel['board_config'] = None
        panels.append(panel)

    message = json.dumps({'type': 'box_config_response', 'box_id': box_id, 'panels': panels})

    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting box_config for box {box_id} to {len(CONNECTED_CLIENTS)} clients.")
        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])



async def broadcast_settings(box_id):
    """Fetches resolved settings for a given box and broadcasts them."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast desktop settings.")
        return

    cursor = DB_CONN.cursor()
    settings = get_resolved_settings_sync(box_id, cursor)
    
    message = json.dumps({'type': 'desktop_settings', 'settings': settings, 'box_id': box_id})

    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting desktop_settings for box {box_id} to {len(CONNECTED_CLIENTS)} clients.")
        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])


async def read_stream(stream, websocket, ask_id, stream_name):
    """Read from a subprocess stream and forward to websocket."""
    while not stream.at_eof():
        line = await stream.readline()
        if line:
            await websocket.send(json.dumps({
                'type': 'ask_output',
                'askId': ask_id,
                'stream': stream_name,
                'data': line.decode('utf-8', errors='ignore')
            }))


async def handle_sk_ask(websocket, msg):
    """Handles the sk_ask request to run the 'ask' command."""
    ask_id = msg.get('askId')
    if not ask_id:
        log.error("sk_ask message missing askId")
        return

    # Find the path to the 'ask' executable. Assumes it's in the same
    # directory as the script running this server (e.g., venv/bin).
    sk_dir = os.path.dirname(sys.executable)
    ask_executable = os.path.join(sk_dir, 'ask')
    if platform.system() == 'Windows' and not os.path.exists(ask_executable):
        ask_executable += '.exe'

    if not os.path.exists(ask_executable):
        log.warning(f"'ask' not found at {ask_executable}, trying PATH.")
        ask_executable = 'ask'

    try:
        cmd = [ask_executable]
        options = msg.get('options', {})
        if options.get('use_openai'): cmd.append('--openai')
        if options.get('work'): cmd.append('-w')
        if options.get('screenshot'): cmd.append('-s')
        if options.get('model'): cmd.append(options['model'])

        for f in msg.get('files', []):
            abs_path = os.path.abspath(f)
            if os.path.exists(abs_path):
                cmd.append(abs_path)
            else:
                log.warning(f"File not found for 'ask', skipping: {abs_path}")

        log.info(f"Executing ask command for {ask_id}: {cmd}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        running_asks[ask_id] = process

        prompt_text = msg.get('prompt', '')
        if prompt_text:
            process.stdin.write(prompt_text.encode('utf-8'))
        await process.stdin.drain()
        process.stdin.close()

        await asyncio.gather(
            read_stream(process.stdout, websocket, ask_id, 'stdout'),
            read_stream(process.stderr, websocket, ask_id, 'stderr')
        )

        exit_code = await process.wait()
        await websocket.send(json.dumps({
            'type': 'ask_exit', 'askId': ask_id, 'code': exit_code
        }))

    except Exception as e:
        log.error(f"Error executing 'ask' for {ask_id}: {e}", exc_info=True)
        if websocket.open:
            await websocket.send(json.dumps({
                'type': 'ask_error', 'askId': ask_id, 'data': str(e)
            }))
    finally:
        if ask_id in running_asks:
            del running_asks[ask_id]


async def handle_fs_list(path, recursive=False, requester_id=None):
    """Handles the fs_list request."""
    try:
        abs_path = os.path.abspath(path)

        if not os.path.isdir(abs_path):
            response = {'type': 'fs_error', 'path': path, 'error': 'Not a directory or does not exist'}
            if requester_id is not None:
                response['requester_id'] = requester_id
            return response

        entries = []
        if recursive:
            for root, dirs, files in os.walk(abs_path, topdown=True):
                for name in sorted(dirs):
                    try:
                        full_path = os.path.join(root, name)
                        stat = os.stat(full_path)
                        entries.append({
                            'name': name,
                            'path': full_path.replace(os.sep, '/'),
                            'type': 'dir',
                            'size': stat.st_size,
                            'mtime': stat.st_mtime
                        })
                    except OSError:
                        continue
                for name in sorted(files):
                    try:
                        full_path = os.path.join(root, name)
                        stat = os.stat(full_path)
                        entries.append({
                            'name': name,
                            'path': full_path.replace(os.sep, '/'),
                            'type': 'file',
                            'size': stat.st_size,
                            'mtime': stat.st_mtime
                        })
                    except OSError:
                        continue
        else:
            for name in sorted(os.listdir(abs_path)):
                try:
                    full_path = os.path.join(abs_path, name)
                    stat = os.stat(full_path)
                    entry_type = 'dir' if os.path.isdir(full_path) else 'file'
                    entries.append({
                        'name': name,
                        'path': full_path.replace(os.sep, '/'),
                        'type': entry_type,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    })
                except OSError:
                    continue
        
        # Return the normalized absolute path, as the frontend uses this
        # for tree building and navigation state.
        norm_path = abs_path.replace(os.sep, '/')
        response = {'type': 'fs_list_response', 'path': norm_path, 'entries': entries}
        if requester_id is not None:
            response['requester_id'] = requester_id
        return response
    except Exception as e:
        log.error(f"Error listing path {path}: {e}")
        response = {'type': 'fs_error', 'path': path, 'error': str(e)}
        if requester_id is not None:
            response['requester_id'] = requester_id
        return response


async def handle_fs_read(path, offset=0, length=-1, requester_id=None):
    """Handles the fs_read request, supporting binary files and chunking."""
    response = {'type': 'fs_read_response', 'path': path}
    if requester_id is not None:
        response['requester_id'] = requester_id
    
    try:
        abs_path = os.path.abspath(path)

        if not os.path.isfile(abs_path):
            response['type'] = 'fs_error'
            response['error'] = 'Not a file or does not exist'
            return response

        total_size = os.path.getsize(abs_path)
        is_bin = is_binary(abs_path)
        
        with open(abs_path, 'rb') as f:
            f.seek(offset)
            if length == -1:
                content_bytes = f.read()
            else:
                content_bytes = f.read(length)

        response.update({
            'content_b64': base64.b64encode(content_bytes).decode('utf-8'),
            'is_binary': is_bin,
            'total_size': total_size,
            'offset': offset,
            'length': len(content_bytes) if length != -1 else -1,
        })
        return response
    except Exception as e:
        log.error(f"Error reading path {path}: {e}")
        response['type'] = 'fs_error'
        response['error'] = str(e)
        return response


def _get_formatted_file_content(full_path):
    item = os.path.basename(full_path)
    hint = 'python' if item.endswith('.py') else \
           'svelte' if item.endswith('.svelte') else \
           'markdown' if item.endswith('.md') else \
           'rst' if item.endswith('.rst') else \
           'html' if item.endswith('.html') else \
           'css' if item.endswith('.css') else \
           'javascript' if item.endswith('.js') else \
           'json' if item.endswith('.json') else \
           'config' if item.endswith('.conf') or item.endswith('.theme') else \
           'bat' if item.endswith('.bat') else \
           'shell' if item.endswith('.sh') or item.endswith('.bash') else \
           'text' if item.endswith('.txt') else ''

    text = f'\n>>> BEGIN FILE {full_path}:\n'
    text += f'```{hint}\n'
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as file:
            text += file.read()
    except Exception as e:
        log.error(f"Error reading file for stats: {full_path}: {e}")
        raise
    text += '```\n'
    text += '<<< END FILE\n\n'
    return text


async def handle_ask_stats(msg):
    """Calculates stats for a potential 'ask' command."""
    try:
        prompt_text = msg.get('prompt', '')
        paths = msg.get('files', [])

        full_content = prompt_text

        for path in paths:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                continue

            if os.path.isdir(abs_path):
                full_content += get_directory_tree_as_text(abs_path, count=False)
                full_content += get_directory_contents_as_text(abs_path)
            elif os.path.isfile(abs_path):
                if not is_binary(abs_path):
                    full_content += _get_formatted_file_content(abs_path)

        byte_count = len(full_content.encode('utf-8'))
        token_count = len(ENCODING.encode(full_content))

        return {
            'type': 'ask_stats_response',
            'bytes': byte_count,
            'tokens': token_count,
            'nonce': msg.get('nonce')
        }
    except Exception as e:
        log.error(f"Error calculating ask stats: {e}", exc_info=True)
        return {'type': 'fs_error', 'error': 'Failed to calculate stats.', 'nonce': msg.get('nonce')}


async def pty_reader(pty_master_fd, websocket, term_id):
    """Reads from the pty and sends data to the websocket."""
    try:
        while websocket.open:
            try:
                data = os.read(pty_master_fd, 1024)
                if data:
                    await websocket.send(json.dumps({'type': 'term_data', 'term_id': term_id, 'data': data.decode('utf-8', errors='ignore')}))
                else:
                    log.info(f"PTY child process for term_id {term_id} exited.")
                    break  # EOF
            except BlockingIOError:
                await asyncio.sleep(0.01)
                continue
            except OSError as e:
                # This is expected when the child process exits.
                log.info(f"PTY child process for term_id {term_id} exited (OSError: {e}).")
                break
    except (ConnectionClosed, BrokenPipeError):
        log.info(f"PTY reader for term_id {term_id}: Connection closed.")
    except Exception as e:
        log.error(f"Error in pty_reader for term_id {term_id}: {e}")
    finally:
        log.info(f"PTY reader task for term_id {term_id} finished, notifying client of exit.")
        if websocket.open:
            try:
                await websocket.send(json.dumps({'type': 'term_exit', 'term_id': term_id}))
            except ConnectionClosed:
                pass # Client may have disconnected in the meantime.


async def directory_watcher_task(path):
    """Polls a directory for changes and notifies clients."""
    log.info(f"Starting watcher for: {path}")
    abs_path = os.path.abspath(path)
    
    try:
        current_state = {f: os.path.getmtime(os.path.join(abs_path, f)) for f in os.listdir(abs_path)}
        WATCHERS[path]['state'] = current_state

        while path in WATCHERS and WATCHERS[path]['clients']:
            await asyncio.sleep(2)
            
            if not os.path.isdir(abs_path):
                event_data = {'type': 'fs_watch_event', 'path': path, 'event_type': 'deleted', 'entry_name': os.path.basename(path), 'is_dir': True}
                clients = list(WATCHERS[path]['clients'])
                if clients:
                    await asyncio.gather(*[client.send(json.dumps(event_data)) for client in clients])
                break

            new_state = {f: os.path.getmtime(os.path.join(abs_path, f)) for f in os.listdir(abs_path)}
            
            old_files, new_files = set(current_state.keys()), set(new_state.keys())
            created, deleted = new_files - old_files, old_files - new_files
            
            events = []
            for f in created:
                events.append({'path': path, 'event_type': 'created', 'entry_name': f, 'is_dir': os.path.isdir(os.path.join(abs_path, f))})
            for f in deleted:
                events.append({'path': path, 'event_type': 'deleted', 'entry_name': f, 'is_dir': False})
            for f in old_files.intersection(new_files):
                if new_state[f] > current_state[f]:
                    events.append({'path': path, 'event_type': 'modified', 'entry_name': f, 'is_dir': os.path.isdir(os.path.join(abs_path, f))})
            
            if events:
                clients = list(WATCHERS[path]['clients'])
                if clients:
                    for event in events:
                        await asyncio.gather(*[client.send(json.dumps({'type': 'fs_watch_event', **event})) for client in clients])

            current_state = new_state
            WATCHERS[path]['state'] = current_state
    except Exception as e:
        log.error(f"Error in watcher for {path}: {e}")
    finally:
        if path in WATCHERS:
            del WATCHERS[path]
        log.info(f"Stopping watcher for: {path}")


async def file_tailer_task(path):
    """Polls a file for new content and sends it to clients."""
    log.info(f"Starting tailer for: {path}")
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            while path in TAILERS and TAILERS[path]['clients']:
                line = f.readline()
                if line:
                    clients = list(TAILERS[path]['clients'])
                    if clients:
                        await asyncio.gather(*[client.send(json.dumps({'type': 'fs_tail_event', 'path': path, 'data': line})) for client in clients])
                else:
                    await asyncio.sleep(0.1)
    except FileNotFoundError:
        log.warning(f"File to tail not found: {path}")
        if path in TAILERS:
            clients = list(TAILERS[path]['clients'])
            if clients:
                await asyncio.gather(*[client.send(json.dumps({'type': 'fs_tail_event', 'path': path, 'error': 'File not found'})) for client in clients])
    except Exception as e:
        log.error(f"Error in tailer for {path}: {e}")
        if path in TAILERS:
            clients = list(TAILERS[path]['clients'])
            if clients:
                await asyncio.gather(*[client.send(json.dumps({'type': 'fs_tail_event', 'path': path, 'error': str(e)})) for client in clients])
    finally:
        if path in TAILERS:
            del TAILERS[path]
        log.info(f"Stopping tailer for: {path}")


# --- ProcBox Process Management ---

async def broadcast_process_list():
    """Fetches all managed processes and broadcasts them to clients."""
    if not DB_CONN or not CONNECTED_CLIENTS:
        return
    
    cursor = DB_CONN.cursor()
    cursor.execute("""
        SELECT p.*, b.name as box_name, i.enable_stdin
        FROM process p 
        LEFT JOIN box b ON p.box_id = b.id
        LEFT JOIN iosk i ON p.box_id = i.box_id
        ORDER BY p.start_time DESC
    """)
    processes = [dict(row) for row in cursor.fetchall()]
    message = json.dumps({'type': 'running_processes_list', 'processes': processes})

    log.info(f"Broadcasting process_list to {len(CONNECTED_CLIENTS)} clients.")
    await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])

async def process_log_tailer(pid, stream, log_path):
    """Tails a log file for a process and broadcasts its output."""
    log.info(f"Starting log tailer for pid {pid} ({stream}) on {log_path}")
    try:
        await asyncio.sleep(0.1)
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    if CONNECTED_CLIENTS:
                        message = json.dumps({'type': 'process_output', 'pid': pid, 'stream': stream, 'data': line})
                        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])
                else:
                    await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass # Expected when process stops
    except Exception as e:
        log.error(f"Error in log tailer for pid {pid} ({stream}): {e}")
    finally:
        log.info(f"Stopping log tailer for pid {pid} ({stream}).")

async def process_monitor(pid, process_obj):
    """Waits for a process to exit and handles cleanup."""
    await process_obj.wait()
    log.info(f"Monitored process {pid} has terminated.")
    
    cursor = DB_CONN.cursor()
    cursor.execute("UPDATE process SET status = 'stopped' WHERE pid = ?", (pid,))
    DB_CONN.commit()
    
    proc_data = RUNNING_PROCESSES.pop(pid, None)
    if proc_data:
        log.info(f"Cleaning up resources for process {pid}.")
        proc_data['stdout_tailer'].cancel()
        proc_data['stderr_tailer'].cancel()
        if process_obj.stdout: process_obj.stdout.close()
        if process_obj.stderr: process_obj.stderr.close()
    
    await broadcast_process_list()

async def handle_start_iosk(msg):
    """Handles logic for launching and managing an iosk process."""
    box_id = msg.get('box_id')
    cursor = DB_CONN.cursor()
    cursor.execute("SELECT context FROM box WHERE id = ?", (box_id,))
    box_row = cursor.fetchone()
    if not box_row: return

    cursor.execute("SELECT mount_point, daemon_mode, enable_stdin FROM iosk WHERE box_id = ?", (box_id,))
    iosk_row = cursor.fetchone()
    if not iosk_row: return
    
    cursor.execute("SELECT id FROM process WHERE box_id = ? AND status IN ('running', 'paused')", (box_id,))
    if cursor.fetchone():
        log.warning(f"Process for box {box_id} is already running.")
        return

    # Find iosk executable
    sk_dir = os.path.dirname(sys.executable)
    iosk_executable = os.path.join(sk_dir, 'iosk')
    if platform.system() == 'Windows' and not os.path.exists(iosk_executable):
        iosk_executable += '.exe'
    if not os.path.exists(iosk_executable):
        iosk_executable = 'iosk' # Fallback to PATH

    # Prepare log files
    log_dir = os.path.join(config.DIRS.user_data_dir, 'proc_logs')
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    stdout_log = os.path.join(log_dir, f"{box_id}_{timestamp}.stdout.log")
    stderr_log = os.path.join(log_dir, f"{box_id}_{timestamp}.stderr.log")

    cmd = [iosk_executable, os.path.abspath(box_row['context'])]
    if iosk_row['mount_point']: cmd.append(os.path.abspath(iosk_row['mount_point']))
    
    proc_args = {
        'stdin': asyncio.subprocess.PIPE if iosk_row['enable_stdin'] else None,
        'stdout': open(stdout_log, 'w', buffering=1),
        'stderr': open(stderr_log, 'w', buffering=1),
    }

    if iosk_row['daemon_mode']:
        if platform.system() == 'Windows':
            proc_args['creationflags'] = subprocess.DETACHED_PROCESS
        else:
            proc_args['start_new_session'] = True

    try:
        process = await asyncio.create_subprocess_exec(*cmd, **proc_args)
        pid = process.pid
        print_action("Start IOSK", f"box={box_id}, pid={pid}, daemon={bool(iosk_row['daemon_mode'])}")

        start_time_iso = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO process (box_id, pid, type, start_time, status, stdout_log_path, stderr_log_path) VALUES (?, ?, 'iosk', ?, 'running', ?, ?)",
            (box_id, pid, start_time_iso, stdout_log, stderr_log)
        )
        DB_CONN.commit()

        RUNNING_PROCESSES[pid] = {
            'process': process,
            'monitor_task': asyncio.create_task(process_monitor(pid, process)),
            'stdout_tailer': asyncio.create_task(process_log_tailer(pid, 'stdout', stdout_log)),
            'stderr_tailer': asyncio.create_task(process_log_tailer(pid, 'stderr', stderr_log)),
        }
        
        await broadcast_process_list()
    except Exception as e:
        log.error(f"Failed to start iosk for box {box_id}: {e}", exc_info=True)
        # Update DB to error status
        cursor.execute("UPDATE process SET status = 'error' WHERE box_id = ?", (box_id,))
        DB_CONN.commit()
        await broadcast_process_list()

# --- End ProcBox ---


async def websocket_handler(websocket):
    """Main handler for each WebSocket connection."""
    log.info(f"Client connected from {websocket.remote_address}")
    CONNECTED_CLIENTS.add(websocket)
    active_terminals = {} # term_id -> {'pid': pid, 'fd': fd, 'task': task}

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get('type')

                # --- Filesystem Operations ---
                if msg_type == 'fs_list':
                    path = msg.get('path', '.')
                    recursive = msg.get('recursive', False)
                    requester_id = msg.get('requester_id')
                    print_action("FS List", f"path='{path}', recursive={recursive}, id={requester_id}")
                    response = await handle_fs_list(path, recursive, requester_id)
                    await websocket.send(json.dumps(response))
                elif msg_type == 'fs_read':
                    path = msg.get('path')
                    offset = msg.get('offset', 0)
                    length = msg.get('length', -1)
                    requester_id = msg.get('requester_id')
                    print_action("FS Read", f"path='{path}', offset={offset}, len={length}, id={requester_id}")
                    response = await handle_fs_read(path, offset, length, requester_id)
                    await websocket.send(json.dumps(response))

                # --- Filesystem Advanced Operations ---
                elif msg_type == 'fs_watch_start':
                    path = msg.get('path')
                    print_action("FS Watch Start", f"path='{path}'")
                    if path not in WATCHERS:
                        task = asyncio.create_task(directory_watcher_task(path))
                        WATCHERS[path] = {'clients': set(), 'task': task, 'state': {}}
                    WATCHERS[path]['clients'].add(websocket)
                elif msg_type == 'fs_watch_stop':
                    path = msg.get('path')
                    print_action("FS Watch Stop", f"path='{path}'")
                    if path in WATCHERS and websocket in WATCHERS[path]['clients']:
                        WATCHERS[path]['clients'].remove(websocket)
                        if not WATCHERS[path]['clients']:
                            WATCHERS[path]['task'].cancel()
                elif msg_type == 'fs_tail_start':
                    path = msg.get('path')
                    print_action("FS Tail Start", f"path='{path}'")
                    if path not in TAILERS:
                        task = asyncio.create_task(file_tailer_task(path))
                        TAILERS[path] = {'clients': set(), 'task': task}
                    TAILERS[path]['clients'].add(websocket)
                elif msg_type == 'fs_tail_stop':
                    path = msg.get('path')
                    print_action("FS Tail Stop", f"path='{path}'")
                    if path in TAILERS and websocket in TAILERS[path]['clients']:
                        TAILERS[path]['clients'].remove(websocket)
                        if not TAILERS[path]['clients']:
                            TAILERS[path]['task'].cancel()

                # --- Ask Operations ---
                elif msg_type == 'sk_ask':
                    print_action("SK Ask", f"prompt_len={len(msg.get('prompt', ''))}, files={len(msg.get('files', []))}")
                    asyncio.create_task(handle_sk_ask(websocket, msg))
                elif msg_type == 'ask_stats':
                    print_action("Ask Stats", f"prompt_len={len(msg.get('prompt', ''))}, files={len(msg.get('files', []))}")
                    response = await handle_ask_stats(msg)
                    await websocket.send(json.dumps(response))

                # --- Desktop Settings ---
                elif msg_type == 'update_desktop_settings':
                    box_id = msg.get('box_id', 0)
                    theme_blob = msg.get('settings', {})
                    print_action("Update Theme", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "INSERT OR REPLACE INTO config (box_id, theme) VALUES (?, ?)",
                        (box_id, json.dumps(theme_blob))
                    )
                    DB_CONN.commit()
                    await broadcast_box_list() # Broadcast to update has_custom_settings flag
                    
                    # After saving, broadcast the new specific settings for this box to keep client caches in sync.
                    # Get view settings
                    cursor.execute("SELECT key, value FROM settings WHERE box_id = ?", (box_id,))
                    view_settings = {}
                    for row in cursor.fetchall():
                        try:
                            view_settings[row['key']] = json.loads(row['value'])
                        except (json.JSONDecodeError, TypeError):
                            view_settings[row['key']] = row['value']

                    # Get theme config
                    cursor.execute("SELECT theme FROM config WHERE box_id = ?", (box_id,))
                    theme_row = cursor.fetchone()
                    theme_settings = json.loads(theme_row['theme']) if theme_row and theme_row['theme'] else {}

                    specific_settings = {**theme_settings, **view_settings}
                    
                    response_message = json.dumps({'type': 'box_specific_settings_response', 'settings': specific_settings, 'box_id': box_id})
                    if CONNECTED_CLIENTS:
                        log.info(f"Broadcasting updated specific settings for box {box_id}.")
                        await asyncio.gather(*[client.send(response_message) for client in CONNECTED_CLIENTS])

                
                elif msg_type == 'update_view_settings':
                    box_id = msg.get('box_id', 0)
                    view_settings = msg.get('settings', {})
                    print_action("Update View", f"box={box_id}, keys={list(view_settings.keys())}")
                    cursor = DB_CONN.cursor()
                    for key, value in view_settings.items():
                        cursor.execute(
                            "INSERT OR REPLACE INTO settings (box_id, key, value) VALUES (?, ?, ?)",
                            (box_id, key, json.dumps(value))
                        )
                    DB_CONN.commit()
                    # Broadcast full settings so client stays in sync
                    await broadcast_box_list() # Broadcast to update has_custom_settings flag
                    #await broadcast_settings(box_id)

                elif msg_type == 'clear_box_settings':
                    box_id = msg.get('box_id')
                    if box_id is None:
                        continue
                    
                    print_action("Clear Settings", f"box={box_id}")
                    cursor = DB_CONN.cursor()

                    cursor.execute("DELETE FROM config WHERE box_id = ?", (box_id,))
                    cursor.execute("DELETE FROM settings WHERE box_id = ?", (box_id,))
                    DB_CONN.commit()
                    
                    await broadcast_box_list() # To update the has_custom_settings flag
                    
                    # Also broadcast the new (empty) specific settings for the cleared box.
                    message = json.dumps({'type': 'box_specific_settings_response', 'settings': {}, 'box_id': box_id})
                    if CONNECTED_CLIENTS:
                        log.info(f"Broadcasting cleared specific settings for box {box_id}.")
                        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])


                # --- Desktop Shortcut Operations ---
                elif msg_type == 'create_shortcut':
                    box_id = msg.get('box_id', 0)
                    name, shortcut_type, path, x, y = msg['name'], msg['shortcut_type'], msg['path'], msg['x'], msg['y']
                    print_action("Create Shortcut", f"box={box_id}, path='{path}'")
                    cursor = DB_CONN.cursor()
                    cursor.execute("""
                        INSERT INTO shortcut (box_id, name, type, path, x, y)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(box_id, path) DO UPDATE SET
                            x = excluded.x,
                            y = excluded.y;
                    """, (box_id, name, shortcut_type, path, x, y))
                    DB_CONN.commit()
                    await broadcast_shortcut_list(box_id)

                elif msg_type == 'update_shortcut_transform':
                    shortcut_id, x, y, scale = msg['id'], msg['x'], msg['y'], msg.get('scale', 1.0)
                    print_action("Shortcut Xform", f"id={shortcut_id}, x={int(x)}, y={int(y)}, scale={scale:.2f}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT box_id FROM shortcut WHERE id = ?", (shortcut_id,))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute(
                            "UPDATE shortcut SET x = ?, y = ?, scale = ? WHERE id = ?",
                            (x, y, scale, shortcut_id)
                        )
                        DB_CONN.commit()
                        await broadcast_shortcut_list(row['box_id'])

                elif msg_type == 'delete_shortcut':
                    shortcut_id = msg['id']
                    print_action("Delete Shortcut", f"id={shortcut_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT box_id FROM shortcut WHERE id = ?", (shortcut_id,))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute("DELETE FROM shortcut WHERE id = ?", (shortcut_id,))
                        DB_CONN.commit()
                        await broadcast_shortcut_list(row['box_id'])

                # --- Backed Window Operations ---
                elif msg_type == 'create_backed_window':
                    box_id = msg.get('box_id', 0)
                    config, x, y, w, h, scale = msg['config'], msg['x'], msg['y'], msg['width'], msg['height'], msg.get('scale', 1.0)
                    original_group_id = msg.get('original_group_id')
                    print_action("Create BackWin", f"box={box_id}, x={int(x)}, y={int(y)}")
                    cursor = DB_CONN.cursor()

                    # MODIFICATION: Ensure original_group_id is unique for this box_id by deleting any stale entries.
                    # This is more robust than nullifying the ID.
                    if original_group_id is not None:
                        cursor.execute(
                            "DELETE FROM board WHERE box_id = ? AND original_group_id = ?",
                            (box_id, original_group_id)
                        )

                    cursor.execute(
                        "INSERT INTO board (box_id, config, x, y, width, height, scale, original_group_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (box_id, config, x, y, w, h, scale, original_group_id)
                    )
                    DB_CONN.commit()
                    await broadcast_backed_window_list(box_id)
                elif msg_type == 'update_backed_window_transform':
                    win_id, x, y, scale = msg['id'], msg['x'], msg['y'], msg.get('scale', 1.0)
                    config_json = msg.get('config')
                    action_details = f"id={win_id}, x={int(x)}, y={int(y)}, scale={scale:.2f}"
                    if config_json:
                        action_details += ", config=updated"
                    print_action("BackWin Xform ", action_details)
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT box_id FROM board WHERE id = ?", (win_id,))
                    row = cursor.fetchone()
                    if row:
                        if config_json:
                            cursor.execute(
                                "UPDATE board SET x = ?, y = ?, scale = ?, config = ? WHERE id = ?",
                                (x, y, scale, config_json, win_id)
                            )
                        else:
                            cursor.execute(
                                "UPDATE board SET x = ?, y = ?, scale = ? WHERE id = ?",
                                (x, y, scale, win_id)
                            )
                        DB_CONN.commit()
                        await broadcast_backed_window_list(row['box_id'])
                elif msg_type == 'delete_backed_window':
                    win_id = msg['id']
                    print_action("Delete BackWin", f"id={win_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT box_id FROM board WHERE id = ?", (win_id,))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute("DELETE FROM board WHERE id = ?", (win_id,))
                        DB_CONN.commit()
                        await broadcast_backed_window_list(row['box_id'])


                # --- Getters for Box Contents ---
                elif msg_type == 'get_desktop_settings':
                    box_id = msg.get('box_id', 0)
                    print_action("Get Dsk Set", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    
                    settings = get_resolved_settings_sync(box_id, cursor)

                    # Ensure defaults exist if config is partial/missing
                    if 'panX' not in settings: settings['panX'] = 0
                    if 'panY' not in settings: settings['panY'] = 0
                    if 'zoom' not in settings: settings['zoom'] = 1.0
                    await websocket.send(json.dumps({'type': 'desktop_settings', 'settings': settings, 'box_id': box_id}))

                elif msg_type == 'get_box_specific_settings':
                    box_id = msg.get('box_id', 0)
                    print_action("Get Box Spec Set", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    
                    # Get view settings
                    cursor.execute("SELECT key, value FROM settings WHERE box_id = ?", (box_id,))
                    view_settings = {}
                    for row in cursor.fetchall():
                        try:
                            view_settings[row['key']] = json.loads(row['value'])
                        except (json.JSONDecodeError, TypeError):
                            view_settings[row['key']] = row['value']

                    # Get theme config
                    cursor.execute("SELECT theme FROM config WHERE box_id = ?", (box_id,))
                    theme_row = cursor.fetchone()
                    theme_settings = json.loads(theme_row['theme']) if theme_row and theme_row['theme'] else {}

                    specific_settings = {**theme_settings, **view_settings}
                    
                    await websocket.send(json.dumps({'type': 'box_specific_settings_response', 'settings': specific_settings, 'box_id': box_id}))

                elif msg_type == 'get_shortcut_list':
                    box_id = msg.get('box_id', 0)
                    print_action("Get Shortcuts", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT id, name, type, path, x, y, scale FROM shortcut WHERE box_id = ?", (box_id,))
                    shortcuts = [dict(row) for row in cursor.fetchall()]
                    await websocket.send(json.dumps({'type': 'shortcut_list', 'shortcuts': shortcuts, 'box_id': box_id}))

                elif msg_type == 'get_backed_window_list':
                    box_id = msg.get('box_id', 0)
                    print_action("Get BackWins", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT id, config, x, y, width, height, scale, z_index, original_group_id FROM board WHERE box_id = ?", (box_id,))
                    windows = [dict(row) for row in cursor.fetchall()]
                    await websocket.send(json.dumps({'type': 'backed_window_list', 'windows': windows, 'box_id': box_id}))

                # --- ProcBox Operations ---
                elif msg_type == 'promote_to_iosk':
                    box_id = msg.get('box_id')
                    print_action("Promote to IOSK", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("UPDATE box SET type = 'iosk' WHERE id = ?", (box_id,))
                    cursor.execute("INSERT OR IGNORE INTO iosk (box_id) VALUES (?)", (box_id,))
                    DB_CONN.commit()
                    await broadcast_box_list()

                elif msg_type == 'get_iosk_config':
                    box_id = msg.get('box_id')
                    print_action("Get IOSK Cfg", f"box={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT box_id, mount_point, daemon_mode, enable_stdin FROM iosk WHERE box_id = ?", (box_id,))
                    config_row = cursor.fetchone()
                    config_data = dict(config_row) if config_row else None
                    await websocket.send(json.dumps({'type': 'iosk_config_response', 'box_id': box_id, 'config': config_data}))

                elif msg_type == 'update_iosk_config':
                    box_id = msg.get('box_id')
                    config = msg.get('config', {})
                    print_action("Update IOSK Cfg", f"box={box_id}, keys={list(config.keys())}")
                    cursor = DB_CONN.cursor()
                    # Use a helper to build the SET part of the query safely
                    allowed_keys = {'mount_point', 'daemon_mode', 'enable_stdin'}
                    updates = {k: v for k, v in config.items() if k in allowed_keys}
                    if updates:
                        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                        values = list(updates.values()) + [box_id]
                        cursor.execute(f"UPDATE iosk SET {set_clause} WHERE box_id = ?", tuple(values))
                        DB_CONN.commit()

                elif msg_type == 'start_iosk':
                    asyncio.create_task(handle_start_iosk(msg))

                elif msg_type == 'stop_process':
                    pid_to_stop = msg.get('pid')
                    print_action("Stop Process", f"pid={pid_to_stop}, signal=SIGTERM")
                    try:
                        if platform.system() == 'Windows':
                            subprocess.run(['taskkill', '/PID', str(pid_to_stop)], check=True, capture_output=True)
                        else:
                            os.kill(pid_to_stop, signal.SIGTERM)
                    except (ProcessLookupError, subprocess.CalledProcessError):
                        log.warning(f"Process {pid_to_stop} not found, already stopped.")
                        cursor = DB_CONN.cursor()
                        cursor.execute("UPDATE process SET status = 'stopped' WHERE pid = ?", (pid_to_stop,))
                        DB_CONN.commit()
                        await broadcast_process_list()
                    except Exception as e:
                        log.error(f"Failed to send SIGTERM to process {pid_to_stop}: {e}")
                
                elif msg_type == 'kill_process':
                    pid_to_kill = msg.get('pid')
                    print_action("Kill Process", f"pid={pid_to_kill}, signal=SIGKILL")
                    try:
                        if platform.system() == 'Windows':
                            subprocess.run(['taskkill', '/F', '/PID', str(pid_to_kill)], check=True, capture_output=True)
                        else:
                            os.kill(pid_to_kill, signal.SIGKILL)
                    except (ProcessLookupError, subprocess.CalledProcessError):
                        log.warning(f"Process {pid_to_kill} not found for kill, already stopped.")
                        cursor = DB_CONN.cursor()
                        cursor.execute("UPDATE process SET status = 'stopped' WHERE pid = ?", (pid_to_kill,))
                        DB_CONN.commit()
                        await broadcast_process_list()
                    except Exception as e:
                        log.error(f"Failed to send kill signal to process {pid_to_kill}: {e}")

                elif msg_type in ('pause_process', 'resume_process'):
                    if platform.system() == 'Windows':
                        log.warning("Pause/Resume is not supported on this platform (e.g., Windows).")
                        continue
                    
                    pid = msg.get('pid')
                    sig = signal.SIGSTOP if msg_type == 'pause_process' else signal.SIGCONT
                    new_status = 'paused' if msg_type == 'pause_process' else 'running'
                    print_action(msg_type.replace('_', ' ').title(), f"pid={pid}")

                    try:
                        os.kill(pid, sig)
                        cursor = DB_CONN.cursor()
                        cursor.execute("UPDATE process SET status = ? WHERE pid = ?", (new_status, pid))
                        DB_CONN.commit()
                        await broadcast_process_list()
                    except Exception as e:
                        log.error(f"Failed to send signal to process {pid}: {e}")
                
                elif msg_type == 'list_running_processes':
                    print_action("List Processes")
                    await broadcast_process_list()
                
                elif msg_type == 'process_stdin':
                    pid = msg.get('pid')
                    data = msg.get('data')
                    proc_data = RUNNING_PROCESSES.get(pid)
                    if proc_data and proc_data['process'].stdin:
                        try:
                            proc_data['process'].stdin.write(data.encode('utf-8'))
                            await proc_data['process'].stdin.drain()
                        except (BrokenPipeError, ConnectionResetError):
                            log.warning(f"stdin for process {pid} is closed.")
                        except Exception as e:
                            log.error(f"Error writing to stdin for process {pid}: {e}")


                # --- SKYBRIDGE Box Operations ---
                elif msg_type == 'list_boxes':
                    print_action("List Boxes")
                    cursor = DB_CONN.cursor()
                    boxes = _get_boxes_with_settings_info(cursor)
                    await websocket.send(json.dumps({'type': 'box_list', 'boxes': boxes}))

                elif msg_type == 'create_box':
                    name = msg.get('name')
                    box_type = msg.get('box_type')
                    context = msg.get('context')
                    aspect_ratio = msg.get('aspect_ratio')
                    x = msg.get('x')
                    y = msg.get('y')
                    parent_box_id = msg.get('parent_box_id', 0)
                    pos_str = f"pos=({int(x)},{int(y)})" if x is not None and y is not None else "pos=default"
                    ratio_str = f"{aspect_ratio:.2f}" if aspect_ratio is not None else "N/A"
                    print_action("Create Box", f"name='{name}', parent={parent_box_id}, type='{box_type}', ratio={ratio_str}, {pos_str}")
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "INSERT INTO box (name, type, context, aspect_ratio, x, y, parent_box_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (name, box_type, context, aspect_ratio, x, y, parent_box_id)
                    )
                    new_id = cursor.lastrowid

                    # Create default panels for the new box
                    # Left Panel: Files (-1, 0)
                    files_board_config = {
                        "x": 100, "y": 100,
                        "width": 500, "height": 600,
                        "maximized": False,
                        "activeTabId": 1,
                        "tabs": [
                            {
                                "originalId": 1,
                                "componentName": "LocalFileExplorer",
                                "title": f"Files - {name}",
                                "initialPath": context
                            }
                        ]
                    }
                    cursor.execute(
                        "INSERT INTO panel (box_id, loc_x, loc_y, parent_loc_x, parent_loc_y, board_type, board_config) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (new_id, -1, 0, 0, 0, 'window', json.dumps(files_board_config))
                    )

                    # Right Panel: Terminal (1, 0)
                    terminal_board_config = {
                        "x": 150, "y": 150,
                        "width": 800, "height": 500,
                        "maximized": False,
                        "activeTabId": 1,
                        "tabs": [
                            {
                                "originalId": 1,
                                "componentName": "LocalTerminal",
                                "title": f"Terminal - {name}",
                                "initialPath": context
                            }
                        ]
                    }
                    cursor.execute(
                        "INSERT INTO panel (box_id, loc_x, loc_y, parent_loc_x, parent_loc_y, board_type, board_config) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (new_id, 1, 0, 0, 0, 'window', json.dumps(terminal_board_config))
                    )

                    DB_CONN.commit()
                    await broadcast_box_list()
                    await broadcast_box_config(new_id)

                elif msg_type == 'update_box':
                    box_id = msg.get('id')
                    name = msg.get('name')
                    print_action("Update Box", f"id={box_id}, name='{name}'")
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "UPDATE box SET name = ? WHERE id = ?",
                        (msg.get('name'), msg.get('id'))
                    )
                    DB_CONN.commit()
                    await broadcast_box_list()

                elif msg_type == 'update_box_transform':
                    box_id = msg.get('id')
                    x, y, scale = msg.get('x'), msg.get('y'), msg.get('scale')
                    print_action("Box Transform", f"id={box_id}, x={int(x)}, y={int(y)}, scale={scale:.2f}")
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "UPDATE box SET x = ?, y = ?, scale = ? WHERE id = ?",
                        (x, y, scale, box_id)
                    )
                    DB_CONN.commit()
                    await broadcast_box_list()

                elif msg_type == 'set_box_cover':
                    box_id = msg.get('box_id')
                    location = msg.get('location') # can be a coordinate string 'x_y' or None
                    print_action("Set Box Cover", f"id={box_id}, loc='{location}'")
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "UPDATE box SET cover_panel_location = ? WHERE id = ?",
                        (location, box_id)
                    )
                    DB_CONN.commit()
                    await broadcast_box_list()

                elif msg_type == 'delete_box':
                    box_id = msg.get('id')
                    print_action("Delete Box", f"id={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("DELETE FROM box WHERE id = ?", (msg.get('id'),))
                    DB_CONN.commit()
                    await broadcast_box_list()

                # --- SKYBRIDGE Panel/Board Operations ---
                elif msg_type == 'get_box_config':
                    box_id = msg.get('id')
                    print_action("Get Box Cfg", f"id={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT id, box_id, loc_x, loc_y, parent_loc_x, parent_loc_y, board_type, board_config FROM panel WHERE box_id = ?", (box_id,))
                    panels = []
                    for row in cursor.fetchall():
                        panel = dict(row)
                        try:
                            if panel['board_config']:
                                panel['board_config'] = json.loads(panel['board_config'])
                        except json.JSONDecodeError:
                            log.warning(f"Could not decode board_config for panel at ({panel['loc_x']},{panel['loc_y']}) in box {box_id}")
                            panel['board_config'] = None
                        panels.append(panel)

                    await websocket.send(json.dumps({
                        'type': 'box_config_response',
                        'box_id': box_id,
                        'panels': panels
                    }))

                elif msg_type == 'set_panel_config':
                    box_id = msg.get('box_id')
                    loc_x = msg.get('loc_x')
                    loc_y = msg.get('loc_y')
                    parent_loc_x = msg.get('parent_loc_x')
                    parent_loc_y = msg.get('parent_loc_y')
                    board_type = msg.get('board_type')
                    print_action("Set Panel", f"box_id={box_id}, loc=({loc_x},{loc_y}), parent=({parent_loc_x},{parent_loc_y}), type='{board_type}'")
                    board_config = msg.get('board_config') # This is a dict from client

                    cursor = DB_CONN.cursor()
                    if board_type == 'empty':
                        cursor.execute(
                            "DELETE FROM panel WHERE box_id = ? AND loc_x = ? AND loc_y = ?",
                            (box_id, loc_x, loc_y)
                        )
                    else:
                        # Serialize the board_config dict to a JSON string for storage
                        board_config_json = json.dumps(board_config) if board_config else None

                        # Use UPSERT (INSERT ... ON CONFLICT)
                        cursor.execute("""
                            INSERT INTO panel (box_id, loc_x, loc_y, parent_loc_x, parent_loc_y, board_type, board_config)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(box_id, loc_x, loc_y) DO UPDATE SET
                                parent_loc_x = excluded.parent_loc_x,
                                parent_loc_y = excluded.parent_loc_y,
                                board_type = excluded.board_type,
                                board_config = excluded.board_config;
                        """, (box_id, loc_x, loc_y, parent_loc_x, parent_loc_y, board_type, board_config_json))

                    DB_CONN.commit()
                    # After successful update, broadcast the new state to all clients
                    await broadcast_box_config(box_id)

                # --- Terminal Operations ---
                elif pty and msg_type == 'term_open':
                    term_id = msg.get('term_id')
                    if not term_id:
                        log.error("term_open message missing term_id")
                        continue

                    if term_id in active_terminals:
                        log.warning(f"Terminal with term_id {term_id} already open for this connection.")
                        continue

                    path = msg.get('path')
                    print_action("Term Open", f"id='{term_id}', path='{path}'" if path else f"id='{term_id}'")
                    (pid, fd) = pty.fork()

                    if pid == 0:  # Child process
                        if path and os.path.isdir(path):
                            try:
                                os.chdir(path)
                                log.info(f"Child process for term_id {term_id} changed directory to: {path}")
                            except Exception as e:
                                log.error(f"Could not change directory to {path} for term_id {term_id}: {e}")

                        shell = os.environ.get('SHELL', 'sh')
                        log.info(f"Child process for term_id {term_id} launching shell: {shell}")
                        os.execvpe(shell, [shell], os.environ)
                    else:  # Parent process
                        log.info(f"PTY forked for term_id {term_id} with child PID: {pid}")
                        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                        reader_task = asyncio.create_task(pty_reader(fd, websocket, term_id))
                        active_terminals[term_id] = {'pid': pid, 'fd': fd, 'task': reader_task}

                elif pty and msg_type == 'term_data':
                    term_id = msg.get('term_id')
                    term_session = active_terminals.get(term_id)
                    if term_session:
                        os.write(term_session['fd'], msg.get('data', '').encode('utf-8'))

                elif pty and msg_type == 'term_resize':
                    term_id = msg.get('term_id')
                    term_session = active_terminals.get(term_id)
                    if term_session:
                        rows, cols = msg.get('rows', 24), msg.get('cols', 80)
                        print_action("Term Resize", f"id='{term_id}', rows={rows}, cols={cols}")
                        winsize = struct.pack('HHHH', rows, cols, 0, 0)
                        fcntl.ioctl(term_session['fd'], termios.TIOCSWINSZ, winsize)

                elif pty and msg_type == 'term_close':
                    term_id = msg.get('term_id')
                    if term_id in active_terminals:
                        print_action("Term Close", f"id='{term_id}'")
                        term_session = active_terminals.pop(term_id)
                        term_session['task'].cancel()
                        os.close(term_session['fd'])
                        try:
                            os.kill(term_session['pid'], 15)  # SIGTERM
                        except ProcessLookupError:
                            pass # Process may have already exited
                    else:
                        log.warning(f"Received term_close for non-existent term_id: {term_id}")

                else:
                    if msg_type and msg_type.startswith('term_') and not pty:
                        log.warning("Terminal operations are not supported on this platform (e.g., Windows).")
                    else:
                        log.warning(f"Unknown message type or invalid state: {msg_type}")

            except json.JSONDecodeError:
                log.error("Received non-JSON message.")
            except Exception as e:
                log.error(f"Error processing message: {e}", exc_info=True)

    except ConnectionClosed:
        log.info("Client disconnected.")
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        
        # Disconnect client from any watchers and cancel tasks if no clients left
        for path, data in list(WATCHERS.items()):
            if websocket in data['clients']:
                data['clients'].remove(websocket)
            if not data['clients']:
                data['task'].cancel()
        
        # Disconnect client from any tailers and cancel tasks if no clients left
        for path, data in list(TAILERS.items()):
            if websocket in data['clients']:
                data['clients'].remove(websocket)
            if not data['clients']:
                data['task'].cancel()

        if active_terminals:
            log.info(f"Cleaning up {len(active_terminals)} PTY resources for disconnected client.")
            for term_id, term_session in active_terminals.items():
                log.info(f"  - Cleaning up term_id {term_id} (PID: {term_session['pid']})")
                term_session['task'].cancel()
                os.close(term_session['fd'])
                try:
                    os.kill(term_session['pid'], 15)  # SIGTERM
                except ProcessLookupError:
                    pass


async def start_server():
    """Starts the WebSocket server."""
    async with serve(websocket_handler, HOST, PORT):
        await asyncio.Future()  # run forever


def main(args):
    """Entry point for `sk local` command."""
    print_startup_banner()
    init_db()  # Initialize the database on startup
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print_shutdown_message()
    except OSError as e:
        if e.errno == 98:  # Address already in use
            log.error(f"Error: Port {PORT} is already in use.")
            log.error("Another instance of sk-local might be running, or another service is using that port.")
        else:
            raise e
    finally:
        if DB_CONN:
            DB_CONN.close()
            log.info("Database connection closed.")
        print_stopped_message()