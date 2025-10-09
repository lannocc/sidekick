 # Proposal: Evolving IOSK Netroom to a Full Mesh Network

**Status**: Proposed

### 1. Introduction

The `netroom` implementation successfully introduced peer-to-peer networking to the IOSK ecosystem, enabling direct system-to-system communication, remote command execution, and shared room states. However, the current model is based on direct connections, forming a simple graph (often a star or chain topology). If system A is connected to B, and B is connected to C, A and C remain unaware of each other's existence, preventing direct communication and creating a single point of failure at B.

This proposal outlines the next evolution of IOSK networking: a true, self-organizing, and fully-connected mesh network. The goal is to create a system where every node in the mesh is aware of every other node and can communicate with them, either through a direct connection or by routing through an intermediary peer.

This enhancement will provide three key benefits:
1.  **Resilience**: The mesh will be able to withstand the loss of individual nodes without partitioning the entire network.
2.  **Efficiency**: Nodes will proactively seek and establish direct connections to maintain the shortest possible communication paths.
3.  **Scalability**: The system will have a clear protocol for discovering and integrating new nodes, allowing the network to grow organically.

### 2. Architectural Refinements

To achieve a cleaner separation of concerns, the first step is to fully encapsulate all networking logic within the `PortManager`.

#### 2.1. Consolidating Network State Management

Currently, the `IOSK` kernel in `src/iosk/kernel.py` contains the `update_network_state()` method, which processes state updates from remote peers. This responsibility for interpreting network messages properly belongs to the networking subsystem.

**Proposal:** Move the logic from `kernel.update_network_state()` into a new private method within `PortManager` (e.g., `_process_peer_state_update`). The `PortManager`'s message dispatcher will call this method directly. The kernel will remain the owner of the state caches (`network_users`, `network_rooms`), but the `PortManager` will be responsible for populating them based on network traffic. This reinforces `PortManager` as the sole handler of the network protocol.

### 3. Mesh Discovery and State Propagation Protocol

To enable a full mesh, we must enhance the protocol to allow nodes to discover each other indirectly and then form direct connections. This will be a three-phase process.

#### 3.1. Phase 1: Enhanced Handshake (Peer Introduction)

The existing handshake protocol will be extended. When a peer (C) connects to an existing node (B), the `handshake_ack` message from B to C will now include B's list of its own connected peers (e.g., `peers: [{'hostname': 'A', 'address': '10.1.2.3:4209'}]`). This informs C that A exists and provides its last known address.

#### 3.2. Phase 2: Proactive Connection (Shortest Path Seeking)

Upon receiving the peer list in the `handshake_ack`, the connecting peer (C) will iterate through the list of new, unknown peers (A). For each one, it will automatically initiate a background `mesh` connection attempt. This proactive behavior ensures that the mesh always trends towards a fully-connected state with the shortest possible paths (direct connections).

#### 3.3. Phase 3: Peer Propagation (Network-wide Announcement)

To ensure all nodes are aware of new arrivals, a new `peer_update` message will be introduced. When B successfully completes a handshake with a new peer C, B will immediately broadcast a `peer_update` message to all of its *other* established peers (A).

*   **Message Format**: `{'type': 'peer_update', 'action': 'connect', 'peer_info': {'hostname': 'C', 'address': 'c.ip:port'}}`
*   **Behavior**: When A receives this message, it learns about C and its address. Just as in Phase 2, A will then initiate its own proactive connection attempt to C.

This dual mechanism of "introduction" during handshake and "announcement" after connection ensures rapid and robust propagation of the network topology.

### 4. Routing and Message Forwarding

In cases where a direct connection cannot be established (e.g., due to firewall restrictions), the mesh must be able to route messages through intermediary nodes.

#### 4.1. Routing Table

The `PortManager` will maintain a new `self.routing_table` attribute. This table will map every known hostname in the mesh to its connection status.

*   **Direct Route**: `{'hostname': 'B', 'type': 'direct', 'websocket': <ws_object>}`
*   **Indirect Route**: `{'hostname': 'C', 'type': 'indirect', 'via': 'B'}`

This table becomes the definitive source for how to reach any node in the mesh.

#### 4.2. Updated `route_message` Logic

The `PortManager.route_message(target_host, message)` method will be enhanced:
1.  It looks up `target_host` in `self.routing_table`.
2.  If the route is `direct`, it sends the `message` over the corresponding websocket as it does now.
3.  If the route is `indirect`, it identifies the intermediary (`via: 'B'`). It then wraps the original message in a `forward_request` and sends it to 'B'.
    *   **Forward Request Format**: `{'type': 'forward_request', 'final_destination': 'C', 'payload': original_message}`

#### 4.3. Handling Forward Requests

When a `PortManager` receives a message of type `forward_request`, its `_dispatch_message` method will not process the payload locally. Instead, it will read the `final_destination`, unwrap the `payload`, and call its own `route_message` to send the payload on to its final destination. This enables multi-hop routing.

### 5. Updated `mesh` Command Output

The `mesh` command must be updated to provide users with a clear view of the network topology, including routed connections. The `iocall` in `/bin/mesh.py` will be modified to read from the `PortManager`'s new routing table.

**Proposed `ADDRESS` Column Format**:
*   **Direct Connection**: The IP address and port of the peer (e.g., `10.1.2.3:4209`).
*   **Indirect Connection**: The next hop required to reach the destination, for clarity (e.g., `[via gemini2]`).

**Example `mesh` Output on Host `alpha`:**
(Assuming `alpha` is directly connected to `beta`, and `gamma` is connected to `beta` but not `alpha`)
```
HOSTNAME   ADDRESS
--------   -----------------
beta       10.1.2.4:4209
gamma      [via beta]

:: 2 systems in mesh.
```
This output clearly communicates that to reach `gamma`, traffic will be routed through `beta`.

### 6. Implementation Plan

1.  **Refactor `PortManager`**: Move the logic from `kernel.update_network_state` into `port.py`. Add the `self.routing_table` attribute and logic to populate it based on direct connections and `peer_update` messages.
2.  **Enhance Handshake Protocol**: Modify `_handshake` in `PortManager` to exchange full peer lists (including addresses) within the `handshake` and `handshake_ack` messages.
3.  **Implement Proactive Connection**: In `PortManager`, add logic to process the received peer list after a handshake and spawn background tasks to attempt direct connections to any unknown peers. Add checks to prevent connecting to self or re-connecting to existing peers.
4.  **Implement Peer Propagation**: Define the `peer_update` message type. Modify `PortManager` to broadcast this message to all existing peers whenever a new peer connection is successfully established.
5.  **Implement Routing Logic**: Update `route_message` to consult the routing table and wrap messages in a `forward_request` for indirect routes. Add a handler for `forward_request` to the message dispatcher.
6.  **Update `mesh` Command**: Modify `/bin/mesh.py` to query the `PortManager` for its routing table and display peers with the new `ADDRESS` format, distinguishing between direct and indirect (`[via ...]`) connections.

### 7. Conclusion

This proposal provides a clear and actionable path to evolving IOSK's networking from a simple peer-to-peer system into a robust, self-organizing mesh network. By implementing these changes, IOSK will gain significant resilience, efficiency, and scalability, making it a far more powerful and reliable platform for building distributed, collaborative AI systems.

