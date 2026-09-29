import { Router } from 'express';
import { healthController } from '../controllers/healthController.js';

export const healthRouter = Router();

// Gateway and composite health
healthRouter.get('/health', (req, res) => healthController.getHealth(req, res));
healthRouter.get('/ready', (req, res) => healthController.getReady(req, res));
healthRouter.get('/api/health', (req, res) => healthController.getHealth(req, res));

// Direct Python AI-Services health & wake-up endpoints
healthRouter.get('/health/ai', (req, res) => healthController.getAiHealth(req, res));
healthRouter.get('/health/ai/wakeup', (req, res) => healthController.wakeupAi(req, res));
healthRouter.post('/health/ai/wakeup', (req, res) => healthController.wakeupAi(req, res));
