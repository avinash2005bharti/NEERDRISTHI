import { io, Socket } from 'socket.io-client';
import { getStoredToken } from '../api/client';
import {
  SocketAgentStarted,
  SocketAgentProgress,
  SocketAgentCompleted,
  SocketDataUnavailable,
  SocketClarificationRequired,
  OrcaQueryResponse,
  OrcaQueryRequest,
} from '../../types';

export type SocketEventHandler = (data: any) => void;

class SocketService {
  private socket: Socket | null = null;
  private isConnecting = false;
  private listeners: Map<string, Set<SocketEventHandler>> = new Map();
  private currentConversationId: string | null = null;

  public connect(): void {
    if (this.socket?.connected || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    const token = getStoredToken();

    // In production decoupled deployment, connect to backend URL (e.g. https://orca-backend.onrender.com).
    // In local dev proxy or single-port mode, falls back to window.location.origin.
    const envSocketUrl = (import.meta.env.VITE_SOCKET_URL || import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
    const socketUrl = envSocketUrl || window.location.origin;
    
    this.socket = io(`${socketUrl}/orca`, {
      auth: {
        token: token || '',
      },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 10,
      reconnectionDelay: 2000,
    });

    this.socket.on('connect', () => {
      this.isConnecting = false;
      this.emitInternal('connect', { socketId: this.socket?.id });
      if (this.currentConversationId) {
        this.joinConversation(this.currentConversationId);
      }
    });

    this.socket.on('disconnect', (reason) => {
      this.emitInternal('disconnect', reason);
    });

    this.socket.on('connect_error', (error) => {
      this.isConnecting = false;
      this.emitInternal('error', error);
    });

    // Wire up all official ORCA server events
    const serverEvents = [
      'orca:connected',
      'orca:query:accepted',
      'orca:agent:started',
      'orca:agent:progress',
      'orca:agent:completed',
      'orca:data:unavailable',
      'orca:clarification:required',
      'orca:response:completed',
      'orca:response:partial',
      'orca:response:failed',
    ];

    serverEvents.forEach((event) => {
      this.socket?.on(event, (data) => {
        this.emitInternal(event, data);
      });
    });
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnecting = false;
    }
  }

  public isConnected(): boolean {
    return !!this.socket?.connected;
  }

  public joinConversation(conversationId: string): void {
    this.currentConversationId = conversationId;
    if (this.socket?.connected) {
      this.socket.emit('orca:conversation:join', { conversationId });
    }
  }

  public leaveConversation(conversationId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('orca:conversation:leave', { conversationId });
    }
    if (this.currentConversationId === conversationId) {
      this.currentConversationId = null;
    }
  }

  public submitQuery(request: OrcaQueryRequest, callback?: (ack: any) => void): void {
    if (this.socket?.connected) {
      this.socket.emit('orca:query:submit', { request }, callback);
    } else {
      if (callback) {
        callback({ accepted: false, error: 'Socket not connected' });
      }
    }
  }

  public on(event: string, handler: SocketEventHandler): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);

    // Return cleanup unsubscribe function
    return () => {
      this.listeners.get(event)?.delete(handler);
    };
  }

  private emitInternal(event: string, data: any): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (e) {
          console.error(`Error in socket event handler for ${event}:`, e);
        }
      });
    }
  }
}

export const socketService = new SocketService();
