import { orcaService } from '../services/orcaService.js';
import { orcaQuerySchema } from '../validators/orcaSchemas.js';

export class OrcaController {
  async submitQuery(req, res, next) {
    try {
      const validated = orcaQuerySchema.parse(req.body);
      const userId = req.user?.userId;

      const result = await orcaService.processQuery(validated, userId);

      const response = {
        success: true,
        data: result,
        meta: {
          requestId: result.requestId,
          timestamp: new Date().toISOString(),
        },
      };

      res.status(200).json(response);
    } catch (err) {
      next(err);
    }
  }

  async getQueryStatus(req, res, next) {
    try {
      const { requestId } = req.params;
      const result = await orcaService.getQueryById(requestId);

      const response = {
        success: true,
        data: result,
        meta: {
          requestId,
          timestamp: new Date().toISOString(),
        },
      };

      res.status(200).json(response);
    } catch (err) {
      next(err);
    }
  }

  async getConversation(req, res, next) {
    try {
      const { conversationId } = req.params;
      const history = await orcaService.getConversationHistory(conversationId);

      const response = {
        success: true,
        data: history,
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
}

export const orcaController = new OrcaController();
