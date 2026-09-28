import pino from 'pino';

const isDev = process.env.NODE_ENV !== 'production';

let transport;
if (isDev) {
  try {
    transport = {
      target: 'pino-pretty',
      options: {
        colorize: true,
        translateTime: 'SYS:standard',
        ignore: 'pid,hostname',
      },
    };
  } catch {
    transport = undefined;
  }
}

export const logger = pino({
  level: process.env.LOG_LEVEL || (isDev ? 'debug' : 'info'),
  redact: {
    paths: [
      'req.headers.authorization',
      'req.headers.cookie',
      'req.headers["x-internal-service-secret"]',
      'password',
      'token',
      'accessToken',
      'refreshToken',
      'secret',
      'apiKey',
      'credentials',
      '*.password',
      '*.token',
      '*.apiKey',
      '*.secret',
    ],
    censor: '[REDACTED]',
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  transport,
});
