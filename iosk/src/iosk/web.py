# src/iosk/web.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

"""
Dedicated message handlers for the PortManager.

This module decouples the message processing logic from the connection
lifecycle management in PortManager, as per the refactoring proposal.
Each `handle_*` function corresponds to a message type received from
a peer or client.
"""

import asyncio
import json
import logging
import traceback
import base64
import os
import posixpath
import shlex

from typing import TYPE_CHECKING, Dict, Any, Optional

from binaryornot.check import is_binary
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

if TYPE_CHECKING:
    from .port import PortManager, Connection
    from .io import Context
    from websockets.server import WebSocketServerProtocol

log = logging.getLogger(__name__)


# Helper class for fs_watch, moved from PortManager
class _ClientUpdateEventHandler(FileSystemEventHandler):
    """Helper class to dispatch watchdog events back to the client."""
    def __init__(self, port_manager: "PortManager", user: str, watched_path: str, loop: asyncio.AbstractEventLoop):
        self.port_manager = port_manager
        self.user = user
        self.watched_path = watched_path
        self.loop = loop

    def on_any_event(self, event):
        # We are in a separate thread. Use thread-safe call.
        affected_filename = os.path.basename(event.src_path)
        affected_virtual_path = posixpath.join(self.watched_path, affected_filename)

        payload = {
            "type": "fs_watch_update",
            "path": self.watched_path,
            "event_type": event.event_type, # 'created', 'deleted', 'modified', 'moved'
            "affected_path": affected_virtual_path,
            "is_dir": event.is_directory
        }
        coro = self.port_manager.send_payload_to_client(self.user, payload)
        asyncio.run_coroutine_threadsafe(coro, self.loop)


