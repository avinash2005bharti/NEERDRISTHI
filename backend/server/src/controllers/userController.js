import { userService } from '../services/userService.js';
import { UnauthorizedError } from '../utils/errors.js';

export class UserController {
  getUserId(req) {
    if (!req.user?.userId) {
      throw new UnauthorizedError('Authentication required');
    }
    return req.user.userId;
  }

  async getProfile(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const user = await userService.getProfile(userId);

      const response = {
        success: true,
        data: {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
          vesselClass: user.vesselClass,
          homePort: user.homePort,
          registrationNumber: user.registrationNumber,
          preferredLanguage: user.preferredLanguage,
          preferences: user.preferences,
          savedLocations: user.savedLocations,
          createdAt: user.createdAt,
        },
        meta: {
          requestId: req.id || 'unknown',
          timestamp: new Date().toISOString(),
        },
      };
      res.status(200).json(response);
    } catch (err) {
      next(err);
    }
  }

  async updateProfile(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const updated = await userService.updateProfile(userId, req.body);

      const response = {
        success: true,
        data: {
          id: updated.id,
          email: updated.email,
          name: updated.name,
          role: updated.role,
          vesselClass: updated.vesselClass,
          preferredLanguage: updated.preferredLanguage,
          preferences: updated.preferences,
        },
        meta: {
          requestId: req.id || 'unknown',
          timestamp: new Date().toISOString(),
        },
      };
      res.status(200).json(response);
    } catch (err) {
      next(err);
    }
  }

  async getPreferences(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const prefs = await userService.getPreferences(userId);

      res.status(200).json({
        success: true,
        data: prefs,
      });
    } catch (err) {
      next(err);
    }
  }

  async updatePreferences(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const updated = await userService.updatePreferences(userId, req.body);

      res.status(200).json({
        success: true,
        data: updated,
      });
    } catch (err) {
      next(err);
    }
  }

  async getSavedLocations(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const locations = await userService.getSavedLocations(userId);

      res.status(200).json({
        success: true,
        data: locations,
      });
    } catch (err) {
      next(err);
    }
  }

  async addSavedLocation(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const newLoc = await userService.addSavedLocation(userId, req.body);

      res.status(201).json({
        success: true,
        data: newLoc,
      });
    } catch (err) {
      next(err);
    }
  }

  async deleteSavedLocation(req, res, next) {
    try {
      const userId = this.getUserId(req);
      const { locationId } = req.params;
      await userService.deleteSavedLocation(userId, locationId);

      res.status(200).json({
        success: true,
        data: { deleted: true, locationId },
      });
    } catch (err) {
      next(err);
    }
  }
}

export const userController = new UserController();
