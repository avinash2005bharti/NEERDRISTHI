import { Router } from 'express';
import { healthController } from '../controllers/healthController.js';

export const healthRouter = Router();

healthRouter.get('/health', (req, res) => healthController.getHealth(req, res));
