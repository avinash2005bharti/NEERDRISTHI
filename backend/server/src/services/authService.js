import bcrypt from 'bcryptjs';
import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../config/database.js';
import { env } from '../config/env.js';
import { signJwtToken } from '../utils/jwt.js';
import { BadRequestError, UnauthorizedError } from '../utils/errors.js';

// Fallback in-memory user map when MongoDB is not connected in local development
const inMemoryUsers = new Map();

export class AuthService {
  async register(input) {
    const db = getDb();
    const normalizedEmail = input.email.toLowerCase().trim();

    // Check if user already exists
    if (db) {
      const existing = await db.collection('users').findOne({ email: normalizedEmail });
      if (existing) {
        throw new BadRequestError('User with this email already exists');
      }
    } else {
      if (inMemoryUsers.has(normalizedEmail)) {
        throw new BadRequestError('User with this email already exists (in-memory store)');
      }
    }

    const salt = await bcrypt.genSalt(env.BCRYPT_SALT_ROUNDS);
    const passwordHash = await bcrypt.hash(input.password, salt);
    const userId = uuidv4();
    const now = new Date().toISOString();

    const userDoc = {
      id: userId,
      email: normalizedEmail,
      passwordHash,
      name: input.name.trim(),
      role: input.role || 'fisherman',
      vesselClass: input.vesselClass,
      preferredLanguage: input.preferredLanguage || 'en',
      createdAt: now,
      updatedAt: now,
    };

    if (db) {
      await db.collection('users').insertOne(userDoc);
    } else {
      inMemoryUsers.set(normalizedEmail, userDoc);
    }

    const authUser = {
      id: userDoc.id,
      email: userDoc.email,
      name: userDoc.name,
      role: userDoc.role,
      vesselClass: userDoc.vesselClass,
      preferredLanguage: userDoc.preferredLanguage,
      createdAt: userDoc.createdAt,
    };

    const token = signJwtToken({
      userId: userDoc.id,
      email: userDoc.email,
      role: userDoc.role,
      vesselClass: userDoc.vesselClass,
    });

    return {
      user: authUser,
      token,
      expiresIn: env.JWT_EXPIRES_IN,
    };
  }

  async login(input) {
    const db = getDb();
    const normalizedEmail = input.email.toLowerCase().trim();

    let userDoc = null;
    if (db) {
      userDoc = await db.collection('users').findOne({ email: normalizedEmail });
    } else {
      userDoc = inMemoryUsers.get(normalizedEmail) || null;
    }

    if (!userDoc) {
      throw new UnauthorizedError('Invalid email or password');
    }

    const isMatch = await bcrypt.compare(input.password, userDoc.passwordHash);
    if (!isMatch) {
      throw new UnauthorizedError('Invalid email or password');
    }

    const authUser = {
      id: userDoc.id,
      email: userDoc.email,
      name: userDoc.name,
      role: userDoc.role,
      vesselClass: userDoc.vesselClass,
      preferredLanguage: userDoc.preferredLanguage,
      createdAt: userDoc.createdAt,
    };

    const token = signJwtToken({
      userId: userDoc.id,
      email: userDoc.email,
      role: userDoc.role,
      vesselClass: userDoc.vesselClass,
    });

    return {
      user: authUser,
      token,
      expiresIn: env.JWT_EXPIRES_IN,
    };
  }

  async getMe(userId) {
    const db = getDb();
    let userDoc = null;
    if (db) {
      userDoc = await db.collection('users').findOne({ id: userId });
    } else {
      userDoc = Array.from(inMemoryUsers.values()).find((u) => u.id === userId) || null;
    }
    if (!userDoc) {
      throw new UnauthorizedError('User not found');
    }
    return {
      id: userDoc.id,
      email: userDoc.email,
      name: userDoc.name,
      role: userDoc.role,
      vesselClass: userDoc.vesselClass,
      preferredLanguage: userDoc.preferredLanguage,
      createdAt: userDoc.createdAt,
    };
  }
}

export const authService = new AuthService();
