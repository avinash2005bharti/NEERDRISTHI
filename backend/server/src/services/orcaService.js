import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../config/database.js';
import { fastApiClient } from '../clients/fastApiClient.js';
import { orcaEventEmitter } from '../sockets/eventEmitter.js';
import { logger } from '../utils/logger.js';
import { NotFoundError } from '../utils/errors.js';

// Fallback in-memory store for recent queries when MongoDB is unavailable
const inMemoryQueries = new Map();

export class OrcaService {
  async processQuery(request, userId) {
    const requestId = uuidv4();
    const conversationId = request.conversationId || uuidv4();
    const startTime = new Date().toISOString();

    // Attach canonical IDs
    const normalizedRequest = {
      ...request,
      conversationId,
    };

    logger.info({ requestId, conversationId, query: request.query }, 'Received ORCA query');

    // 1. Emit query accepted event
    orcaEventEmitter.emitQueryAccepted({
      requestId,
      conversationId,
      timestamp: startTime,
      status: 'accepted',
      estimatedSteps: [
        'Query Intake & Planning',
        'Geospatial Coordinate Resolution',
        'Parallel Marine & Weather Observation Fetching',
        'Semantic Memory & Maritime Advisory Retrieval',
        'Deterministic Safety & Risk Rule Evaluation',
        'Multi-Agent Grounded Synthesis',
      ],
    });

    // 2. Emit initial progress
    orcaEventEmitter.emitAgentStarted({
      requestId,
      conversationId,
      timestamp: new Date().toISOString(),
      agent: 'planner',
      agentLabel: 'Query Intake & Multi-Agent Planner',
      intent: request.intent || 'safety_check',
    });

    try {
      // 3. Dispatch to FastAPI LangGraph workflow
      const result = await fastApiClient.executeWorkflow(normalizedRequest, requestId);

      // 4. Emit events for any data unavailability discovered
      if (result.dataAvailability) {
        for (const [cat, status] of Object.entries(result.dataAvailability)) {
          if (status === 'unavailable' || status === 'stale') {
            orcaEventEmitter.emitDataUnavailable({
              requestId,
              conversationId,
              timestamp: new Date().toISOString(),
              category: cat,
              providerName: cat.toUpperCase(),
              reason: `Official ${cat} telemetry endpoint is unconfigured or returned no live data.`,
              impactOnRecommendation:
                result.recommendation === 'INSUFFICIENT_DATA' || result.recommendation === 'NO_GO'
                  ? 'Policy mandates NO_GO or INSUFFICIENT_DATA due to missing critical observations.'
                  : 'Observation gap noted in evidence ledger.',
            });
          }
        }
      }

      // 5. Emit clarification event if needed
      if (result.status === 'clarification_required' && result.clarificationQuestion) {
        orcaEventEmitter.emitClarificationRequired({
          requestId,
          conversationId,
          timestamp: new Date().toISOString(),
          question: result.clarificationQuestion,
        });
      }

      // 6. Emit completion event
      if (result.status === 'completed') {
        orcaEventEmitter.emitResponseCompleted({
          requestId,
          conversationId,
          timestamp: new Date().toISOString(),
          response: result,
        });
      } else if (result.status === 'partial') {
        const unavailableCount = Object.values(result.dataAvailability || {}).filter(
          (s) => s === 'unavailable'
        ).length;

        orcaEventEmitter.emitResponsePartial({
          requestId,
          conversationId,
          timestamp: new Date().toISOString(),
          response: result,
          dataUnavailableCount: unavailableCount,
        });
      }

      // 7. Persist to MongoDB (or memory fallback)
      await this.persistQueryRecord(requestId, conversationId, normalizedRequest, result, userId);

      return result;
    } catch (error) {
      logger.error({ requestId, err: error.message }, 'Failed processing query in agent core');

      orcaEventEmitter.emitResponseFailed({
        requestId,
        conversationId,
        timestamp: new Date().toISOString(),
        error: {
          code: error.code || 'AGENT_CORE_ERROR',
          message: error.message || 'Marine agent reasoning failed to execute',
        },
      });

      throw error;
    }
  }

  async persistQueryRecord(requestId, conversationId, request, response, userId) {
    const db = getDb();
    const doc = {
      requestId,
      conversationId,
      userId: userId || null,
      request,
      response,
      createdAt: new Date().toISOString(),
    };

    if (db) {
      try {
        await db.collection('queries').insertOne(doc);
        await db.collection('conversations').updateOne(
          { conversationId },
          {
            $set: {
              conversationId,
              userId: userId || null,
              lastQueryAt: doc.createdAt,
            },
            $push: { queryIds: requestId },
          },
          { upsert: true }
        );
      } catch (err) {
        logger.warn({ err, requestId }, 'Failed persisting query audit to MongoDB');
      }
    } else {
      inMemoryQueries.set(requestId, response);
    }
  }

  async getQueryById(requestId) {
    const db = getDb();
    if (db) {
      const record = await db.collection('queries').findOne({ requestId });
      if (record && record.response) {
        return record.response;
      }
    } else {
      const cached = inMemoryQueries.get(requestId);
      if (cached) return cached;
    }

    // Try FastAPI core
    const upstream = await fastApiClient.getRequestStatus(requestId);
    if (upstream) return upstream;

    throw new NotFoundError(`Query with requestId '${requestId}' not found`);
  }

  async getConversationHistory(conversationId) {
    const db = getDb();
    if (!db) {
      return Array.from(inMemoryQueries.values()).filter(
        (q) => q.conversationId === conversationId
      );
    }

    const records = await db
      .collection('queries')
      .find({ conversationId })
      .sort({ createdAt: 1 })
      .toArray();

    return records.map((r) => r.response);
  }
}

export const orcaService = new OrcaService();
