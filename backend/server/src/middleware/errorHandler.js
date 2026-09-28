import { AppError } from '../utils/errors.js';
import { logger } from '../utils/logger.js';
import { ZodError } from 'zod';

export const errorHandler = (err, req, res, _next) => {
  const requestId = req.id || req.headers['x-request-id'] || 'unknown';

  // Handle Zod validation errors
  if (err instanceof ZodError) {
    const errorResponse = {
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed',
        details: err.flatten().fieldErrors,
      },
      meta: {
        requestId,
        timestamp: new Date().toISOString(),
      },
    };
    res.status(400).json(errorResponse);
    return;
  }

  // Handle known operational AppError
  if (err instanceof AppError) {
    const errorResponse = {
      success: false,
      error: {
        code: err.code,
        message: err.message,
        details: err.details,
      },
      meta: {
        requestId,
        timestamp: new Date().toISOString(),
      },
    };
    res.status(err.statusCode).json(errorResponse);
    return;
  }

  // Unexpected internal errors: log detailed trace internally, return safe message to client
  logger.error({ err, requestId, path: req.path }, 'Unhandled server error');

  const safeResponse = {
    success: false,
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected internal error occurred. Please contact system administrator.',
    },
    meta: {
      requestId,
      timestamp: new Date().toISOString(),
    },
  };
  res.status(500).json(safeResponse);
};
