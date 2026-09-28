import { conversationService } from '../services/conversationService.js';

export class ConversationController {
  async listConversations(req, res, next) {
    try {
      const userId = req.user?.userId;
      const list = await conversationService.listConversations(userId);

      res.status(200).json({
        success: true,
        data: list,
      });
    } catch (err) {
      next(err);
    }
  }

  async createConversation(req, res, next) {
    try {
      const userId = req.user?.userId;
      const { title, initialLocation } = req.body;
      const conv = await conversationService.createConversation(userId, title, initialLocation);

      res.status(201).json({
        success: true,
        data: conv,
      });
    } catch (err) {
      next(err);
    }
  }

  async getConversation(req, res, next) {
    try {
      const { conversationId } = req.params;
      const conv = await conversationService.getConversation(conversationId);
      const messages = await conversationService.getMessages(conversationId);

      res.status(200).json({
        success: true,
        data: {
          ...conv,
          messages,
        },
      });
    } catch (err) {
      next(err);
    }
  }

  async deleteConversation(req, res, next) {
    try {
      const { conversationId } = req.params;
      const userId = req.user?.userId;
      await conversationService.deleteConversation(conversationId, userId);

      res.status(200).json({
        success: true,
        data: { deleted: true, conversationId },
      });
    } catch (err) {
      next(err);
    }
  }

  async getMessages(req, res, next) {
    try {
      const { conversationId } = req.params;
      const messages = await conversationService.getMessages(conversationId);

      res.status(200).json({
        success: true,
        data: messages,
      });
    } catch (err) {
      next(err);
    }
  }

  async postMessage(req, res, next) {
    try {
      const { conversationId } = req.params;
      const { message, text, userProfile, location } = req.body;
      const userId = req.user?.userId;

      const messageContent = message || text;
      if (!messageContent || !messageContent.trim()) {
        res.status(400).json({ success: false, error: { message: 'Message content is required' } });
        return;
      }

      const result = await conversationService.sendMessage(
        conversationId,
        messageContent.trim(),
        userId,
        userProfile,
        location
      );

      res.status(200).json({
        success: true,
        data: result,
      });
    } catch (err) {
      next(err);
    }
  }
}

export const conversationController = new ConversationController();
