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
from datetime import datetime
from . import config
from .util import get_directory_tree_as_text, get_directory_contents_as_text
from binaryornot.check import is_binary

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
        log.info(f"Starting Skybox Local Server on ws://{HOST}:{PORT}")
        return
    print(f"\n{Colors.BOLD}{Colors.GREEN}--- Skybox Local Server ---{Colors.RESET}")
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

# --- Skybox Globals ---
DB_CONN = None
CONNECTED_CLIENTS = set()
# --------------------

def init_db():
    """Initializes the SQLite database for Skybox."""
    global DB_CONN
    db_path = os.path.join(config.DIRS.user_data_dir, 'skybox.db')
    log.info(f"Using Skybox database at {db_path}")
    DB_CONN = sqlite3.connect(db_path)
    DB_CONN.row_factory = sqlite3.Row  # Makes rows dict-like
    DB_CONN.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
    cursor = DB_CONN.cursor()
    
    # Check if box table exists to decide if we need to check for migration
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='box';")
    box_table_exists = cursor.fetchone()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS box (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('local', 'iosk')),
            context TEXT NOT NULL,
            x INTEGER DEFAULT 100,
            y INTEGER DEFAULT 100,
            scale REAL DEFAULT 1.0
        );
    """)

    # If table already existed, check if we need to add columns for migration
    if box_table_exists:
        cursor.execute("PRAGMA table_info(box)")
        columns = [col['name'] for col in cursor.fetchall()]
        if 'x' not in columns:
            log.info("Migrating 'box' table: adding 'x' column.")
            cursor.execute("ALTER TABLE box ADD COLUMN x INTEGER DEFAULT 100")
        if 'y' not in columns:
            log.info("Migrating 'box' table: adding 'y' column.")
            cursor.execute("ALTER TABLE box ADD COLUMN y INTEGER DEFAULT 100")
        if 'scale' not in columns:
            log.info("Migrating 'box' table: adding 'scale' column.")
            cursor.execute("ALTER TABLE box ADD COLUMN scale REAL DEFAULT 1.0")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS panel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            location TEXT NOT NULL CHECK(location IN ('center', 'top', 'bottom', 'left', 'right', 'cover')),
            board_type TEXT NOT NULL CHECK(board_type IN ('empty', 'window', 'tabs', 'dash', 'image')),
            board_config TEXT, -- JSON blob for the BOARD configuration
            FOREIGN KEY(box_id) REFERENCES box(id) ON DELETE CASCADE,
            UNIQUE(box_id, location)
        );
    """)
    DB_CONN.commit()
    log.info("Skybox database initialized.")

