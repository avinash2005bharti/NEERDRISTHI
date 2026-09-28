import { verifyJwtToken } from '../utils/jwt.js';
import { logger } from '../utils/logger.js';

export function socketAuthMiddleware(socket, next) {
  const token =
    socket.handshake.auth?.token ||
    socket.handshake.headers?.authorization?.replace(/^Bearer\s+/i, '') ||
    socket.handshake.query?.token;

  if (!token) {
    // If auth token is missing, allow guest connection with unauthenticated flag
    socket.data = socket.data || {};
    socket.data.authenticated = false;
    logger.debug({ socketId: socket.id }, 'Socket connected without token (guest/unauthenticated)');
    return next();
  }

  try {
    const payload = verifyJwtToken(token);
    socket.data = socket.data || {};
    socket.data.user = payload;
    socket.data.authenticated = true;
    logger.debug({ socketId: socket.id, userId: payload.userId }, 'Socket authenticated successfully');
    next();
  } catch (err) {
    logger.warn({ socketId: socket.id, err: err.message }, 'Socket authentication token rejected');
    next(new Error('Authentication failed: Invalid or expired token'));
  }
}
