import { MongoClient } from 'mongodb';
import { env } from './env.js';
import { logger } from '../utils/logger.js';

let client = null;
let db = null;

export async function connectMongo() {
  if (!env.MONGODB_URI) {
    logger.warn('MONGODB_URI is not configured. Running in unpersisted fallback mode.');
    return null;
  }

  try {
    client = new MongoClient(env.MONGODB_URI, {
      serverSelectionTimeoutMS: 5000,
    });
    await client.connect();
    db = client.db(env.MONGODB_DB_NAME);
    logger.info({ dbName: env.MONGODB_DB_NAME }, 'Connected to MongoDB successfully');

    await initializeIndexes(db);
    return db;
  } catch (error) {
    logger.error({ err: error }, 'Failed to connect to MongoDB. Server will continue without DB persistence.');
    return null;
  }
}

async function initializeIndexes(database) {
  try {
    // Users collection indexes
    await database.collection('users').createIndex({ email: 1 }, { unique: true });
    await database.collection('users').createIndex({ role: 1 });

    // Sessions & Conversations
    await database.collection('sessions').createIndex({ sessionId: 1 }, { unique: true });
    await database.collection('conversations').createIndex({ conversationId: 1 });
    await database.collection('conversations').createIndex({ userId: 1 });

    // Queries & Messages (STM)
    await database.collection('queries').createIndex({ requestId: 1 }, { unique: true });
    await database.collection('queries').createIndex({ conversationId: 1 });
    await database.collection('queries').createIndex({ createdAt: -1 });
    await database.collection('messages').createIndex({ conversationId: 1, createdAt: 1 });
    await database.collection('messages').createIndex({ messageId: 1 }, { unique: true });

    // Active Marine Alerts
    await database.collection('alerts').createIndex({ alertId: 1 }, { unique: true });
    await database.collection('alerts').createIndex({ severity: 1 });
    await database.collection('alerts').createIndex({ isActive: 1 });

    // Marine Advisories & Snapshots
    await database.collection('marine_advisories').createIndex({ 'source.provider': 1 });
    await database.collection('marine_advisories').createIndex({ valid_to: 1 });
    await database.collection('weather_snapshots').createIndex({ observed_at: -1 });
    await database.collection('tide_snapshots').createIndex({ observed_at: -1 });

    // 2dsphere Geospatial indexes
    await database.collection('pfz_zones').createIndex({ geometry: '2dsphere' });
    await database.collection('restricted_zones').createIndex({ geometry: '2dsphere' });

    // Risk assessments & agent traces
    await database.collection('risk_assessments').createIndex({ requestId: 1 });
    await database.collection('agent_traces').createIndex({ requestId: 1 });
    await database.collection('source_audit').createIndex({ requestId: 1 });

    logger.info('MongoDB indexes verified and ensured.');
  } catch (err) {
    logger.warn({ err }, 'Error initializing some MongoDB indexes. Existing indexes preserved.');
  }
}

export function getDb() {
  return db;
}

export async function closeMongo() {
  if (client) {
    await client.close();
    logger.info('MongoDB connection closed.');
  }
}