async def handle_forward_request(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    final_destination = message.get('final_destination')
    payload = message.get('payload')
    if not final_destination or payload is None:
        log.warning(f"Malformed forward_request received: {message}")
        return
    # Do not process locally. Unwrap and route it onward.
    await port_manager.route_message(final_destination, payload)


async def handle_peer_update(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    from_peer_hostname = conn_meta.hostname
    await port_manager._handle_peer_update(message, from_peer=from_peer_hostname)


async def handle_state_gossip(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], message_str: str):
    """Handles messages that update shared state and need to be forwarded."""
    # 1. Process locally first
    await _process_network_state_update(port_manager, message)
    # 2. Forward the update to all other peers
    peers_to_notify = {h: ws for h, ws in port_manager.peers.items() if h != conn_meta.hostname}
    if peers_to_notify:
        msg_type = message.get("type")
        log.info(f"Forwarding {msg_type} from {conn_meta.hostname} to {list(peers_to_notify.keys())}")
        aws = [ws.send(message_str) for ws in peers_to_notify.values()]
        await asyncio.gather(*aws, return_exceptions=True)

# Alias for clarity in the router
handle_user_update = handle_state_gossip
handle_room_update = handle_state_gossip
handle_room_state_update = handle_state_gossip
handle_user_colors_update = handle_state_gossip


async def handle_state_sync(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    await _process_network_state_update(port_manager, message)


async def handle_system_broadcast(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    msg_content = message.get("message")
    if msg_content:
        await port_manager.os.system.print(msg_content)


async def handle_remote_exec_request(port_manager: "PortManager", websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    await port_manager._handle_remote_exec(websocket, message)


async def handle_remote_exec_response(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    await port_manager._handle_remote_exec_response(message)


async def handle_room_message(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], message_str: str):
    msg_id = message.get("msg_id")
    if msg_id:
        if msg_id in port_manager.seen_message_ids:
            return  # Already processed this message, drop it.
        port_manager.seen_message_ids.add(msg_id)
        if len(port_manager.seen_message_ids) > port_manager.MESSAGE_ID_CACHE_SIZE:
            port_manager.seen_message_ids.pop() # Evict an old ID

    # 1. Process the message locally
    await port_manager.os.chat.handle_network_message(message)

    # 2. Forward the message to all other connected peers
    from_peer_hostname = conn_meta.hostname
    peers_to_forward = {h: ws for h, ws in port_manager.peers.items() if h != from_peer_hostname}
    if peers_to_forward:
        log.info(f"Forwarding room message from '{from_peer_hostname}' to {list(peers_to_forward.keys())}")
        aws = [ws.send(message_str) for ws in peers_to_forward.values()]
        await asyncio.gather(*aws, return_exceptions=True)


async def handle_direct_message(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    await port_manager.os.chat.handle_network_message(message)


async def handle_client_input(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        await port_manager.os.handle_client_input(conn_meta.username, message.get("data", ""))
    else:
        log.warning("Received client_input from non-client connection.")


async def handle_room_action(port_manager: "PortManager", _websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        action = message.get("action")
        if action == "join":
            room_name = message.get("roomName")
            if room_name:
                command = f"$ room {shlex.quote(room_name)}"
                await port_manager.os.handle_client_input(conn_meta.username, command + '\n')
        elif action == "close":
            command = "$ clroom"
            await port_manager.os.handle_client_input(conn_meta.username, command + '\n')
    else:
        log.warning("Received room_action from non-client connection.")


async def handle_exec_command(port_manager: "PortManager", websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        io_context = port_manager.os.users.contexts.get(conn_meta.username)
        if io_context:
            await port_manager._handle_exec_command(websocket, io_context, message)
    else:
        log.warning("Received exec_command from non-client connection.")


async def handle_fs_list(port_manager: "PortManager", websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        path = message.get("path", "/")
        requesterId = message.get("requesterId")
        recursive = message.get("recursive", False)
        io_context = port_manager.os.users.contexts.get(conn_meta.username)
        if io_context:
            await port_manager._handle_fs_list(websocket, io_context, path, requesterId, recursive)
    else:
        log.warning("Received fs_list from non-client connection.")


async def handle_fs_read(port_manager: "PortManager", websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        io_context = port_manager.os.users.contexts.get(conn_meta.username)
        if io_context:
            await port_manager._handle_fs_read(websocket, io_context, message)
    else:
        log.warning("Received fs_read from non-client or malformed request.")


async def handle_fs_watch_start(port_manager: "PortManager", websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        path = message.get("path")
        io_context = port_manager.os.users.contexts.get(conn_meta.username)
        if io_context and path:
            await port_manager._handle_fs_watch_start(websocket, io_context, path)


async def handle_fs_watch_stop(port_manager: "PortManager", websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    path = message.get("path")
    if path:
        await port_manager._handle_fs_watch_stop(websocket, path)


async def handle_fs_tail_start(port_manager: "PortManager", websocket: "WebSocketServerProtocol", conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    if conn_meta.type == 'client' and conn_meta.username:
        path = message.get("path")
        io_context = port_manager.os.users.contexts.get(conn_meta.username)
        if io_context and path:
            await port_manager._handle_fs_tail_start(websocket, io_context, path)


async def handle_fs_tail_stop(port_manager: "PortManager", websocket: "WebSocketServerProtocol", _conn_meta: "Connection", message: Dict[str, Any], _message_str: str):
    path = message.get("path")
    if path:
        await port_manager._handle_fs_tail_stop(websocket, path)


async def _process_network_state_update(port_manager: "PortManager", message: dict):
    """Processes state update messages from peers to update the kernel's state caches."""
    msg_type = message.get("type")

    if msg_type == "user_update":
        action = message.get("action")
        user = message.get("user")
        host = message.get("host")

        if not all([action, user, host]):
            return # Malformed message

        user_addr = f"{user}.{host}"
        if action == "login":
            is_bot = message.get('is_bot', False)
            paused = message.get('paused', False)
            port_manager.os.network_users[user_addr] = {'is_bot': is_bot, 'paused': paused} # Add user
            # Assign color for this network user to all local interactive users
            for uio in port_manager.os.users.contexts.values():
                if not uio.session.bot and user_addr not in uio.session.user_colors:
                    uio.session.user_colors[user_addr] = port_manager.os._get_next_color(uio)
        elif action == "logout":
            if user_addr in port_manager.os.network_users:
                del port_manager.os.network_users[user_addr] # Remove user
            # Remove color for this network user from all local interactive users
            for uio in port_manager.os.users.contexts.values():
                if not uio.session.bot and user_addr in uio.session.user_colors:
                    del uio.session.user_colors[user_addr]
            # Also remove from rooms dict if they were in one
            if user_addr in port_manager.os.network_rooms:
                del port_manager.os.network_rooms[user_addr]
        elif action == "state_update":
            if user_addr in port_manager.os.network_users:
                paused = message.get('paused')
                if paused is not None:
                    port_manager.os.network_users[user_addr]['paused'] = paused

    elif msg_type == "room_update":
        action = message.get("action")
        host = message.get("host")
        room_name = message.get("name")

        if not all([action, host, room_name]):
            return # Malformed message

        # Find all users associated with the host that sent the update
        users_on_host = [
            user_addr for user_addr in port_manager.os.network_users
            if user_addr.endswith(f'.{host}')
        ]

        if action == "open":
            for user_addr in users_on_host:
                port_manager.os.network_rooms[user_addr] = room_name
        elif action == "close":
            for user_addr in users_on_host:
                if user_addr in port_manager.os.network_rooms:
                    del port_manager.os.network_rooms[user_addr]

    elif msg_type == "state_sync":
        # This handles the initial sync of users and room state from a new peer
        host = message.get("host")
        users = message.get("users", [])
        room_info = message.get("room", {})

        if not host: # users list can be empty, but host is required
            return # Malformed sync message

        # Sync users
        for user in users:
            user_addr = f"{user}.{host}"
            if user_addr not in port_manager.os.network_users:
                port_manager.os.network_users[user_addr] = {} # Add the user

        # Sync room state for those users
        room_name = room_info.get('name')
        if room_name:
            users_on_host = [u_addr for u_addr in port_manager.os.network_users if u_addr.endswith(f'.{host}')]
            for user_addr in users_on_host:
                port_manager.os.network_rooms[user_addr] = room_name

    if port_manager.os.chat:
        await port_manager.os.chat._broadcast_room_state_update()
    await port_manager.broadcast_color_updates()