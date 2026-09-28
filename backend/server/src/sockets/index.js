import { Server as SocketIOServer } from 'socket.io';
import { corsOriginsArray } from '../config/env.js';
import { ORCA_SOCKET_NAMESPACE } from '../contracts/index.js';
import { socketAuthMiddleware } from './socketAuth.js';
import { registerOrcaSocketHandlers } from './orcaHandlers.js';
import { orcaEventEmitter } from './eventEmitter.js';
import { logger } from '../utils/logger.js';

let io = null;

export function initializeSockets(httpServer) {
  io = new SocketIOServer(httpServer, {
    cors: {
      origin: corsOriginsArray,
      methods: ['GET', 'POST'],
      credentials: true,
    },
    transports: ['websocket', 'polling'],
  });

  const orcaNamespace = io.of(ORCA_SOCKET_NAMESPACE);

  // Handshake authentication
  orcaNamespace.use(socketAuthMiddleware);

  // Set emitter target
  orcaEventEmitter.setNamespace(orcaNamespace);

  // Connection handling
  orcaNamespace.on('connection', (socket) => {
    logger.info({ socketId: socket.id, namespace: ORCA_SOCKET_NAMESPACE }, 'New client connected to /orca namespace');
    registerOrcaSocketHandlers(socket);
  });

  logger.info({ namespace: ORCA_SOCKET_NAMESPACE }, 'Socket.IO initialized successfully');
  return io;
}

export function getIO() {
  return io;
}
