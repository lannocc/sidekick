# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import asyncio
import json
import os
import logging
import platform
import sys

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

running_asks = {}


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
    pty_master_fd = None
    pty_child_pid = None
    reader_task = None

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get('type')

                if msg_type == 'fs_list':
                    response = await handle_fs_list(msg.get('path', '.'))
                    await websocket.send(json.dumps(response))
                elif msg_type == 'fs_read':
                    response = await handle_fs_read(msg.get('path'))
                    await websocket.send(json.dumps(response))
                elif msg_type == 'sk_ask':
                    asyncio.create_task(handle_sk_ask(websocket, msg))

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