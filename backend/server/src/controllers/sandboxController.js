import { fastApiClient } from '../clients/fastApiClient.js';

export class SandboxController {
  async execute(req, res, next) {
    try {
      const { code, datasetCsv, contextData, timeoutSeconds } = req.body;
      if (!code || typeof code !== 'string') {
        res.status(400).json({ success: false, error: 'code string is required' });
        return;
      }

      const result = await fastApiClient.executeSandbox(
        code,
        datasetCsv,
        contextData,
        timeoutSeconds
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

export const sandboxController = new SandboxController();
