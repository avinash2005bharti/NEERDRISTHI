import { logger } from '../utils/logger.js';

export class OrcaEventEmitter {
  constructor() {
    this.ioNamespace = null;
  }

  setNamespace(ns) {
    this.ioNamespace = ns;
  }

  broadcastToRooms(conversationId, requestId, event, payload) {
    if (!this.ioNamespace) {
      logger.debug({ event, requestId }, 'Socket namespace not initialized yet, skipping broadcast');
      return;
    }

    // Broadcast to both conversation room and specific request room
    this.ioNamespace.to(`conversation:${conversationId}`).to(`request:${requestId}`).emit(event, payload);
    logger.debug({ event, conversationId, requestId }, 'Broadcasted Socket.IO event');
  }

  emitQueryAccepted(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:query:accepted', payload);
  }

  emitAgentStarted(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:agent:started', payload);
  }

  emitAgentProgress(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:agent:progress', payload);
  }

  emitAgentCompleted(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:agent:completed', payload);
  }

  emitDataUnavailable(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:data:unavailable', payload);
  }

  emitClarificationRequired(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:clarification:required', payload);
  }

  emitResponseCompleted(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:response:completed', payload);
  }

  emitResponsePartial(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:response:partial', payload);
  }

  emitResponseFailed(payload) {
    this.broadcastToRooms(payload.conversationId, payload.requestId, 'orca:response:failed', payload);
  }

  emitEmergencyAlert(payload) {
    if (this.ioNamespace) {
      this.ioNamespace.emit('orca:alert:emergency', payload);
      logger.warn({ alertId: payload.alertId, severity: payload.severity }, 'Broadcasted system-wide emergency SOS beacon');
    }
  }
}

export const orcaEventEmitter = new OrcaEventEmitter();
