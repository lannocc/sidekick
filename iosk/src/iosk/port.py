# sk/iosk/port.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import asyncio
import json
import logging
import traceback
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Any, Optional
import shlex
import base64
import os
import posixpath

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from binaryornot.check import is_binary
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


if TYPE_CHECKING:
    from .kernel import IOSK
    from .io import Context

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class Connection:
    """Metadata for an active network connection."""
    websocket: WebSocketServerProtocol
    type: str  # 'peer' or 'client'
    hostname: Optional[str] = None
    username: Optional[str] = None

class PortManager:
    """
    Manages all network communication for an IOSK system, including the
    WebSocket server, connection lifecycle, and message routing.
    """
    COLOR_MAP = {
        'black': '\033[30m', 'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m',
        'blue': '\033[34m', 'magenta': '\033[35m', 'cyan': '\033[36m', 'white': '\033[37m',
        'bright_black': '\033[90m', 'bright_red': '\033[91m', 'bright_green': '\033[92m',
        'bright_yellow': '\033[93m', 'bright_blue': '\033[94m', 'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m', 'bright_white': '\033[97m',
    }
    REVERSE_COLOR_MAP = {v: k for k, v in COLOR_MAP.items()}

    def __init__(self, kernel: "IOSK"):
        self.kernel = kernel
        self.server_task: Optional[asyncio.Task] = None
        self.port: Optional[int] = None
        self.host: Optional[str] = None
        self.active_connections: Dict[WebSocketServerProtocol, Connection] = {}
        self.peers: Dict[str, WebSocketServerProtocol] = {}
        self.routing_table: Dict[str, Dict[str, Any]] = {}
        self._connecting_peers: set[str] = set()
        self.remote_exec_sessions: Dict[str, Dict[str, Any]] = {}
        self.seen_message_ids: set = set()
        self.MESSAGE_ID_CACHE_SIZE = 500
        # --- ADDED for Filesystem Events Proposal ---
        self.active_watchers: Dict[tuple, Observer] = {}
        self.active_tailers: Dict[tuple, asyncio.Task] = {}

    # --------------------------------------------------------------------------
    # Public API (Kernel-Facing)
    # --------------------------------------------------------------------------

    async def start(self, port_num: int) -> bool:
        """Starts the WebSocket server on the given port."""
        if self.server_task:
            await self.kernel.system.error(f"!! port is already open on {self.port}")
            return False

        self.port = port_num
        self.host = "0.0.0.0"
        try:
            server = await websockets.serve(
                self._connection_handler, self.host, self.port
            )
            self.server_task = asyncio.create_task(server.wait_closed())
            log.info(f"IOSK PortManager started on port {self.port}")
            return True
        except Exception as e:
            await self.kernel.system.error(f"!! failed to start port manager: {e}")
            self.port = None
            self.host = None
            return False

    async def stop(self):
        """Gracefully shuts down the network service and all active connections."""
        if not self.server_task:
            return

        log.info("Stopping IOSK PortManager...")
        self.server_task.cancel()

        # Close all active connections
        for ws in list(self.active_connections.keys()):
            await ws.close(1001, "Server shutting down")

        self.active_connections.clear()
        self.peers.clear()
        self.port = None
        self.host = None
        self.server_task = None
        log.info("IOSK PortManager stopped.")

    async def connect_to_peer(self, host_uri: str, target_hostname: Optional[str] = None, via_peer: Optional[str] = None):
        """Establishes an outbound connection to another IOSK system."""

        # This function launches a background task to handle the full
        # connection and handshake lifecycle for an outbound connection.
        async def _outbound_connect_and_manage():
            websocket = None
            peer_host_from_uri = None
            try:
                # Simple parse of ws://host:port to get 'host' for tracking
                peer_host_from_uri = host_uri.split('//')[1].split(':')[0]
                # Use target_hostname if provided, otherwise fall back to parsed host
                effective_target_host = target_hostname or peer_host_from_uri

                if effective_target_host in self.peers or effective_target_host in self._connecting_peers:
                    log.info(f"Connection to '{effective_target_host}' is already established or in progress. Skipping.")
                    return

                self._connecting_peers.add(effective_target_host)

                websocket = await websockets.connect(host_uri)

                # Get current room info to include in handshake
                room_info = {}
                if self.kernel.chat and self.kernel.chat.active_room:
                    room_info['name'] = self.kernel.chat.active_room
                    room_info['topic'] = self.kernel.chat.room_topic

                # MODIFIED: Send our handshake with current user and room list
                handshake_payload = {
                    "type": "handshake",
                    "id": "peer",
                    "hostname": self.kernel.hostname,
                    "users": list(self.kernel.users.keys()),
                    "room": room_info
                }
                await websocket.send(json.dumps(handshake_payload))

                # Before state update, capture current network state for diffing
                old_network_users = set(self.kernel.network_users.keys())

                # 2. Wait for the server's acknowledgement
                ack_str = await websocket.recv()
                ack_message = json.loads(ack_str)

                if not (ack_message.get("type") == "handshake_ack" and ack_message.get("status") == "ok"):
                    reason = ack_message.get("reason", "unknown error")
                    await self.kernel.system.error(f"!! peer handshake failed: {reason}")
                    await websocket.close()
                    return

                peer_hostname = ack_message.get("hostname")
                if not peer_hostname:
                    await self.kernel.system.error("!! peer handshake failed: ACK missing hostname")
                    await websocket.close()
                    return

                # After handshake, we have the canonical hostname. Check if we're already connected.
                if peer_hostname in self.peers:
                    # This handles user-initiated connections via IP/alias when already connected via canonical name.
                    if not via_peer: # Only print for user-initiated commands
                        await self.kernel.system.print(f":: Already connected to peer '{peer_hostname}'.")
                    await websocket.close(1000, "Redundant connection")
                    return

                if peer_hostname == self.kernel.hostname:
                    reason = f"Cannot connect to self: remote host has same name '{self.kernel.hostname}'."
                    await self.kernel.system.error(f"!! {reason}")
                    await websocket.close()
                    return

                # The 'peers' key now contains a list of dictionaries with hostname and address.
                remote_peers = ack_message.get("peers", [])

                # Extract just the hostnames for the conflict check.
                remote_peer_hostnames = [p.get('hostname') for p in remote_peers if p.get('hostname')]

                if self.kernel.hostname in remote_peer_hostnames:
                    reason = f"Hostname conflict: remote mesh already contains a peer named '{self.kernel.hostname}'."
                    await self.kernel.system.error(f"!! Peer connection aborted: {reason}")
                    await websocket.close()
                    return

                # --- Proactive Mesh Connection (Meshing Proposal Phase 2) ---
                if remote_peers:
                    log.info(f"Received {len(remote_peers)} additional peer(s) from {peer_hostname}. Proactively checking for new connections...")
                    for peer_info in remote_peers:
                        new_peer_host = peer_info.get('hostname')
                        new_peer_addr = peer_info.get('address')

                        if not new_peer_host or not new_peer_addr:
                            log.warning(f"Skipping malformed peer info received from {peer_hostname}: {peer_info}")
                            continue

                        # 1. Don't connect to self.
                        if new_peer_host == self.kernel.hostname:
                            continue

                        # 2. Don't connect if already connected or a connection is in progress.
                        if new_peer_host in self.peers or new_peer_host in self._connecting_peers:
                            continue

                        # 3. It's a new peer, attempt to connect in the background.
                        log.info(f"Proactively attempting to connect to new mesh peer '{new_peer_host}' at {new_peer_addr}")
                        await self.connect_to_peer(f"ws://{new_peer_addr}", target_hostname=new_peer_host, via_peer=peer_hostname)

                # Prioritize full mesh state sync if available.
                mesh_state = ack_message.get("mesh_state")
                if mesh_state:
                    log.info(f"Received full mesh state from {peer_hostname}. Syncing...")
                    self.kernel.network_users = mesh_state.get("users", {})
                    self.kernel.network_rooms = mesh_state.get("rooms", {})
                else:
                    # Fallback for older peers: process only the peer's local state.
                    log.warning(f"Peer {peer_hostname} did not provide full mesh state. Performing partial sync.")
                    await self._process_network_state_update({
                        "type": "state_sync",
                        "host": peer_hostname,
                        "users": ack_message.get("users", []),
                        "room": ack_message.get("room", {})
                    })

                # 3. Handshake successful, set up connection metadata and state
                conn_meta = Connection(websocket=websocket, type='peer', hostname=peer_hostname)
                self.peers[peer_hostname] = websocket
                self.active_connections[websocket] = conn_meta
                self.routing_table[peer_hostname] = {
                    'type': 'direct',
                    'websocket': websocket
                }
                log.info(f"Handshake successful with peer: {conn_meta}")

                # Announce connection to local system log
                await self.kernel.system.print(f":: host '{self.kernel.hostname}' connected to '{peer_hostname}'")

                # --- GOSSIP LOGIC ---
                await self._gossip_state_after_connection(
                    new_peer_hostname=peer_hostname,
                    new_peer_ws=websocket,
                    old_network_users=old_network_users,
                    newly_learned_users_list=ack_message.get("users", [])
                )

                # MESHING PROPAGATION for topology
                addr_part = host_uri.split('//')[1]
                await self._broadcast_peer_connect(peer_hostname, addr_part)

                # 4. Enter the message loop for the duration of the connection
                await self._message_loop(websocket, conn_meta)

            except (ConnectionClosed, websockets.exceptions.InvalidURI, websockets.exceptions.InvalidHandshake, OSError) as e:
                # MODIFIED: Handle connection failures differently for proactive vs. user-initiated connections
                effective_target_host = target_hostname or peer_host_from_uri
                if via_peer:
                    # This was a proactive, indirect connection attempt that failed.
                    if effective_target_host in self.routing_table:
                        return # Route already exists, do nothing.

                    log.warning(f"Proactive direct connection to '{effective_target_host}' failed: {e}. Establishing indirect route via '{via_peer}'.")
                    self.routing_table[effective_target_host] = {'type': 'indirect', 'via': via_peer}
                    # Announce to the local system that a new (indirect) peer is available.
                    await self.kernel.system.print(f":: host '{effective_target_host}' discovered in mesh (routed via {via_peer})")
                else:
                    # This was a direct, user-initiated `mesh` command that failed. This is an error.
                    await self.kernel.system.error(f"!! failed to connect to peer {host_uri}: {e}")
            except Exception as e:
                # Handle other unexpected errors
                await self.kernel.system.error(f"!! an unexpected error occurred while connecting to peer {host_uri}: {e}")
                log.error(f"Full error for peer connection to {host_uri}: {traceback.format_exc()}")
            finally:
                effective_target_host = target_hostname or peer_host_from_uri
                if effective_target_host and effective_target_host in self._connecting_peers:
                    self._connecting_peers.remove(effective_target_host)
                if websocket:
                    await self._cleanup_and_propagate_disconnect(websocket)

        # The `mesh` command should not block. Run the connection logic in the background.
        asyncio.create_task(_outbound_connect_and_manage())

    async def send_to_client(self, username: str, data: str):
        """Sends a data payload to a specific connected client."""
        await self.send_payload_to_client(username, {"output": data})

    async def send_prompt_to_client(self, username: str, prompt_str: str):
        """Sends a prompt payload to a specific connected client."""
        await self.send_payload_to_client(username, {"prompt": prompt_str})

    async def send_payload_to_client(self, username: str, payload: Dict[str, Any]):
        """Sends a JSON payload to a specific connected client using the SK1 protocol."""
        target_ws: Optional[WebSocketServerProtocol] = None
        for ws, conn_meta in self.active_connections.items():
            if conn_meta.type == 'client' and conn_meta.username == username:
                target_ws = ws
                break

        if not target_ws:
            log.warning(f"send_payload_to_client: Could not find active connection for user '{username}'.")
            return

        message_to_send = f"SK1:{json.dumps(payload)}"
        try:
            await target_ws.send(message_to_send)
        except ConnectionClosed:
            log.info(f"send_payload_to_client: Connection for user '{username}' was already closed.")

    async def broadcast_to_peers(self, message: Dict[str, Any]):
        """Sends a message to all connected IOSK peer systems."""
        if not self.peers:
            return

        payload = json.dumps(message)
        aws = [ws.send(payload) for ws in self.peers.values()]
        await asyncio.gather(*aws, return_exceptions=True)

    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """Sends a message to all connected GUI clients."""
        clients = [ws for ws, conn in self.active_connections.items() if conn.type == 'client']
        if not clients:
            return

        # Use the SK1: protocol wrapper for clients
        payload = f"SK1:{json.dumps(message)}"
        aws = [ws.send(payload) for ws in clients]
        await asyncio.gather(*aws, return_exceptions=True)

    async def broadcast_color_updates(self):
        """Sends each connected client their updated user_colors map."""
        client_usernames = [
            conn.username for conn in self.active_connections.values()
            if conn.type == 'client' and conn.username
        ]

        for username in client_usernames:
            io_context = self.kernel.users.get(username)
            if not io_context:
                continue

            color_map = self._get_color_name_map(io_context)
            payload = {
                'type': 'user_colors_update',
                'colors': color_map
            }
            await self.send_payload_to_client(username, payload)

    async def route_message(self, target_host: str, message: Dict[str, Any]):
        """Sends a targeted message to a specific peer host, forwarding if necessary."""
        # Step 1: Look up the target in the routing table
        route = self.routing_table.get(target_host)

        if not route:
            log.error(f"Cannot route message: no route found for host '{target_host}'.")
            return

        # Step 2: Handle direct vs. indirect routes
        if route['type'] == 'direct':
            websocket = route.get('websocket')
            if not websocket:
                log.error(f"Routing error for direct connection to '{target_host}': websocket object missing.")
                return

            payload = json.dumps(message)
            try:
                await websocket.send(payload)
            except ConnectionClosed:
                log.warning(f"Failed to route message to {target_host}: connection closed.")

        elif route['type'] == 'indirect':
            intermediary_host = route.get('via')
            if not intermediary_host:
                log.error(f"Routing error for indirect connection to '{target_host}': 'via' host missing.")
                return

            # Step 3: Wrap the message in a forward_request
            forward_request = {
                'type': 'forward_request',
                'final_destination': target_host,
                'payload': message
            }

            # Step 4: Recursively call route_message to send to the next hop.
            # This is cleaner than directly accessing the peers dict, as it will handle
            # multi-hop scenarios correctly.
            log.info(f"Forwarding message for '{target_host}' via '{intermediary_host}'")
            await self.route_message(intermediary_host, forward_request)

        else:
            log.error(f"Unknown route type '{route.get('type')}' for host '{target_host}'.")

    async def stream_remote_exec(self, host: str, command_str: str, io: "Context") -> bool:
        """Initiates a remote command execution and streams the output."""
        request_id = str(uuid.uuid4())
        completion_event = asyncio.Event()

        # Store the necessary context for handling the response stream
        self.remote_exec_sessions[request_id] = {
            'io': io,
            'event': completion_event,
            'success': True # Assume success until an error occurs
        }

        # Construct the request payload
        request_payload = {
            'type': 'remote_exec_request',
            'request_id': request_id,
            'command_str': command_str
        }

        # Send the request to the target host
        await self.route_message(host, request_payload)

        # Wait for the completion event, which will be set by the message dispatcher
        try:
            # Add a timeout to prevent waiting forever
            await asyncio.wait_for(completion_event.wait(), timeout=300.0) # 5-minute timeout
        except asyncio.TimeoutError:
            await io.error(f"!! on: command timed out on host '{host}'.")
            self.remote_exec_sessions[request_id]['success'] = False

        # Retrieve final status and clean up
        final_success = self.remote_exec_sessions.get(request_id, {}).get('success', False)
        if request_id in self.remote_exec_sessions:
            del self.remote_exec_sessions[request_id]

        return final_success

    async def disconnect_client(self, username: str):
        """
        Finds and closes the connection for a specific client username.
        Called by the kernel when a network user logs out.
        """
        target_ws: Optional[WebSocketServerProtocol] = None
        for ws, conn_meta in self.active_connections.items():
            if conn_meta.type == 'client' and conn_meta.username == username:
                target_ws = ws
                break

        if target_ws:
            log.info(f"Programmatically disconnecting client '{username}' on server-side logout.")
            # Closing the connection will trigger the cleanup logic in the
            # _connection_handler's finally block.
            await target_ws.close(1000, "User logged out")
        else:
            # This might happen if the connection was already dropped, which is not an error.
            log.warning(f"disconnect_client: Could not find active connection for user '{username}' to disconnect.")

    async def send_private_message_to_client(self, to_user: str, from_user: str, content: str):
        """Sends a structured private message to a specific connected client."""
        payload = {
            "type": "private_message",
            "from": from_user,
            "to": to_user,
            "content": content
        }
        await self.send_payload_to_client(to_user, payload)

    async def broadcast_token_stats_update(self, user_io: "Context"):
        """Broadcasts a bot's token telemetry update to all connected clients."""
        if not user_io.bot: return
        payload = {
            "type": "token_stats_update",
            "user": f"{user_io.user}.{self.kernel.hostname}",
            "stats": user_io.token_stats
        }
        await self.broadcast_to_clients(payload)

    # --------------------------------------------------------------------------
    # Internal Logic and Connection Handling
    # --------------------------------------------------------------------------

    class _ClientUpdateEventHandler(FileSystemEventHandler):
        """Helper class to dispatch watchdog events back to the client."""
        def __init__(self, port_manager, user, watched_path, loop):
            self.pm = port_manager
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
            coro = self.pm.send_payload_to_client(self.user, payload)
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _get_color_name_map(self, user_io: "Context") -> dict:
        """Converts a user's ANSI color map to a map of usernames to color names."""
        if not user_io or not hasattr(user_io, 'user_colors'):
            return {}

        name_map = {}
        for user, ansi_code in user_io.user_colors.items():
            color_name = self.REVERSE_COLOR_MAP.get(ansi_code, 'white')
            name_map[user] = color_name
        return name_map

    async def _connection_handler(self, websocket: WebSocketServerProtocol): #, path: str):
        """Handles the entire lifecycle of a single network connection."""
        connection_metadata = None
        io_context = None
        try:
            connection_metadata, io_context = await self._handshake(websocket)
            if connection_metadata:
                # self.active_connections is now set inside _handshake
                log.info(f"Handshake successful: {connection_metadata}")

                if connection_metadata.type == 'peer':
                    new_peer_host = connection_metadata.hostname
                    addr = websocket.remote_address
                    new_peer_addr = f"{addr[0]}:{addr[1]}"
                    await self._broadcast_peer_connect(new_peer_host, new_peer_addr)
                    await self.kernel.system.print(f":: host '{new_peer_host}' connected to mesh")
                elif connection_metadata.type == 'client':
                    # Now that the connection is registered, run post-login scripts.
                    if io_context:
                        await self.kernel.run_post_login_setup(io_context)

                await self._message_loop(websocket, connection_metadata)
        except ConnectionClosed:
            log.info(f"Connection closed: {websocket}")
        except Exception as e:
            log.error(f"Error in connection handler for {websocket}: {e}")
            await websocket.close(1011, "Internal server error")
        finally:
            await self._cleanup_and_propagate_disconnect(websocket)

    async def _handshake(self, websocket: WebSocketServerProtocol) -> Optional[tuple[Connection, Optional["Context"]]]:
        """Performs handshake. Returns (Connection, io_context) or (None, None)."""
        message_str = await websocket.recv()
        message = json.loads(message_str)

        if message.get("type") != "handshake":
            raise ValueError("Invalid handshake: 'type' is not 'handshake'")

        conn_id = message.get("id")
        if conn_id == "peer":
            hostname = message.get("hostname")
            if not hostname:
                raise ValueError("Invalid peer handshake: missing hostname")

            if hostname == self.kernel.hostname:
                reason = f"Hostname conflict: both systems are named '{hostname}'."
                await self.kernel.system.error(f"!! Peer handshake rejected: {reason}")
                await websocket.send(json.dumps({"type": "handshake_ack", "status": "error", "reason": reason}))
                await websocket.close(1008, reason)  # 1008 is "policy violation"
                return None, None

            if hostname in self.peers:
                reason = f"Hostname '{hostname}' already exists in the mesh."
                await self.kernel.system.error(f"!! Peer handshake rejected: {reason}")
                await websocket.send(json.dumps({"type": "handshake_ack", "status": "error", "reason": reason}))
                await websocket.close(1008, reason)
                return None, None

            # Before state update, capture current network state for diffing
            old_network_users = set(self.kernel.network_users.keys())

            # ADDED: Process incoming user and room list and sync state
            await self._process_network_state_update({
                "type": "state_sync",
                "host": hostname,
                "users": message.get("users", []),
                "room": message.get("room", {})
            })

            # Create the detailed peer list for the handshake acknowledgement.
            peers_for_ack = []
            for peer_name, peer_ws in self.peers.items():
                addr = peer_ws.remote_address
                peers_for_ack.append({
                    'hostname': peer_name,
                    'address': f"{addr[0]}:{addr[1]}"
                })

            self.peers[hostname] = websocket
            self.routing_table[hostname] = {
                'type': 'direct',
                'websocket': websocket
            }

            # Create and register connection metadata BEFORE returning
            conn_meta = Connection(websocket=websocket, type='peer', hostname=hostname)
            self.active_connections[websocket] = conn_meta

            # Get local room info for the ack
            local_room_info = {}
            if self.kernel.chat and self.kernel.chat.active_room:
                local_room_info['name'] = self.kernel.chat.active_room
                local_room_info['topic'] = self.kernel.chat.room_topic

            # Send the handshake acknowledgement with the new detailed peer list.
            await websocket.send(json.dumps({
                "type": "handshake_ack",
                "status": "ok",
                "hostname": self.kernel.hostname,
                "users": list(self.kernel.users.keys()),
                "room": local_room_info,
                "peers": peers_for_ack,
                # This new field contains the full state of the mesh as known by this peer.
                "mesh_state": {
                    "users": self.kernel.network_users,
                    "rooms": self.kernel.network_rooms
                }
            }))

            # --- GOSSIP LOGIC ---
            await self._gossip_state_after_connection(
                new_peer_hostname=hostname,
                new_peer_ws=websocket,
                old_network_users=old_network_users,
                newly_learned_users_list=message.get("users", [])
            )

            return conn_meta, None

        elif conn_id == "client":
            username = message.get("user")
            if not username:
                raise ValueError("Invalid client handshake: missing user")
            # Delegate login to kernel
            io_context = await self.kernel.login_network_user(username, websocket)
            if not io_context:
                await websocket.send(json.dumps({"type": "handshake_ack", "status": "error", "reason": f"Login for user '{username}' failed."}))
                raise ValueError(f"Client login failed for user {username}")

            # Create and register the connection metadata BEFORE sending any state
            conn_meta = Connection(websocket=websocket, type='client', username=username)
            self.active_connections[websocket] = conn_meta

            await websocket.send(json.dumps({"type": "handshake_ack", "status": "ok", "hostname": self.kernel.hostname}))

            # Send initial state info to the new client
            initial_state_payload = {'type': 'state_info'}
            initial_state_payload['hostname'] = self.kernel.hostname
            initial_state_payload['userColors'] = self._get_color_name_map(io_context)
            # Get available rooms, using the user's new io_context
            available_rooms = await self.kernel.get_room_list(io_context)
            initial_state_payload['availableRooms'] = available_rooms
            if self.kernel.chat and self.kernel.chat.active_room:
                # Room is active, send room state
                room = self.kernel.chat

                # MODIFIED: Gather participants as objects with name and is_bot status
                all_participants_map = {} # Use dict to handle duplicates

                # 1. Add local users (without hostname)
                for username in room.local_room_participants:
                    user_io = self.kernel.users.get(username)
                    if user_io:
                        all_participants_map[username] = {
                            'name': username,
                            'is_bot': user_io.bot
                        }

                # 2. Add network users in the same room (with hostname)
                for user_addr, r_name in self.kernel.network_rooms.items():
                    if r_name == room.active_room:
                        user_part, host_part = user_addr.split('.', 1)
                        # Only add if they are not on the local host, as they are already covered.
                        if host_part != self.kernel.hostname:
                            user_info = self.kernel.network_users.get(user_addr, {})
                            all_participants_map[user_addr] = {
                                'name': user_addr,
                                'is_bot': user_info.get('is_bot', False)
                            }

                participants_list = sorted(list(all_participants_map.values()), key=lambda p: p['name'])

                initial_state_payload.update({
                    'roomName': room.active_room,
                    'roomTopic': room.room_topic,
                    'participants': participants_list
                })
            else:
                # No room, send MOTD. The MOTD was selected and cached during login.
                motd_content = getattr(io_context, 'motd_cache', None)
                initial_state_payload['motd'] = motd_content or ''

            # This call will now succeed because the connection is registered
            await self.send_payload_to_client(username, initial_state_payload)

            return conn_meta, io_context

        else:
            raise ValueError(f"Invalid handshake: unknown id '{conn_id}'")

    async def _message_loop(self, websocket: WebSocketServerProtocol, conn_meta: Connection):
        """Continuously receives and dispatches messages from a connection."""
        async for message_str in websocket:
            await self._dispatch_message(websocket, conn_meta, message_str)

    async def _dispatch_message(self, websocket: WebSocketServerProtocol, conn_meta: Connection, message_str: str):
        """Parses and routes a single incoming message based on its type."""
        try:
            # Client messages might be wrapped in the SK1 protocol
            if message_str.startswith("SK1:"):
                message_str = message_str[4:]

            message = json.loads(message_str)
            msg_type = message.get("type")

            if msg_type == "forward_request":
                final_destination = message.get('final_destination')
                payload = message.get('payload')
                if not final_destination or payload is None:
                    log.warning(f"Malformed forward_request received: {message}")
                    return
                # Do not process locally. Unwrap and route it onward.
                await self.route_message(final_destination, payload)

            # --- MESHING PROPAGATION ---
            elif msg_type == "peer_update":
                # MODIFIED: Pass the hostname of the peer that sent this message
                from_peer_hostname = conn_meta.hostname
                await self._handle_peer_update(message, from_peer=from_peer_hostname)

            elif msg_type in ("user_update", "room_update", "room_state_update", "user_colors_update"):
                # 1. Process locally first
                await self._process_network_state_update(message)
                # 2. Forward the update to all other peers
                peers_to_notify = {h: ws for h, ws in self.peers.items() if h != conn_meta.hostname}
                if peers_to_notify:
                    log.info(f"Forwarding {msg_type} from {conn_meta.hostname} to {list(peers_to_notify.keys())}")
                    aws = [ws.send(message_str) for ws in peers_to_notify.values()]
                    await asyncio.gather(*aws, return_exceptions=True)

            elif msg_type == "state_sync":
                await self._process_network_state_update(message)

            elif msg_type == "system_broadcast":
                msg_content = message.get("message")
                if msg_content:
                    await self.kernel.system.print(msg_content)

            elif msg_type == "remote_exec_request":
                # This is a complex handler that streams output back
                await self._handle_remote_exec(websocket, message)

            elif msg_type == "remote_exec_response":
                await self._handle_remote_exec_response(message)

            elif msg_type == "room_message":
                msg_id = message.get("msg_id")
                if msg_id:
                    if msg_id in self.seen_message_ids:
                        return  # Already processed this message, drop it.
                    self.seen_message_ids.add(msg_id)
                    if len(self.seen_message_ids) > self.MESSAGE_ID_CACHE_SIZE:
                        self.seen_message_ids.pop() # Evict an old ID

                # 1. Process the message locally
                await self.kernel.chat.handle_network_message(message)

                # 2. Forward the message to all other connected peers
                from_peer_hostname = conn_meta.hostname
                peers_to_forward = {h: ws for h, ws in self.peers.items() if h != from_peer_hostname}
                if peers_to_forward:
                    log.info(f"Forwarding room message from '{from_peer_hostname}' to {list(peers_to_forward.keys())}")
                    aws = [ws.send(message_str) for ws in peers_to_forward.values()]
                    await asyncio.gather(*aws, return_exceptions=True)

            elif msg_type == "direct_message":
                await self.kernel.chat.handle_network_message(message)

            elif msg_type == "client_input":
                if conn_meta.type == 'client' and conn_meta.username:
                    await self.kernel.handle_client_input(conn_meta.username, message.get("data", ""))
                else:
                    log.warning("Received client_input from non-client connection.")

            elif msg_type == "room_action":
                if conn_meta.type == 'client' and conn_meta.username:
                    action = message.get("action")
                    if action == "join":
                        room_name = message.get("roomName")
                        if room_name:
                            command = f"$ room {shlex.quote(room_name)}"
                            await self.kernel.handle_client_input(conn_meta.username, command + '\n')
                    elif action == "close":
                        command = "$ clroom"
                        await self.kernel.handle_client_input(conn_meta.username, command + '\n')
                else:
                    log.warning("Received room_action from non-client connection.")

            elif msg_type == "exec_command":
                if conn_meta.type == 'client' and conn_meta.username:
                    io_context = self.kernel.users.get(conn_meta.username)
                    if io_context:
                        await self._handle_exec_command(websocket, io_context, message)
                else:
                    log.warning("Received exec_command from non-client connection.")

            elif msg_type == "fs_list":
                if conn_meta.type == 'client' and conn_meta.username:
                    path = message.get("path", "/")
                    requesterId = message.get("requesterId")
                    recursive = message.get("recursive", False)
                    io_context = self.kernel.users.get(conn_meta.username)
                    if io_context:
                        await self._handle_fs_list(websocket, io_context, path, requesterId, recursive)
                else:
                    log.warning("Received fs_list from non-client connection.")

            elif msg_type == "fs_read":
                if conn_meta.type == 'client' and conn_meta.username:
                    io_context = self.kernel.users.get(conn_meta.username)
                    if io_context:
                        await self._handle_fs_read(websocket, io_context, message)
                else:
                    log.warning("Received fs_read from non-client or malformed request.")

            elif msg_type == "fs_watch_start":
                if conn_meta.type == 'client' and conn_meta.username:
                    path = message.get("path")
                    io_context = self.kernel.users.get(conn_meta.username)
                    if io_context and path:
                        await self._handle_fs_watch_start(websocket, io_context, path)

            elif msg_type == "fs_watch_stop":
                if conn_meta.type == 'client':
                    path = message.get("path")
                    if path:
                        await self._handle_fs_watch_stop(websocket, path)

            elif msg_type == "fs_tail_start":
                if conn_meta.type == 'client' and conn_meta.username:
                    path = message.get("path")
                    io_context = self.kernel.users.get(conn_meta.username)
                    if io_context and path:
                        await self._handle_fs_tail_start(websocket, io_context, path)

            elif msg_type == "fs_tail_stop":
                if conn_meta.type == 'client':
                    path = message.get("path")
                    if path:
                        await self._handle_fs_tail_stop(websocket, path)

            else:
                log.warning(f"Received unknown message type: {msg_type}")

        except json.JSONDecodeError:
            log.error("Failed to decode JSON message.")
        except Exception:
            log.error(f"Error dispatching message: {traceback.format_exc()}")

    async def _handle_exec_command(self, websocket: WebSocketServerProtocol, io_context: "Context", message: Dict[str, Any]):
        """Handles a transient command execution request from a client (for Watch)."""
        command_str = message.get("command_str")
        pwd = message.get("pwd")
        requesterId = message.get("requesterId")

        if not all([command_str, pwd, requesterId is not None]):
            log.warning("Malformed exec_command request received.")
            return

        response = {"type": "exec_command_response", "requesterId": requesterId}
        try:
            output = await self.kernel.execute_transient_command(io_context, command_str, pwd)
            response["output"] = output
        except Exception as e:
            log.error(f"Error during exec_command for {io_context.user} on command '{command_str}': {e}")
            response["error"] = f"An internal server error occurred during execution: {e}"

        await self.send_payload_to_client(io_context.user, response)

    async def _handle_fs_list(self, websocket: WebSocketServerProtocol, io_context: "Context", path: str, requesterId: Optional[Any], recursive: bool = False):
        """Handles a file system list request from a client."""
        response = {"type": "fs_list_response", "path": path}
        if requesterId is not None:
            response["requesterId"] = requesterId
        try:
            listing = await self.kernel.list_dir(io_context, path, recursive=recursive)
            response["listing"] = listing
        except FileNotFoundError as e:
            response["error"] = str(e)
        except NotADirectoryError as e:
            response["error"] = str(e)
        except Exception as e:
            log.error(f"Error during fs_list for {io_context.user} at '{path}': {e}")
            response["error"] = "An internal server error occurred."

        await self.send_payload_to_client(io_context.user, response)

    async def _handle_fs_read(self, websocket: WebSocketServerProtocol, io_context: "Context", message: Dict[str, Any]):
        """Handles a file read request from a client, now supporting chunking."""
        path = message.get("path")
        requesterId = message.get("requesterId")
        offset = message.get("offset", 0)
        length = message.get("length", -1)

        if path is None or requesterId is None:
            log.warning("Malformed fs_read request received.")
            return

        response = {
            "type": "fs_read_response",
            "path": path,
            "requesterId": requesterId,
            "offset": offset,
            "length": length,
        }

        try:
            host_path = self.kernel.box(path, io_context=io_context)

            if not os.path.exists(host_path):
                response["error"] = f"path not found: {path}"
            elif not os.path.isfile(host_path):
                response["error"] = f"not a file: {path}"
            else:
                total_size = os.path.getsize(host_path)
                response["total_size"] = total_size

                with open(host_path, 'rb') as f:
                    f.seek(offset)
                    content_bytes = f.read(length)

                is_binary_file = is_binary(host_path)
                response["content_b64"] = base64.b64encode(content_bytes).decode('ascii')
                response["is_binary"] = is_binary_file
        except Exception as e:
            log.error(f"Error during fs_read for {io_context.user} at '{path}': {e}")
            response["error"] = "An internal server error occurred."

        await self.send_payload_to_client(io_context.user, response)

    async def _handle_fs_watch_start(self, websocket: WebSocketServerProtocol, io_context: "Context", path: str):
        key = (websocket, path)
        if key in self.active_watchers:
            log.warning(f"Watcher already active for {io_context.user} on '{path}'.")
            return

        host_path = self.kernel.box(path, io_context=io_context)
        if not os.path.isdir(host_path):
            log.error(f"Cannot watch '{path}': not a valid directory for user '{io_context.user}'.")
            return

        loop = asyncio.get_running_loop()
        event_handler = self._ClientUpdateEventHandler(self, io_context.user, path, loop)

        observer = Observer()
        observer.schedule(event_handler, host_path, recursive=False)
        observer.start()

        self.active_watchers[key] = observer
        log.info(f"Started watching '{path}' for user '{io_context.user}'.")

    async def _handle_fs_watch_stop(self, websocket: WebSocketServerProtocol, path: str):
        key = (websocket, path)
        observer = self.active_watchers.pop(key, None)
        if observer:
            observer.stop()
            observer.join()
            log.info(f"Stopped watching '{path}' for connection.")
        else:
            log.warning(f"Could not find active watcher for '{path}' to stop.")

    async def _handle_fs_tail_start(self, websocket: WebSocketServerProtocol, io_context: "Context", path: str):
        key = (websocket, path)
        if key in self.active_tailers:
            log.warning(f"Tailing already active for {io_context.user} on '{path}'.")
            return

        host_path = self.kernel.box(path, io_context=io_context)
        if not os.path.isfile(host_path):
            log.error(f"Cannot tail '{path}': not a valid file for user '{io_context.user}'.")
            return

        task = asyncio.create_task(self._tail_file_task(websocket, io_context, path))
        self.active_tailers[key] = task
        log.info(f"Started tailing '{path}' for user '{io_context.user}'.")

    async def _handle_fs_tail_stop(self, websocket: WebSocketServerProtocol, path: str):
        key = (websocket, path)
        task = self.active_tailers.pop(key, None)
        if task:
            task.cancel()
            log.info(f"Stopped tailing '{path}' for connection.")
        else:
            log.warning(f"Could not find active tailing task for '{path}' to stop.")

    async def _tail_file_task(self, websocket: WebSocketServerProtocol, io_context: "Context", path: str):
        try:
            host_path = self.kernel.box(path, io_context=io_context)
            with open(host_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        await asyncio.sleep(0.5)
                        continue

                    payload = {
                        "type": "fs_tail_update",
                        "path": path,
                        "data": line
                    }
                    await self.send_payload_to_client(io_context.user, payload)
        except asyncio.CancelledError:
            pass # Task cancellation is the normal way to stop tailing.
        except Exception as e:
            log.error(f"Error in tailing task for '{path}': {e}")
        finally:
            log.info(f"Tailing task for '{path}' for user '{io_context.user}' has ended.")

    async def _handle_remote_exec(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Handles a remote execution request and streams output back."""
        command_str = message.get('command_str', '')
        request_id = message.get('request_id')
        if not command_str or not request_id:
            return

        exec_io = self.kernel.system.fork()

        # Custom writer to stream stdout back over the websocket
        class RemoteWriter:
            def __init__(self, ws, stream_name, req_id):
                self.ws = ws
                self.stream_name = stream_name
                self.req_id = req_id

            def write(self, data: str):
                response = {
                    "type": "remote_exec_response",
                    "request_id": self.req_id,
                    "stream": self.stream_name,
                    "data": data,
                    "is_complete": False
                }
                asyncio.create_task(self.ws.send(json.dumps(response)))

            def flush(self):
                pass

        exec_io.stdout = RemoteWriter(websocket, 'stdout', request_id)
        # TODO: A proper solution would also capture stderr

        try:
            await self.kernel.call(exec_io, command_str)
        finally:
            # Signal completion
            response = {
                "type": "remote_exec_response",
                "request_id": request_id,
                "stream": "status",
                "data": "",
                "is_complete": True
            }
            await websocket.send(json.dumps(response))

    async def _handle_remote_exec_response(self, message: Dict[str, Any]):
        """Handles a streamed response from a remote execution command."""
        request_id = message.get('request_id')
        if not request_id or request_id not in self.remote_exec_sessions:
            # This could be a response for a timed-out request, or malformed.
            log.warning(f"Received remote_exec_response for unknown or stale request_id: {request_id}")
            return

        session = self.remote_exec_sessions[request_id]
        io_context = session['io']
        completion_event = session['event']

        data = message.get('data', '')
        stream = message.get('stream')
        is_complete = message.get('is_complete', False)

        if stream == 'stdout' and data:
            # Use io.output to avoid extra formatting/logging from io.print
            await io_context.output(data)
        elif stream == 'stderr' and data: # Future-proofing
            await io_context.error(data)

        # Check for completion signal
        if is_complete:
            completion_event.set()

    async def _process_network_state_update(self, message: dict):
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
                self.kernel.network_users[user_addr] = {'is_bot': is_bot} # Add user
                # Assign color for this network user to all local interactive users
                for uio in self.kernel.users.values():
                    if not uio.bot and user_addr not in uio.user_colors:
                        uio.user_colors[user_addr] = self.kernel._get_next_color(uio)
            elif action == "logout":
                if user_addr in self.kernel.network_users:
                    del self.kernel.network_users[user_addr] # Remove user
                # Remove color for this network user from all local interactive users
                for uio in self.kernel.users.values():
                    if not uio.bot and user_addr in uio.user_colors:
                        del uio.user_colors[user_addr]
                # Also remove from rooms dict if they were in one
                if user_addr in self.kernel.network_rooms:
                    del self.kernel.network_rooms[user_addr]

        elif msg_type == "room_update":
            action = message.get("action")
            host = message.get("host")
            room_name = message.get("name")

            if not all([action, host, room_name]):
                return # Malformed message

            # Find all users associated with the host that sent the update
            users_on_host = [
                user_addr for user_addr in self.kernel.network_users
                if user_addr.endswith(f'.{host}')
            ]

            if action == "open":
                for user_addr in users_on_host:
                    self.kernel.network_rooms[user_addr] = room_name
            elif action == "close":
                for user_addr in users_on_host:
                    if user_addr in self.kernel.network_rooms:
                        del self.kernel.network_rooms[user_addr]

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
                if user_addr not in self.kernel.network_users:
                    self.kernel.network_users[user_addr] = {} # Add the user

            # Sync room state for those users
            room_name = room_info.get('name')
            if room_name:
                users_on_host = [u_addr for u_addr in self.kernel.network_users if u_addr.endswith(f'.{host}')]
                for user_addr in users_on_host:
                    self.kernel.network_rooms[user_addr] = room_name

        if self.kernel.chat:
            await self.kernel.chat._broadcast_room_state_update()
        await self.broadcast_color_updates()

    # --------------------------------------------------------------------------
    # MESHING-SPECIFIC METHODS
    # --------------------------------------------------------------------------
    async def _gossip_state_after_connection(self, new_peer_hostname, new_peer_ws, old_network_users, newly_learned_users_list):
        """Symmetrically exchanges user state with a new peer to sync the mesh."""
        # 1. Tell our other peers about the users from the new peer.
        other_peers = {h: ws for h, ws in self.peers.items() if h != new_peer_hostname}
        if other_peers and newly_learned_users_list:
            log.info(f"Gossiping about {new_peer_hostname}'s {len(newly_learned_users_list)} user(s) to {len(other_peers)} other peer(s).")
            for user in newly_learned_users_list:
                update_msg = {"type": "user_update", "action": "login", "user": user, "host": new_peer_hostname}
                payload = json.dumps(update_msg)
                aws = [ws.send(payload) for ws in other_peers.values()]
                await asyncio.gather(*aws, return_exceptions=True)

        # 2. Tell the new peer about all the users we knew about *before* this connection.
        if old_network_users:
            log.info(f"Gossiping about {len(old_network_users)} existing user(s) to new peer '{new_peer_hostname}'.")
            for user_addr in old_network_users:
                user, host = user_addr.split('.', 1)
                update_msg = {"type": "user_update", "action": "login", "user": user, "host": host}
                try:
                    await new_peer_ws.send(json.dumps(update_msg))
                except ConnectionClosed:
                    log.warning(f"Could not gossip to new peer '{new_peer_hostname}', connection closed.")
                    break

    async def _broadcast_peer_connect(self, new_peer_hostname: str, new_peer_address: str):
        """Broadcasts a 'peer_update' message to all other peers about a new connection."""
        # We broadcast to all peers *except* the one we just connected to.
        peers_to_notify = {
            host: ws for host, ws in self.peers.items() if host != new_peer_hostname
        }

        if not peers_to_notify:
            return # No other peers to notify.

        message = {
            'type': 'peer_update',
            'action': 'connect',
            'peer_info': {
                'hostname': new_peer_hostname,
                'address': new_peer_address
            }
        }
        payload = json.dumps(message)

        log.info(f"Broadcasting connection of '{new_peer_hostname}' to {len(peers_to_notify)} other peer(s).")
        aws = [ws.send(payload) for ws in peers_to_notify.values()]
        await asyncio.gather(*aws, return_exceptions=True)

    async def _handle_peer_update(self, message: Dict[str, Any], from_peer: Optional[str] = None):
        """Handles a peer_update message for both connecting and disconnecting peers."""
        action = message.get('action')
        peer_info = message.get('peer_info')
        if not all([action, peer_info]):
            log.warning(f"Malformed peer_update received: {message}")
            return

        hostname = peer_info.get('hostname')
        if not hostname:
            log.warning(f"Malformed peer_info in peer_update (missing hostname): {peer_info}")
            return

        if action == 'connect':
            address = peer_info.get('address')
            if not address:
                log.warning(f"Malformed peer_info in 'connect' peer_update (missing address): {peer_info}")
                return

            # Proactively try to form a direct connection.
            if hostname == self.kernel.hostname:
                return # It's us.
            if hostname in self.peers or hostname in self._connecting_peers:
                return # Already connected or trying.

            log.info(f"Peer Update: Proactively connecting to new peer '{hostname}' at {address}")
            await self.connect_to_peer(f"ws://{address}", target_hostname=hostname, via_peer=from_peer)

        elif action == 'disconnect':
            log.info(f"Processing disconnect notification for peer '{hostname}' from '{from_peer}'.")

            # If we don't know this host, we're done.
            if hostname not in self.routing_table and hostname not in self.peers:
                return

            # If we have a direct connection, let the local websocket closure handle it.
            # The local connection state is the source of truth for direct peers.
            if hostname in self.peers:
                return

            # This peer is known via an indirect route. Clean it up.
            if hostname in self.routing_table:
                del self.routing_table[hostname]

            # Also clean up users from that host.
            users_to_remove = [user_addr for user_addr in self.kernel.network_users if user_addr.endswith(f'.{hostname}')]
            for user_addr in users_to_remove:
                del self.kernel.network_users[user_addr]
                if user_addr in self.kernel.network_rooms:
                    del self.kernel.network_rooms[user_addr]
            if users_to_remove:
                log.info(f"Cleaned up {len(users_to_remove)} users from disconnected host '{hostname}' via propagation.")

            await self.kernel.system.print(f":: host '{hostname}' disconnected from mesh (propagated via {from_peer})")

            # Forward the disconnect message to our other peers.
            # Don't send it back to the peer who told us.
            peers_to_notify = {h: ws for h, ws in self.peers.items() if h != from_peer}
            if peers_to_notify:
                log.info(f"Forwarding disconnect notification for '{hostname}' to {len(peers_to_notify)} other peer(s).")
                payload = json.dumps(message)
                aws = [ws.send(payload) for ws in peers_to_notify.values()]
                await asyncio.gather(*aws, return_exceptions=True)

    async def _broadcast_peer_disconnect(self, disconnected_hostname: str):
        """Broadcasts a 'peer_update' with action 'disconnect' to all remaining peers."""
        if not self.peers:
            return

        message = {
            'type': 'peer_update',
            'action': 'disconnect',
            'peer_info': {
                'hostname': disconnected_hostname
            }
        }
        payload = json.dumps(message)
        log.info(f"Broadcasting disconnection of '{disconnected_hostname}' to {len(self.peers)} remaining peer(s).")
        aws = [ws.send(payload) for ws in self.peers.values()]
        await asyncio.gather(*aws, return_exceptions=True)

    async def _cleanup_and_propagate_disconnect(self, websocket: WebSocketServerProtocol):
        """
        Handles the cleanup of a disconnected peer and propagates the event to the mesh.
        This is the single source of truth for handling peer disconnections.
        """
        if websocket not in self.active_connections:
            return

        # --- ADDED for Filesystem Events Proposal ---
        # Clean up any watchers associated with this websocket
        for (ws, path), observer in list(self.active_watchers.items()):
            if ws == websocket:
                observer.stop()
                observer.join()
                del self.active_watchers[(ws, path)]
                log.info(f"Cleaned up watcher for '{path}' on disconnect.")

        # Clean up any tailers associated with this websocket
        for (ws, path), task in list(self.active_tailers.items()):
            if ws == websocket:
                task.cancel()
                del self.active_tailers[(ws, path)]
                log.info(f"Cleaned up tailer for '{path}' on disconnect.")
        
        conn_data = self.active_connections.pop(websocket)

        if conn_data.type == 'client' and conn_data.username:
            await self.kernel.logout_network_user(conn_data.username)
            log.info(f"Client '{conn_data.username}' disconnected.")
            return

        if conn_data.type == 'peer' and conn_data.hostname:
            disconnected_host = conn_data.hostname
            # 1. Clean up local peer state
            if disconnected_host in self.peers:
                del self.peers[disconnected_host]
            if disconnected_host in self.routing_table:
                del self.routing_table[disconnected_host]

            log.info(f"Peer '{disconnected_host}' disconnected.")
            await self.kernel.system.print(f":: host '{disconnected_host}' disconnected from mesh")

            # 2. Clean up users from that host
            users_to_remove = [user_addr for user_addr in self.kernel.network_users if user_addr.endswith(f'.{disconnected_host}')]
            for user_addr in users_to_remove:
                del self.kernel.network_users[user_addr]
                if user_addr in self.kernel.network_rooms:
                    del self.kernel.network_rooms[user_addr]
            if users_to_remove:
                log.info(f"Cleaned up {len(users_to_remove)} users from disconnected host '{disconnected_host}'")

            # 3. Propagate the disconnection to remaining peers
            await self._broadcast_peer_disconnect(disconnected_host)

