import { orcaService } from '../services/orcaService.js';
import { orcaQuerySchema } from '../validators/orcaSchemas.js';
import { logger } from '../utils/logger.js';

export function registerOrcaSocketHandlers(socket) {
  // Send welcome on connection
  const welcomePayload = {
    socketId: socket.id,
    userId: socket.data?.user?.userId,
    authenticated: !!socket.data?.authenticated,
    timestamp: new Date().toISOString(),
    message: 'Connected to ORCA Marine Intelligence Realtime Gateway',
  };
  socket.emit('orca:connected', welcomePayload);

  // Handle joining a conversation room
  socket.on('orca:conversation:join', (payload, callback) => {
    const room = `conversation:${payload.conversationId}`;
    socket.join(room);
    logger.info({ socketId: socket.id, room }, 'Socket joined conversation room');
    if (typeof callback === 'function') {
      callback({ joined: true, conversationId: payload.conversationId });
    }
  });

  // Handle leaving a conversation room
  socket.on('orca:conversation:leave', (payload, callback) => {
    const room = `conversation:${payload.conversationId}`;
    socket.leave(room);
    logger.info({ socketId: socket.id, room }, 'Socket left conversation room');
    if (typeof callback === 'function') {
      callback({ left: true, conversationId: payload.conversationId });
    }
  });

  // Handle real-time query submission over socket
  socket.on('orca:query:submit', async (payload, callback) => {
    logger.info({ socketId: socket.id }, 'Received orca:query:submit over websocket');
    try {
      const validated = orcaQuerySchema.parse(payload.request);
      const userId = socket.data?.user?.userId;

      // Auto-join conversation room if conversationId provided
      if (validated.conversationId) {
        socket.join(`conversation:${validated.conversationId}`);
      }

      // Acknowledge receipt immediately to frontend
      if (typeof callback === 'function') {
        callback({ accepted: true });
      }

      // Run workflow asynchronously (events will stream to room)
      await orcaService.processQuery(validated, userId);
    } catch (err) {
      logger.error({ socketId: socket.id, err: err.message }, 'Failed processing socket query submit');
      if (typeof callback === 'function') {
        callback({ accepted: false, error: err.message });
      }
    }
  });

  socket.on('disconnect', (reason) => {
    logger.debug({ socketId: socket.id, reason }, 'Socket disconnected');
  });
}
