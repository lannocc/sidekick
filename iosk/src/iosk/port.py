# src/iosk/port.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import asyncio
import json
import logging
import traceback
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Any, Optional

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

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
    def __init__(self, kernel: "IOSK"):
        self.kernel = kernel
        self.server_task: Optional[asyncio.Task] = None
        self.port: Optional[int] = None
        self.active_connections: Dict[WebSocketServerProtocol, Connection] = {}
        self.peers: Dict[str, WebSocketServerProtocol] = {}

    # --------------------------------------------------------------------------
    # Public API (Kernel-Facing)
    # --------------------------------------------------------------------------

    async def start(self, port_num: int) -> bool:
        """Starts the WebSocket server on the given port."""
        if self.server_task:
            await self.kernel.system.error(f"!! port is already open on {self.port}")
            return False

        self.port = port_num
        try:
            server = await websockets.serve(
                self._connection_handler, "0.0.0.0", self.port
            )
            self.server_task = asyncio.create_task(server.wait_closed())
            log.info(f"IOSK PortManager started on port {self.port}")
            return True
        except Exception as e:
            await self.kernel.system.error(f"!! failed to start port manager: {e}")
            self.port = None
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
        self.server_task = None
        log.info("IOSK PortManager stopped.")

    async def connect_to_peer(self, host_uri: str):
        """Establishes an outbound connection to another IOSK system."""
        
        # This function launches a background task to handle the full
        # connection and handshake lifecycle for an outbound connection.
        async def _outbound_connect_and_manage():
            websocket = None
            try:
                websocket = await websockets.connect(host_uri)
                
                # MODIFIED: Send our handshake with current user list
                handshake_payload = {
                    "type": "handshake",
                    "id": "peer",
                    "hostname": self.kernel.hostname,
                    "users": list(self.kernel.users.keys()) # ADDED: Send our user list
                }
                await websocket.send(json.dumps(handshake_payload))

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

                if peer_hostname == self.kernel.hostname:
                    reason = f"Cannot connect to self: remote host has same name '{self.kernel.hostname}'."
                    await self.kernel.system.error(f"!! {reason}")
                    await websocket.close()
                    return

                remote_peers = ack_message.get("peers", [])
                if self.kernel.hostname in remote_peers:
                    reason = f"Hostname conflict: remote mesh already contains a peer named '{self.kernel.hostname}'."
                    await self.kernel.system.error(f"!! Peer connection aborted: {reason}")
                    await websocket.close()
                    return
                
                # ADDED: Process the user list from the peer
                peer_users = ack_message.get("users", [])
                await self.kernel.update_network_state({
                    "type": "state_sync",
                    "host": peer_hostname,
                    "users": peer_users
                })
                
                # 3. Handshake successful, set up connection metadata and state
                conn_meta = Connection(websocket=websocket, type='peer', hostname=peer_hostname)
                self.peers[peer_hostname] = websocket
                self.active_connections[websocket] = conn_meta
                log.info(f"Handshake successful with peer: {conn_meta}")

                # 4. Enter the message loop for the duration of the connection
                await self._message_loop(websocket, conn_meta)

            except (ConnectionClosed, websockets.exceptions.InvalidURI, websockets.exceptions.InvalidHandshake, OSError) as e:
                # Handle expected connection/handshake errors without a big traceback
                await self.kernel.system.error(f"!! failed to connect to peer {host_uri}: {e}")
            except Exception as e:
                # Handle other unexpected errors
                await self.kernel.system.error(f"!! an unexpected error occurred while connecting to peer {host_uri}: {e}")
                log.error(f"Full error for peer connection to {host_uri}: {traceback.format_exc()}")
            finally:
                # This cleanup logic is crucial for outbound connections, mirroring the
                # server-side handler's finally block.
                if websocket and websocket in self.active_connections:
                    conn_data = self.active_connections.pop(websocket)
                    if conn_data.type == 'peer' and conn_data.hostname in self.peers:
                        del self.peers[conn_data.hostname]
                        log.info(f"Peer '{conn_data.hostname}' disconnected.")
                elif websocket: # and not websocket.closed:
                    # Ensure the socket is closed if it was opened but never fully registered
                    await websocket.close()

        # The `mesh` command should not block. Run the connection logic in the background.
        asyncio.create_task(_outbound_connect_and_manage())

    async def broadcast_to_peers(self, message: Dict[str, Any]):
        """Sends a message to all connected IOSK peer systems."""
        if not self.peers:
            return
        
        payload = json.dumps(message)
        aws = [ws.send(payload) for ws in self.peers.values()]
        await asyncio.gather(*aws, return_exceptions=True)

    async def route_message(self, target_host: str, message: Dict[str, Any]):
        """Sends a targeted message to a specific peer host."""
        if target_host in self.peers:
            websocket = self.peers[target_host]
            payload = json.dumps(message)
            try:
                await websocket.send(payload)
            except ConnectionClosed:
                log.warning(f"Failed to route message to {target_host}: connection closed.")
        else:
            log.error(f"Cannot route message: peer '{target_host}' not found.")

    # --------------------------------------------------------------------------
    # Internal Logic and Connection Handling
    # --------------------------------------------------------------------------

    async def _connection_handler(self, websocket: WebSocketServerProtocol): #, path: str):
        """Handles the entire lifecycle of a single network connection."""
        connection_metadata = None
        try:
            connection_metadata = await self._handshake(websocket)
            if connection_metadata:
                self.active_connections[websocket] = connection_metadata
                log.info(f"Handshake successful: {connection_metadata}")
                await self._message_loop(websocket, connection_metadata)
        except ConnectionClosed:
            #log.info(f"Connection closed: {path}")
            log.info(f"Connection closed: {websocket}")
        except Exception as e:
            #log.error(f"Error in connection handler for {path}: {e}")
            log.error(f"Error in connection handler for {websocket}: {e}")
            await websocket.close(1011, "Internal server error")
        finally:
            if websocket in self.active_connections:
                conn_data = self.active_connections.pop(websocket)
                if conn_data.type == 'peer' and conn_data.hostname in self.peers:
                    del self.peers[conn_data.hostname]
                    log.info(f"Peer '{conn_data.hostname}' disconnected.")
                elif conn_data.type == 'client' and conn_data.username:
                    await self.kernel.logout_network_user(conn_data.username)
                    log.info(f"Client '{conn_data.username}' disconnected.")

    async def _handshake(self, websocket: WebSocketServerProtocol) -> Optional[Connection]:
        """Performs the initial handshake to identify the connection type."""
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
                return None

            if hostname in self.peers:
                reason = f"Hostname '{hostname}' already exists in the mesh."
                await self.kernel.system.error(f"!! Peer handshake rejected: {reason}")
                await websocket.send(json.dumps({"type": "handshake_ack", "status": "error", "reason": reason}))
                await websocket.close(1008, reason)
                return None

            # ADDED: Process incoming user list and sync state
            peer_users = message.get("users", [])
            await self.kernel.update_network_state({
                "type": "state_sync",
                "host": hostname,
                "users": peer_users
            })

            self.peers[hostname] = websocket
            
            # MODIFIED: Send back our user list in the ack
            await websocket.send(json.dumps({
                "type": "handshake_ack", 
                "status": "ok", 
                "hostname": self.kernel.hostname,
                "users": list(self.kernel.users.keys()), # ADDED
                "peers": list(self.peers.keys())
            }))
            return Connection(websocket=websocket, type='peer', hostname=hostname)
        
        elif conn_id == "client":
            username = message.get("user")
            if not username:
                raise ValueError("Invalid client handshake: missing user")
            # Delegate login to kernel
            io_context = await self.kernel.login_network_user(username, websocket)
            if not io_context:
                await websocket.send(json.dumps({"type": "handshake_ack", "status": "error", "reason": f"Login for user '{username}' failed."}))
                raise ValueError(f"Client login failed for user {username}")
            
            await websocket.send(json.dumps({"type": "handshake_ack", "status": "ok", "hostname": self.kernel.hostname}))
            return Connection(websocket=websocket, type='client', username=username)
        
        else:
            raise ValueError(f"Invalid handshake: unknown id '{conn_id}'")

    async def _message_loop(self, websocket: WebSocketServerProtocol, conn_meta: Connection):
        """Continuously receives and dispatches messages from a connection."""
        async for message_str in websocket:
            await self._dispatch_message(websocket, conn_meta, message_str)

    async def _dispatch_message(self, websocket: WebSocketServerProtocol, conn_meta: Connection, message_str: str):
        """Parses and routes a single incoming message based on its type."""
        try:
            message = json.loads(message_str)
            msg_type = message.get("type")

            # MODIFIED: Handle state updates by calling the new kernel method
            if msg_type in ("user_update", "room_update", "state_sync"):
                await self.kernel.update_network_state(message)

            elif msg_type == "remote_exec_request":
                # This is a complex handler that streams output back
                await self._handle_remote_exec(websocket, message)

            elif msg_type in ("direct_message", "room_message"):
                await self.kernel.chat.handle_network_message(message)

            elif msg_type == "client_input":
                if conn_meta.type == 'client' and conn_meta.username:
                    await self.kernel.handle_client_input(conn_meta.username, message.get("data", ""))
                else:
                    log.warning("Received client_input from non-client connection.")
            else:
                log.warning(f"Received unknown message type: {msg_type}")

        except json.JSONDecodeError:
            log.error("Failed to decode JSON message.")
        except Exception:
            log.error(f"Error dispatching message: {traceback.format_exc()}")
            
    async def _handle_remote_exec(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Handles a remote execution request and streams output back."""
        command_str = message.get('command_str', '')
        if not command_str:
            return

        exec_io = self.kernel.system.fork()

        # Custom writer to stream stdout back over the websocket
        class RemoteWriter:
            def __init__(self, ws, stream_name):
                self.ws = ws
                self.stream_name = stream_name
            
            def write(self, data: str):
                response = {
                    "type": "remote_exec_response",
                    "stream": self.stream_name,
                    "data": data,
                    "is_complete": False
                }
                asyncio.create_task(self.ws.send(json.dumps(response)))
            
            def flush(self):
                pass

        exec_io.stdout = RemoteWriter(websocket, 'stdout')
        # TODO: A proper solution would also capture stderr
        
        try:
            await self.kernel.call(exec_io, command_str)
        finally:
            # Signal completion
            response = {"type": "remote_exec_response", "stream": "status", "data": "", "is_complete": True}
            await websocket.send(json.dumps(response))

