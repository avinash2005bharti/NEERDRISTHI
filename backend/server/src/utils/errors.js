export class AppError extends Error {
  constructor(message, statusCode = 500, code = 'INTERNAL_ERROR', details = undefined) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class BadRequestError extends AppError {
  constructor(message = 'Invalid request data', details = undefined) {
    super(message, 400, 'BAD_REQUEST', details);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required', details = undefined) {
    super(message, 401, 'UNAUTHORIZED', details);
  }
}

export class ForbiddenError extends AppError {
  constructor(message = 'Access forbidden for this role', details = undefined) {
    super(message, 403, 'FORBIDDEN', details);
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Requested resource not found', details = undefined) {
    super(message, 404, 'NOT_FOUND', details);
  }
}

export class UpstreamServiceError extends AppError {
  constructor(message = 'Upstream agent service failure', details = undefined) {
    super(message, 502, 'UPSTREAM_SERVICE_ERROR', details);
  }
}

export class AiServiceUnavailableError extends AppError {
  constructor(
    message = 'The ORCA AI service is starting. Please retry shortly.',
    details = undefined
  ) {
    super(message, 503, 'AI_SERVICE_UNAVAILABLE', details);
  }
}

