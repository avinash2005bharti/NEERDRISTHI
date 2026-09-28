import { Router } from 'express';
import { authController } from '../controllers/authController.js';
import { authenticateJwt } from '../middleware/auth.js';

export const authRouter = Router();

authRouter.post('/register', (req, res, next) => authController.register(req, res, next));
authRouter.post('/login', (req, res, next) => authController.login(req, res, next));
authRouter.post('/logout', (req, res) => authController.logout(req, res));
authRouter.get('/me', authenticateJwt, (req, res, next) => authController.getMe(req, res, next));