async def broadcast_box_list():
    """Fetches all boxes and broadcasts them to all connected clients."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast box list.")
        return

    cursor = DB_CONN.cursor()
    cursor.execute("SELECT id, name, type, context, x, y, scale FROM box ORDER BY name")
    boxes = [dict(row) for row in cursor.fetchall()]
    
    message = json.dumps({'type': 'box_list', 'boxes': boxes})
    
    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting box_list to {len(CONNECTED_CLIENTS)} clients.")
        # Concurrently send the message to all clients.
        await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])


async def broadcast_box_config(box_id):
    """Fetches the panel config for a box and broadcasts it to all clients."""
    if not DB_CONN:
        log.error("Database not connected, cannot broadcast box config.")
        return

    cursor = DB_CONN.cursor()
    cursor.execute("SELECT box_id, location, board_type, board_config FROM panel WHERE box_id = ?", (box_id,))
    panels = []
    for row in cursor.fetchall():
        panel = dict(row)
        try:
            if panel['board_config']:
                panel['board_config'] = json.loads(panel['board_config'])
        except json.JSONDecodeError:
            log.warning(f"Could not decode board_config for panel {panel['location']} in box {box_id}")
            panel['board_config'] = None
        panels.append(panel)

    message = json.dumps({'type': 'box_config_response', 'box_id': box_id, 'panels': panels})

    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting box_config for box {box_id} to {len(CONNECTED_CLIENTS)} clients.")
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


async def handle_fs_list(path):
    """Handles the fs_list request."""
    try:
        abs_path = os.path.abspath(path)

        if not os.path.isdir(abs_path):
            return {'type': 'fs_error', 'path': path, 'error': 'Not a directory or does not exist'}

        entries = []
        for name in sorted(os.listdir(abs_path)):
            try:
                full_path = os.path.join(abs_path, name)
                stat = os.stat(full_path)
                entry_type = 'dir' if os.path.isdir(full_path) else 'file'
                entries.append({'name': name, 'type': entry_type, 'size': stat.st_size})
            except OSError:
                continue
        return {'type': 'fs_list_response', 'path': path, 'entries': entries}
    except Exception as e:
        log.error(f"Error listing path {path}: {e}")
        return {'type': 'fs_error', 'path': path, 'error': str(e)}


async def handle_fs_read(path):
    """Handles the fs_read request."""
    try:
        abs_path = os.path.abspath(path)

        if not os.path.isfile(abs_path):
            return {'type': 'fs_error', 'path': path, 'error': 'Not a file or does not exist'}

        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {'type': 'fs_read_response', 'path': path, 'content': content}
    except Exception as e:
        log.error(f"Error reading path {path}: {e}")
        return {'type': 'fs_error', 'path': path, 'error': str(e)}


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
                    print_action("FS List", f"path='{path}'")
                    response = await handle_fs_list(path)
                    await websocket.send(json.dumps(response))
                elif msg_type == 'fs_read':
                    path = msg.get('path')
                    print_action("FS Read", f"path='{path}'")
                    response = await handle_fs_read(path)
                    await websocket.send(json.dumps(response))
                
                # --- Ask Operations ---
                elif msg_type == 'sk_ask':
                    print_action("SK Ask", f"prompt_len={len(msg.get('prompt', ''))}, files={len(msg.get('files', []))}")
                    asyncio.create_task(handle_sk_ask(websocket, msg))
                elif msg_type == 'ask_stats':
                    print_action("Ask Stats", f"prompt_len={len(msg.get('prompt', ''))}, files={len(msg.get('files', []))}")
                    response = await handle_ask_stats(msg)
                    await websocket.send(json.dumps(response))

                # --- Skybox Box Operations ---
                elif msg_type == 'list_boxes':
                    print_action("List Boxes")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT id, name, type, context, x, y, scale FROM box ORDER BY name")
                    boxes = [dict(row) for row in cursor.fetchall()]
                    await websocket.send(json.dumps({'type': 'box_list', 'boxes': boxes}))
                
                elif msg_type == 'create_box':
                    name = msg.get('name')
                    box_type = msg.get('box_type')
                    context = msg.get('context')
                    print_action("Create Box", f"name='{name}', type='{box_type}'")
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "INSERT INTO box (name, type, context) VALUES (?, ?, ?)",
                        (name, box_type, context)
                    )
                    new_id = cursor.lastrowid
                    
                    # Create default panels for the new box
                    # Left Panel: Files
                    files_board_config = {
                        "x": 100, "y": 100,
                        "width": 500, "height": 600,
                        "maximized": False,
                        "activeTabId": 1,
                        "tabs": [
                            {
                                "originalId": 1,
                                "componentType": "LocalFileExplorer",
                                "title": f"Files - {name}",
                                "initialPath": context
                            }
                        ]
                    }
                    cursor.execute(
                        "INSERT INTO panel (box_id, location, board_type, board_config) VALUES (?, ?, ?, ?)",
                        (new_id, 'left', 'window', json.dumps(files_board_config))
                    )

                    # Right Panel: Terminal
                    terminal_board_config = {
                        "x": 150, "y": 150,
                        "width": 800, "height": 500,
                        "maximized": False,
                        "activeTabId": 1,
                        "tabs": [
                            {
                                "originalId": 1,
                                "componentType": "LocalTerminal",
                                "title": f"Terminal - {name}",
                                "initialPath": context
                            }
                        ]
                    }
                    cursor.execute(
                        "INSERT INTO panel (box_id, location, board_type, board_config) VALUES (?, ?, ?, ?)",
                        (new_id, 'right', 'window', json.dumps(terminal_board_config))
                    )

                    DB_CONN.commit()
                    await broadcast_box_list()

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
                
                elif msg_type == 'delete_box':
                    box_id = msg.get('id')
                    print_action("Delete Box", f"id={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("DELETE FROM box WHERE id = ?", (msg.get('id'),))
                    DB_CONN.commit()
                    await broadcast_box_list()
                
                # --- Skybox Panel/Board Operations ---
                elif msg_type == 'get_box_config':
                    box_id = msg.get('id')
                    print_action("Get Box Cfg", f"id={box_id}")
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT box_id, location, board_type, board_config FROM panel WHERE box_id = ?", (box_id,))
                    panels = []
                    for row in cursor.fetchall():
                        panel = dict(row)
                        try:
                            if panel['board_config']:
                                panel['board_config'] = json.loads(panel['board_config'])
                        except json.JSONDecodeError:
                            log.warning(f"Could not decode board_config for panel {panel['location']} in box {box_id}")
                            panel['board_config'] = None
                        panels.append(panel)
                    
                    await websocket.send(json.dumps({
                        'type': 'box_config_response',
                        'box_id': box_id,
                        'panels': panels
                    }))

                elif msg_type == 'set_panel_config':
                    box_id = msg.get('box_id')
                    location = msg.get('location')
                    board_type = msg.get('board_type')
                    print_action("Set Panel", f"box_id={box_id}, loc='{location}', type='{board_type}'")
                    board_config = msg.get('board_config') # This is a dict from client

                    cursor = DB_CONN.cursor()
                    if board_type == 'empty':
                        cursor.execute(
                            "DELETE FROM panel WHERE box_id = ? AND location = ?",
                            (box_id, location)
                        )
                    else:
                        # Serialize the board_config dict to a JSON string for storage
                        board_config_json = json.dumps(board_config) if board_config else None
                        
                        # Use UPSERT (INSERT ... ON CONFLICT)
                        cursor.execute("""
                            INSERT INTO panel (box_id, location, board_type, board_config)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(box_id, location) DO UPDATE SET
                                board_type = excluded.board_type,
                                board_config = excluded.board_config;
                        """, (box_id, location, board_type, board_config_json))
                    
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