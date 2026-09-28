import { Router } from 'express';
import { sandboxController } from '../controllers/sandboxController.js';
import { authenticateJwt } from '../middleware/auth.js';

export const sandboxRouter = Router();

// Sandbox execution requires authentication
sandboxRouter.post('/execute', authenticateJwt, (req, res, next) =>
  sandboxController.execute(req, res, next)
);
