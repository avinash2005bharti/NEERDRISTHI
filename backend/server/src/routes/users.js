import { Router } from 'express';
import { userController } from '../controllers/userController.js';
import { authenticateJwt } from '../middleware/auth.js';

export const userRouter = Router();

// All user management routes require JWT authentication
userRouter.use(authenticateJwt);

userRouter.get('/profile', (req, res, next) => userController.getProfile(req, res, next));
userRouter.put('/profile', (req, res, next) => userController.updateProfile(req, res, next));

userRouter.get('/preferences', (req, res, next) => userController.getPreferences(req, res, next));
userRouter.put('/preferences', (req, res, next) => userController.updatePreferences(req, res, next));

// Support both /locations and /saved-locations for seamless frontend compatibility
userRouter.get('/saved-locations', (req, res, next) => userController.getSavedLocations(req, res, next));
userRouter.post('/saved-locations', (req, res, next) => userController.addSavedLocation(req, res, next));
userRouter.delete('/saved-locations/:locationId', (req, res, next) => userController.deleteSavedLocation(req, res, next));

userRouter.get('/locations', (req, res, next) => userController.getSavedLocations(req, res, next));
userRouter.post('/locations', (req, res, next) => userController.addSavedLocation(req, res, next));
userRouter.delete('/locations/:locationId', (req, res, next) => userController.deleteSavedLocation(req, res, next));
