import { Router } from 'express';
import { healthRouter } from './health.js';
import { authRouter } from './auth.js';
import { userRouter } from './users.js';
import { conversationRouter } from './conversations.js';
import { marineRouter } from './marine.js';
import { alertRouter } from './alerts.js';
import { sandboxRouter } from './sandbox.js';
import { orcaRouter } from './orca.js';

export const apiRouter = Router();

// Base health & diagnostic
apiRouter.use(healthRouter);

// Core Application Endpoints
apiRouter.use('/auth', authRouter);
apiRouter.use('/users', userRouter);
apiRouter.use('/profile', userRouter); // Friendly alias
apiRouter.use('/chats', conversationRouter);
apiRouter.use('/messages', conversationRouter);
apiRouter.use('/alerts', alertRouter);
apiRouter.use('/marine', marineRouter);
apiRouter.use('/sandbox', sandboxRouter);
apiRouter.use('/orca', orcaRouter);
