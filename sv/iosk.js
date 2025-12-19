import { writable, get } from 'svelte/store';
import { stripAnsi } from './ansi.js';
import { windows } from './windows.js';
import { newIoskPrivateChat } from './apps.js';

// --- Existing Stores (payloads will be updated to include connectionId where appropriate) ---

// Used for Explorer -> Console communication to request a directory listing
export const fileSystemRequests = writable(null);

// Used for Console -> Explorer communication to provide a directory listing
export const fileSystemResponses = writable(null);

// Used for Console -> Components to broadcast live filesystem events
export const fileSystemWatchEvents = writable(null);
export const fileSystemTailEvents = writable(null);

// Used for Private Chat -> Console to send a command/message
export const consoleCommands = writable(null);

// Used for Console -> Private Chat to deliver a received message
export const privateMessages = writable(null);

// Used for file picker communication
export const fileSelection = writable(null);

// Used for Console -> Context Inspector communication
export const contextUpdates = writable(null);


// --- New Central Connection Hub (as per proposal) ---

/**
 * @typedef {Object} IoskConnectionState
 * @property {WebSocket} ws - The WebSocket instance.
 * @property {string} url - The WebSocket URL.
 * @property {string} username - The username for the connection.
 * @property {'connecting'|'connected'|'error'|'disconnected'} status - The connection status.
 * @property {Array<{type: 'prompt'|'output', content: string}>} output - The console output buffer.
 * @property {string[]} commandHistory - History of sent commands.
 * @property {string} currentPrompt - The current prompt string from the server.
 * @property {string|null} roomName - The name of the current room.
 * @property {string} roomTopic - The topic of the current room.
 * @property {string} motd - The message of the day.
 * @property {Array<any>} roomParticipants - List of users in the room.
 * @property {Array<any>} availableRooms - List of available rooms.
 * @property {Object<string, string>} userColors - Mapping of usernames to ANSI color names.
 * @property {Object<string, any>} userTokenStats - Token usage statistics for users.
 * @property {string} localHostname - The hostname reported by the iosk server.
 */

/**
 * A writable store that tracks all active IOSK connections.
 * The key is a unique connectionId (e.g., "root@ws://localhost:4209").
 * The value is an object containing the full state of that connection.
 * @type {import('svelte/store').Writable<Map<string, IoskConnectionState>>}
 */
export const activeIoskConnections = writable(new Map());

const PREAMBLE = "SK1:";

/**
 * Initiates a new persistent WebSocket connection to an iosk server.
 * If a connection for the given url and username already exists, it does nothing.
 * @param {string} url The WebSocket URL (e.g., "ws://localhost:4209").
 * @param {string} username The username to connect with.
 * @returns {string} The unique connectionId for this session.
 */
