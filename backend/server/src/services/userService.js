import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../config/database.js';
import { NotFoundError } from '../utils/errors.js';

// In-memory fallback for user profiles when MongoDB is in fallback mode
const inMemoryUsers = new Map();

export class UserService {
  async getProfile(userId) {
    const db = getDb();
    if (db) {
      const user = await db.collection('users').findOne({ id: userId });
      if (user) return user;
    } else {
      const user = inMemoryUsers.get(userId);
      if (user) return user;
    }
    throw new NotFoundError(`User with id '${userId}' not found`);
  }

  async updateProfile(userId, updates) {
    const db = getDb();
    const now = new Date().toISOString();
    const updatePayload = {
      ...updates,
      updatedAt: now,
    };

    if (db) {
      const result = await db.collection('users').findOneAndUpdate(
        { id: userId },
        { $set: updatePayload },
        { returnDocument: 'after' }
      );
      if (result) return result;
    } else {
      const existing = inMemoryUsers.get(userId);
      if (existing) {
        const updated = { ...existing, ...updatePayload };
        inMemoryUsers.set(userId, updated);
        return updated;
      }
    }
    throw new NotFoundError(`User with id '${userId}' not found`);
  }

  async getPreferences(userId) {
    const profile = await this.getProfile(userId);
    return profile.preferences || {
      theme: 'dark',
      isHighGlare: false,
      alertSound: true,
      voiceLanguage: profile.preferredLanguage || 'en',
      defaultRadiusKm: 50,
    };
  }

  async updatePreferences(userId, prefs) {
    const existingPrefs = await this.getPreferences(userId);
    const merged = { ...existingPrefs, ...prefs };
    await this.updateProfile(userId, { preferences: merged });
    return merged;
  }

  async getSavedLocations(userId) {
    const profile = await this.getProfile(userId);
    return profile.savedLocations || [];
  }

  async addSavedLocation(userId, location) {
    const newLoc = {
      id: uuidv4(),
      ...location,
      createdAt: new Date().toISOString(),
    };

    const currentLocations = await this.getSavedLocations(userId);
    const updated = [...currentLocations, newLoc];
    await this.updateProfile(userId, { savedLocations: updated });
    return newLoc;
  }

  async deleteSavedLocation(userId, locationId) {
    const currentLocations = await this.getSavedLocations(userId);
    const filtered = currentLocations.filter((l) => l.id !== locationId);
    await this.updateProfile(userId, { savedLocations: filtered });
    return true;
  }
}

export const userService = new UserService();
