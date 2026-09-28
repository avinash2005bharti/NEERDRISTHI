import jwt from 'jsonwebtoken';
import { env } from '../config/env.js';

export function signJwtToken(payload) {
  const secret = env.JWT_SECRET || 'dev-insecure-jwt-secret-do-not-use-in-production';
  return jwt.sign(payload, secret, {
    expiresIn: env.JWT_EXPIRES_IN || '7d',
  });
}

export function verifyJwtToken(token) {
  const secret = env.JWT_SECRET || 'dev-insecure-jwt-secret-do-not-use-in-production';
  return jwt.verify(token, secret);
}