export function initiateConnection(url, username) {
    const connectionId = `${username}@${url}`;

    let existingConnection;
    activeIoskConnections.subscribe(conns => {
        existingConnection = conns.get(connectionId);
    })();

    if (existingConnection && (existingConnection.status === 'connected' || existingConnection.status === 'connecting')) {
        console.warn(`Connection for ${connectionId} already exists or is in progress.`);
        return connectionId;
    }

    const ws = new WebSocket(url);

    /** @type {IoskConnectionState} */
    const connectionState = {
        ws,
        url,
        username,
        status: 'connecting',
        output: [{ type: 'output', content: `Connecting to ${url} as ${username}...` }],
        commandHistory: existingConnection?.commandHistory || [], // Persist history on reconnect
        currentPrompt: '',
        roomName: null,
        roomTopic: '',
        motd: '',
        roomParticipants: [],
        availableRooms: [],
        userColors: {},
        userTokenStats: {},
        localHostname: '',
    };

    activeIoskConnections.update(conns => conns.set(connectionId, connectionState));

    ws.onopen = () => {
        activeIoskConnections.update(conns => {
            const state = conns.get(connectionId);
            if (state) {
                state.status = 'connected';
                state.output = [...state.output, { type: 'output', content: `Connected.` }];
                const handshake = { type: 'handshake', id: 'client', user: username };
                ws.send(JSON.stringify(handshake));
            }
            return conns;
        });
    };

    ws.onmessage = (event) => {
        if (typeof event.data !== 'string' || !event.data.startsWith(PREAMBLE)) {
            return;
        }
        try {
            const jsonData = event.data.substring(PREAMBLE.length);
            const data = JSON.parse(jsonData);

            activeIoskConnections.update(conns => {
                const state = conns.get(connectionId);
                if (!state) return conns;

                // --- Handle different message types ---
                if (data.type === 'context_update') {
                    contextUpdates.set({ connectionId, ...data, type: 'full' });
                } else if (data.type === 'private_message') {
                    const remoteUser = stripAnsi(data.from);
                    const localUser = state.username;

                    const messagePayload = {
                        connectionId,
                        from: remoteUser,
                        to: stripAnsi(data.to),
                        content: data.content,
                        timestamp: Date.now()
                    };
                    // First, update the global message store so that any existing or newly
                    // created windows will receive the message.
                    privateMessages.set(messagePayload);
                    
                    // Don't automatically open a chat window for messages sent to oneself.
                    if (remoteUser === localUser) {
                        return conns;
                    }

                    // Check if a chat window for this specific conversation already exists.
                    const allWindows = get(windows);
                    const chatExists = allWindows.flatMap(g => g.tabs).some(t =>
                        t.componentName === 'IoskPrivateChat' &&
                        t.connectionId === connectionId &&
                        t.remoteUser === remoteUser
                    );

                    if (!chatExists) {
                        // If no window exists, create one, passing the initial message.
                        newIoskPrivateChat({
                            connectionId,
                            localUser,
                            remoteUser,
                            initialMessage: messagePayload
                        });
                    }
                } else if (data.type === 'state_info' || data.type === 'room_state_update') {
                    if (data.hostname) state.localHostname = data.hostname;
                    state.roomName = data.roomName || null;
                    state.roomTopic = data.roomTopic || '';
                    state.roomParticipants = data.participants || [];
                    state.availableRooms = data.availableRooms || [];
                    if (data.userColors) state.userColors = data.userColors;

                    const currentParticipantNames = new Set(state.roomParticipants.map(p => p.name));
                    const newStats = {};
                    for (const user of Object.keys(state.userTokenStats)) {
                        if (currentParticipantNames.has(user)) {
                            newStats[user] = state.userTokenStats[user];
                        }
                    }
                    state.userTokenStats = newStats;

                    if (data.type === 'state_info') {
                        state.motd = data.motd || '';
                    }

                    state.roomParticipants.forEach(p => {
                        contextUpdates.set({ connectionId, targetUser: p.name, type: 'partial', data: { isPaused: p.paused } });
                    });
                } else if (data.type === 'token_stats_update') {
                    state.userTokenStats[data.user] = data.stats;
                    state.userTokenStats = { ...state.userTokenStats }; // Trigger reactivity
                    contextUpdates.set({ connectionId, targetUser: data.user, type: 'partial', data: { tokenStats: data.stats } });
                } else if (data.type === 'user_colors_update') {
                    state.userColors = data.colors;
                } else if (data.output || data.prompt) {
                    if (data.output) {
                        const clearScreenCode = "\x1b[H\x1b[2J";
                        if (data.output === clearScreenCode) {
                            state.output = [];
                        } else if (data.output) {
                            const lines = data.output.split('\n');
                            state.output = [...state.output, ...lines.map(line => ({ type: 'output', content: line }))];
                        }
                    }
                    if (data.prompt) {
                        state.currentPrompt = data.prompt;
                    }
                } else if (
                    data.type === 'fs_list_response' || data.type === 'fs_read_response' ||
                    data.type === 'exec_command_response' || data.type === 'fs_watch_update' ||
                    data.type === 'fs_tail_update'
                ) {
                    const payload = { connectionId, requesterId: data.requesterId, data, timestamp: Date.now() };
                    if (data.type === 'fs_watch_update') fileSystemWatchEvents.set(payload);
                    else if (data.type === 'fs_tail_update') fileSystemTailEvents.set(payload);
                    else fileSystemResponses.set(payload);
                }
                
                return conns;
            });
        } catch (e) {
            console.error(`Error parsing WebSocket message for ${connectionId}:`, e);
        }
    };

    ws.onclose = () => {
        activeIoskConnections.update(conns => {
            const state = conns.get(connectionId);
            if (state) {
                state.status = 'disconnected';
                state.output = [...state.output, { type: 'output', content: `Connection closed.` }];
                state.roomName = null;
                state.roomTopic = '';
                state.roomParticipants = [];
                state.currentPrompt = '';
            }
            return conns;
        });
    };

    ws.onerror = (error) => {
        console.error(`WebSocket error for ${connectionId}:`, error);
        activeIoskConnections.update(conns => {
            const state = conns.get(connectionId);
            if (state) {
                state.status = 'error';
                state.output = [...state.output, { type: 'output', content: `[Error] Could not establish connection to ${url}.` }];
            }
            return conns;
        });
    };

    return connectionId;
}

/**
 * Gracefully closes a specific WebSocket connection and removes it from the central store.
 * @param {string} connectionId The ID of the connection to close.
 */
export function disconnect(connectionId) {
    activeIoskConnections.update(conns => {
        const state = conns.get(connectionId);
        if (state) {
            state.ws.onclose = null; // Prevent the default onclose handler from running
            state.ws.close();
            conns.delete(connectionId);
        }
        return conns;
    });
}

/**
 * Sends a command string through a specific connection's WebSocket.
 * @param {string} connectionId The ID of the connection.
 * @param {string} command The command string to send.
 */
export function sendCommand(connectionId, command) {
    let state;
    activeIoskConnections.subscribe(conns => state = conns.get(connectionId))();

    if (state && state.status === 'connected') {
        // Immediately add the command to the local output and history for responsiveness.
        activeIoskConnections.update(conns => {
            const s = conns.get(connectionId);
            if (s) {
                s.output = [...s.output, { type: 'prompt', content: s.currentPrompt + command }];
                if (s.commandHistory.length === 0 || s.commandHistory[s.commandHistory.length - 1] !== command) {
                    s.commandHistory = [...s.commandHistory, command];
                }
            }
            return conns;
        });

        const message = { type: 'client_input', data: command + '\n' };
        state.ws.send(JSON.stringify(message));
    } else {
        console.warn(`Cannot send command to ${connectionId}: not connected.`);
    }
}

/**
 * Sends a structured request object through a specific connection's WebSocket.
 * Used for file system operations, watch commands, etc.
 * @param {string} connectionId The ID of the connection.
 * @param {object} request The structured request object to send.
 */
export function sendRequest(connectionId, request) {
    let state;
    activeIoskConnections.subscribe(conns => state = conns.get(connectionId))();

    if (state && state.status === 'connected') {
        state.ws.send(JSON.stringify(request));
    } else {
        console.warn(`Cannot send request to ${connectionId}: not connected.`);
    }
}