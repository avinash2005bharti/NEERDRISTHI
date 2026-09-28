import { apiRequest } from '../api/client';
import {
  OrcaQueryRequest,
  OrcaQueryResponse,
  Conversation,
  ChatMessage,
} from '../../types';

export const chatService = {
  /**
   * Submit direct query to ORCA LangGraph cognitive multi-agent pipeline
   */
  async submitQuery(payload: OrcaQueryRequest): Promise<OrcaQueryResponse> {
    const res = await apiRequest<{
      success: boolean;
      data: OrcaQueryResponse;
      meta?: { requestId: string; timestamp: string };
    }>('/orca/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },

  /**
   * Fetch cached query result by requestId
   */
  async getQueryStatus(requestId: string): Promise<OrcaQueryResponse> {
    const res = await apiRequest<{ success: boolean; data: OrcaQueryResponse }>(
      `/orca/query/${encodeURIComponent(requestId)}`
    );
    return res.data;
  },

  /**
   * List all stored conversations
   */
  async listConversations(): Promise<Conversation[]> {
    const res = await apiRequest<{ success: boolean; data: Conversation[] }>('/chats');
    return res.data || [];
  },

  /**
   * Create a new conversation session
   */
  async createConversation(title?: string, initialLocation?: { name?: string; latitude?: number; longitude?: number }): Promise<Conversation> {
    const res = await apiRequest<{ success: boolean; data: Conversation }>('/chats', {
      method: 'POST',
      body: JSON.stringify({ title, initialLocation }),
    });
    return res.data;
  },

  /**
   * Get specific conversation details with messages
   */
  async getConversation(conversationId: string): Promise<Conversation> {
    const res = await apiRequest<{ success: boolean; data: Conversation }>(
      `/chats/${encodeURIComponent(conversationId)}`
    );
    return res.data;
  },

  /**
   * Delete conversation
   */
  async deleteConversation(conversationId: string): Promise<void> {
    await apiRequest<{ success: boolean; data: { deleted: boolean } }>(
      `/chats/${encodeURIComponent(conversationId)}`,
      { method: 'DELETE' }
    );
  },

  /**
   * Post message in conversation
   */
  async postMessage(
    conversationId: string,
    message: string,
    userProfile?: Record<string, unknown>,
    location?: { latitude: number; longitude: number; name?: string }
  ): Promise<{
    userMessage: ChatMessage;
    assistantMessage: ChatMessage;
    orcaResponse?: OrcaQueryResponse;
  }> {
    const res = await apiRequest<{
      success: boolean;
      data: {
        userMessage: ChatMessage;
        assistantMessage: ChatMessage;
        orcaResponse?: OrcaQueryResponse;
      };
    }>(`/chats/${encodeURIComponent(conversationId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        message,
        userProfile,
        location,
      }),
    });
    return res.data;
  },
};
