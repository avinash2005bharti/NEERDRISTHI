import { Router } from 'express';
import { alertController } from '../controllers/alertController.js';

export const alertRouter = Router();

// GET /api/alerts (or /api/v1/alerts)
alertRouter.get('/', (req, res, next) => alertController.getAlerts(req, res, next));
alertRouter.post('/', (req, res, next) => alertController.createAlert(req, res, next));
alertRouter.post('/emergency', (req, res, next) => alertController.sendEmergencyAlert(req, res, next));
alertRouter.post('/sos', (req, res, next) => alertController.sendEmergencyAlert(req, res, next));

