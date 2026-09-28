import { authService } from '../services/authService.js';
import { registerSchema, loginSchema } from '../validators/authSchemas.js';

export class AuthController {
  async register(req, res, next) {
    try {
      const validated = registerSchema.parse(req.body);
      const result = await authService.register(validated);

      const response = {
        success: true,
        data: result,
        meta: {
          requestId: req.id || 'unknown',
          timestamp: new Date().toISOString(),
        },
      };

      res.status(201).json(response);
    } catch (err) {
      next(err);
    }
  }

  async login(req, res, next) {
    try {
      const validated = loginSchema.parse(req.body);
      const result = await authService.login(validated);

      const response = {
        success: true,
        data: result,
        meta: {
          requestId: req.id || 'unknown',
          timestamp: new Date().toISOString(),
        },
      };

      res.status(200).json(response);
    } catch (err) {
      next(err);
    }
  }

  async getMe(req, res, next) {
    try {
      if (!req.user?.userId) {
        res.status(401).json({ success: false, error: { message: 'Unauthorized' } });
        return;
      }
      const user = await authService.getMe(req.user.userId);
      res.status(200).json({
        success: true,
        data: user,
      });
    } catch (err) {
      next(err);
    }
  }

  async logout(req, res) {
    res.status(200).json({
      success: true,
      data: { message: 'Logged out successfully' },
    });
  }
}

export const authController = new AuthController();
