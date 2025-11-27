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
    cursor = DB_CONN.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS box (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('local', 'iosk')),
            context TEXT NOT NULL
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
    cursor.execute("SELECT id, name, type, context FROM box ORDER BY name")
    boxes = [dict(row) for row in cursor.fetchall()]
    
    message = json.dumps({'type': 'box_list', 'boxes': boxes})
    
    if CONNECTED_CLIENTS:
        log.info(f"Broadcasting box_list to {len(CONNECTED_CLIENTS)} clients.")
        # Create a list of send tasks that can be awaited
        tasks = [client.send(message) for client in CONNECTED_CLIENTS]
        if tasks:
            await asyncio.wait(tasks)


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


async def pty_reader(pty_master_fd, websocket):
    """Reads from the pty and sends data to the websocket."""
    try:
        while websocket.open:
            try:
                data = os.read(pty_master_fd, 1024)
                if data:
                    await websocket.send(json.dumps({'type': 'term_data', 'data': data.decode('utf-8', errors='ignore')}))
                else:
                    log.info("PTY child process exited.")
                    break  # EOF
            except BlockingIOError:
                await asyncio.sleep(0.01)
                continue
    except (ConnectionClosed, BrokenPipeError):
        log.info("PTY reader: Connection closed.")
    except Exception as e:
        log.error(f"Error in pty_reader: {e}")
    finally:
        log.info("PTY reader task finished.")
        if websocket.open:
            await websocket.close(reason='PTY process exited')


async def websocket_handler(websocket):
    """Main handler for each WebSocket connection."""
    log.info(f"Client connected from {websocket.remote_address}")
    CONNECTED_CLIENTS.add(websocket)
    pty_master_fd = None
    pty_child_pid = None
    reader_task = None

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get('type')

                # --- Filesystem Operations ---
                if msg_type == 'fs_list':
                    response = await handle_fs_list(msg.get('path', '.'))
                    await websocket.send(json.dumps(response))
                elif msg_type == 'fs_read':
                    response = await handle_fs_read(msg.get('path'))
                    await websocket.send(json.dumps(response))
                
                # --- Ask Operations ---
                elif msg_type == 'sk_ask':
                    asyncio.create_task(handle_sk_ask(websocket, msg))
                elif msg_type == 'ask_stats':
                    response = await handle_ask_stats(msg)
                    await websocket.send(json.dumps(response))

                # --- Skybox Box Operations ---
                elif msg_type == 'list_boxes':
                    cursor = DB_CONN.cursor()
                    cursor.execute("SELECT id, name, type, context FROM box ORDER BY name")
                    boxes = [dict(row) for row in cursor.fetchall()]
                    await websocket.send(json.dumps({'type': 'box_list', 'boxes': boxes}))
                
                elif msg_type == 'create_box':
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "INSERT INTO box (name, type, context) VALUES (?, ?, ?)",
                        (msg.get('name'), msg.get('box_type'), msg.get('context'))
                    )
                    new_id = cursor.lastrowid
                    DB_CONN.commit()
                    cursor.execute("SELECT * FROM box WHERE id = ?", (new_id,))
                    new_box_row = cursor.fetchone()
                    new_box = dict(new_box_row) if new_box_row else None
                    await websocket.send(json.dumps({'type': 'box_created', 'box': new_box}))
                    await broadcast_box_list()

                elif msg_type == 'update_box':
                    cursor = DB_CONN.cursor()
                    cursor.execute(
                        "UPDATE box SET name = ? WHERE id = ?",
                        (msg.get('name'), msg.get('id'))
                    )
                    DB_CONN.commit()
                    await broadcast_box_list()
                
                elif msg_type == 'delete_box':
                    cursor = DB_CONN.cursor()
                    cursor.execute("DELETE FROM box WHERE id = ?", (msg.get('id'),))
                    DB_CONN.commit()
                    await broadcast_box_list()

                # --- Terminal Operations ---
                elif pty and msg_type == 'term_open':
                    if pty_child_pid:
                        log.warning("Terminal already open for this connection.")
                        continue

                    (pid, fd) = pty.fork()
                    pty_master_fd, pty_child_pid = fd, pid

                    if pid == 0:  # Child process
                        shell = os.environ.get('SHELL', 'sh')
                        log.info(f"Child process launching shell: {shell}")
                        os.execvpe(shell, [shell], os.environ)
                    else:  # Parent process
                        log.info(f"PTY forked with child PID: {pid}")
                        fl = fcntl.fcntl(pty_master_fd, fcntl.F_GETFL)
                        fcntl.fcntl(pty_master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                        reader_task = asyncio.create_task(pty_reader(pty_master_fd, websocket))

                elif pty and msg_type == 'term_data' and pty_master_fd is not None:
                    os.write(pty_master_fd, msg.get('data', '').encode('utf-8'))

                elif pty and msg_type == 'term_resize' and pty_master_fd is not None:
                    winsize = struct.pack('HHHH', msg.get('rows', 24), msg.get('cols', 80), 0, 0)
                    fcntl.ioctl(pty_master_fd, termios.TIOCSWINSZ, winsize)

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
        if pty_child_pid:
            log.info(f"Cleaning up PTY resources for PID {pty_child_pid}.")
            if reader_task:
                reader_task.cancel()
            if pty_master_fd:
                os.close(pty_master_fd)
            try:
                os.kill(pty_child_pid, 15)  # SIGTERM
            except ProcessLookupError:
                pass  # Process may have already exited


async def start_server():
    """Starts the WebSocket server."""
    log.info(f"Starting sk-local server on ws://{HOST}:{PORT}")
    async with serve(websocket_handler, HOST, PORT):
        await asyncio.Future()  # run forever


def main(args):
    """Entry point for `sk local` command."""
    init_db()  # Initialize the database on startup
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
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