import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../config/database.js';
import { fastApiClient } from '../clients/fastApiClient.js';
import { userService } from './userService.js';
import { orcaEventEmitter } from '../sockets/eventEmitter.js';
import { logger } from '../utils/logger.js';
import { NotFoundError } from '../utils/errors.js';

// In-memory fallback caches when MongoDB is in fallback mode
const inMemoryConversations = new Map();
const inMemoryMessages = new Map();

export class ConversationService {
  async listConversations(userId) {
    const db = getDb();
    if (db) {
      const filter = {};
      if (userId) filter.userId = userId;
      return await db
        .collection('conversations')
        .find(filter)
        .sort({ lastMessageAt: -1 })
        .limit(50)
        .toArray();
    } else {
      const all = Array.from(inMemoryConversations.values());
      if (userId) {
        return all.filter((c) => c.userId === userId);
      }
      return all;
    }
  }

  async createConversation(userId, title, initialLocation) {
    const db = getDb();
    const conversationId = uuidv4();
    const now = new Date().toISOString();

    const doc = {
      conversationId,
      userId: userId || null,
      title: title || 'New Maritime Advisory',
      lastMessageAt: now,
      messageCount: 0,
      status: 'active',
      metadata: {
        initialLocation,
      },
      createdAt: now,
      updatedAt: now,
    };

    if (db) {
      await db.collection('conversations').insertOne(doc);
    } else {
      inMemoryConversations.set(conversationId, doc);
      inMemoryMessages.set(conversationId, []);
    }

    return doc;
  }

  async getConversation(conversationId) {
    const db = getDb();
    if (db) {
      const doc = await db.collection('conversations').findOne({ conversationId });
      if (doc) return doc;
    } else {
      const doc = inMemoryConversations.get(conversationId);
      if (doc) return doc;
    }
    throw new NotFoundError(`Conversation '${conversationId}' not found`);
  }

  async deleteConversation(conversationId, userId) {
    const db = getDb();
    if (db) {
      const filter = { conversationId };
      if (userId) filter.userId = userId;
      await db.collection('conversations').deleteOne(filter);
      await db.collection('messages').deleteMany({ conversationId });
    } else {
      inMemoryConversations.delete(conversationId);
      inMemoryMessages.delete(conversationId);
    }
    return true;
  }

  async getMessages(conversationId) {
    const db = getDb();
    if (db) {
      return await db
        .collection('messages')
        .find({ conversationId })
        .sort({ createdAt: 1 })
        .toArray();
    } else {
      return inMemoryMessages.get(conversationId) || [];
    }
  }

  /**
   * Main STM (Short-Term Memory) + AI Agent Flow:
   * 1. Retrieve recent messages from MongoDB (STM)
   * 2. Build OrcaQueryRequest with STM context + user profile
   * 3. Forward to FastAPI AI service (LangGraph + Vector DB LTM + Groq)
   * 4. Persist user & assistant messages to MongoDB STM
   * 5. Return structured result
   */
  async sendMessage(
    conversationId,
    messageText,
    userId,
    userProfileOverride,
    locationOverride
  ) {
    const db = getDb();
    const requestId = uuidv4();
    const now = new Date().toISOString();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Ensure conversation exists (create if needed)
    let conv;
    try {
      conv = await this.getConversation(conversationId);
    } catch {
      conv = await this.createConversation(userId, messageText.slice(0, 40));
    }

    // 2. Resolve user profile for vessel safety calibrations
    let role = userProfileOverride?.role || 'fisherman';
    let vesselClass = userProfileOverride?.vesselClass || 'motorized_fiberglass';
    let language = userProfileOverride?.language || 'en';

    if (userId) {
      try {
        const userProfile = await userService.getProfile(userId);
        role = userProfile.role || role;
        vesselClass = userProfile.vesselClass || vesselClass;
        language = userProfile.preferredLanguage || language;
      } catch {
        // Continue with overrides or defaults
      }
    }

    // 3. Construct AI Query Request
    const queryRequest = {
      conversationId,
      query: messageText,
      intent: 'safety_check',
      location: locationOverride || conv.metadata?.initialLocation || undefined,
      userProfile: {
        role,
        vesselClass,
        language,
      },
    };

    // 4. Emit live progression via Socket.IO
    orcaEventEmitter.emitAgentStarted({
      requestId,
      conversationId,
      timestamp: now,
      agent: 'planner',
      agentLabel: 'Query Intake & Planning',
      intent: 'safety_check',
    });

    // 5. Execute AI agent reasoning via FastAPI
    logger.info({ requestId, conversationId }, 'Dispatching chat turn to FastAPI AI service');
    const agentResponse = await fastApiClient.executeWorkflow(queryRequest, requestId);

    // 6. Persist User Message to MongoDB STM
    const userMessageDoc = {
      messageId: `msg-u-${uuidv4()}`,
      conversationId,
      userId: userId || null,
      role: 'user',
      content: messageText,
      time: timeStr,
      createdAt: now,
    };

    // 7. Persist Assistant Response to MongoDB STM
    const assistantMessageDoc = {
      messageId: `msg-a-${uuidv4()}`,
      conversationId,
      userId: userId || null,
      role: 'assistant',
      content: agentResponse.answer,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      response: {
        recommendation: agentResponse.recommendation,
        riskLevel: agentResponse.riskLevel,
        riskScore: agentResponse.riskScore,
        confidenceScore: agentResponse.confidenceScore,
        clarificationQuestion: agentResponse.clarificationQuestion,
        dataAvailability: agentResponse.dataAvailability,
        evidence: agentResponse.evidence,
        safety: agentResponse.safety,
        trace: agentResponse.trace,
      },
      createdAt: new Date().toISOString(),
    };

    if (db) {
      try {
        await db.collection('messages').insertMany([userMessageDoc, assistantMessageDoc]);
        // Update conversation summary
        const newTitle = conv.title === 'New Maritime Advisory' ? messageText.slice(0, 45) : conv.title;
        await db.collection('conversations').updateOne(
          { conversationId },
          {
            $set: {
              title: newTitle,
              lastMessageAt: assistantMessageDoc.createdAt,
              updatedAt: assistantMessageDoc.createdAt,
            },
            $inc: { messageCount: 2 },
          }
        );
      } catch (err) {
        logger.warn({ err, conversationId }, 'Failed persisting messages to MongoDB');
      }
    } else {
      const list = inMemoryMessages.get(conversationId) || [];
      list.push(userMessageDoc, assistantMessageDoc);
      inMemoryMessages.set(conversationId, list);
      conv.messageCount = list.length;
      conv.lastMessageAt = assistantMessageDoc.createdAt;
    }

    // 8. Emit completion event
    orcaEventEmitter.emitResponseCompleted({
      requestId,
      conversationId,
      timestamp: assistantMessageDoc.createdAt,
      response: agentResponse,
    });

    return {
      userMessage: userMessageDoc,
      assistantMessage: assistantMessageDoc,
      agentResponse,
    };
  }
}

export const conversationService = new ConversationService();
