import { Router } from 'express';
import { orcaController } from '../controllers/orcaController.js';
import { optionalAuthenticateJwt } from '../middleware/auth.js';

export const orcaRouter = Router();

orcaRouter.use(optionalAuthenticateJwt);

orcaRouter.post('/query', (req, res, next) => orcaController.submitQuery(req, res, next));
orcaRouter.get('/query/:requestId', (req, res, next) => orcaController.getQueryStatus(req, res, next));
orcaRouter.get('/conversations/:conversationId', (req, res, next) =>
  orcaController.getConversation(req, res, next)
);
