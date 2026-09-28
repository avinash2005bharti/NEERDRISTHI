import { useEffect } from 'react';
import { socketService } from '../services/websocket/socketService';
import { appStore } from '../stores/appState';
import {
  SocketAgentStarted,
  SocketAgentProgress,
  SocketAgentCompleted,
  SocketDataUnavailable,
  OrcaQueryResponse,
} from '../types';

export function useSocketEvents(conversationId?: string | null) {
  useEffect(() => {
    socketService.connect();

    if (conversationId) {
      socketService.joinConversation(conversationId);
    }

    const unsubStarted = socketService.on('orca:agent:started', (payload: SocketAgentStarted) => {
      appStore.updateAgentStatus(payload.agent, 'running', payload.agentLabel);
      appStore.setAgentRunning(true, `Agent Active: ${payload.agentLabel || payload.agent}`);
    });

    const unsubProgress = socketService.on('orca:agent:progress', (payload: SocketAgentProgress) => {
      appStore.updateAgentStatus(payload.agent, 'running', payload.message);
      appStore.setAgentRunning(true, payload.message);
    });

    const unsubCompleted = socketService.on('orca:agent:completed', (payload: SocketAgentCompleted) => {
      appStore.updateAgentStatus(payload.agent, 'completed', payload.summary);
    });

    const unsubUnavailable = socketService.on('orca:data:unavailable', (payload: SocketDataUnavailable) => {
      appStore.updateAgentStatus(
        payload.category,
        'skipped',
        `${payload.providerName}: ${payload.reason}`
      );
    });

    const unsubRespCompleted = socketService.on('orca:response:completed', () => {
      appStore.setAgentRunning(false, 'Analysis Complete');
    });

    const unsubRespPartial = socketService.on('orca:response:partial', () => {
      appStore.setAgentRunning(false, 'Analysis Complete (with non-fatal data gaps)');
    });

    const unsubRespFailed = socketService.on('orca:response:failed', (data: any) => {
      appStore.setAgentRunning(false, `Reasoning Stopped: ${data?.error?.message || 'Error'}`);
    });

    const unsubEmergency = socketService.on('orca:alert:emergency', (payload: any) => {
      console.warn('🚨 HIGH-PRIORITY EMERGENCY SOS BEACON RECEIVED:', payload);
      if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
        new Notification(`🚨 MAYDAY SOS: ${payload.title}`, {
          body: payload.summary,
          icon: '/favicon.ico',
        });
      }
    });

    return () => {
      unsubStarted();
      unsubProgress();
      unsubCompleted();
      unsubUnavailable();
      unsubRespCompleted();
      unsubRespPartial();
      unsubRespFailed();
      unsubEmergency();

      if (conversationId) {
        socketService.leaveConversation(conversationId);
      }
    };
  }, [conversationId]);
}
