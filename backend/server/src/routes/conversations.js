import { Router } from 'express';
import { conversationController } from '../controllers/conversationController.js';
import { optionalAuthenticateJwt } from '../middleware/auth.js';

export const conversationRouter = Router();

// Optional JWT: Guests can use basic chat, authenticated users get persisted history tied to their account
conversationRouter.use(optionalAuthenticateJwt);

// Chat listing and creation
conversationRouter.get('/', (req, res, next) => conversationController.listConversations(req, res, next));
conversationRouter.post('/', (req, res, next) => conversationController.createConversation(req, res, next));

// Specific conversation details, deletion, and message retrieval
conversationRouter.get('/:conversationId', (req, res, next) => conversationController.getConversation(req, res, next));
conversationRouter.delete('/:conversationId', (req, res, next) => conversationController.deleteConversation(req, res, next));

// Conversation messages
conversationRouter.get('/:conversationId/messages', (req, res, next) =>
  conversationController.getMessages(req, res, next)
);
conversationRouter.post('/:conversationId/messages', (req, res, next) =>
  conversationController.postMessage(req, res, next)
);
