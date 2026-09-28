import { alertService } from '../services/alertService.js';

export class AlertController {
  async getAlerts(req, res, next) {
    try {
      const latitude = req.query.latitude ? parseFloat(req.query.latitude) : undefined;
      const longitude = req.query.longitude ? parseFloat(req.query.longitude) : undefined;
      const severity = req.query.severity;

      const alerts = await alertService.getActiveAlerts(latitude, longitude, severity);

      res.status(200).json({
        success: true,
        data: alerts,
        meta: {
          count: alerts.length,
          timestamp: new Date().toISOString(),
        },
      });
    } catch (err) {
      next(err);
    }
  }

  async createAlert(req, res, next) {
    try {
      const alert = await alertService.createAlert(req.body);
      res.status(201).json({
        success: true,
        data: alert,
      });
    } catch (err) {
      next(err);
    }
  }

  async sendEmergencyAlert(req, res, next) {
    try {
      const alert = await alertService.createEmergencyAlert(req.body);
      res.status(201).json({
        success: true,
        data: alert,
        message: '🚨 Emergency SOS distress beacon broadcasted to Indian Coast Guard & active maritime network.',
      });
    } catch (err) {
      next(err);
    }
  }
}

export const alertController = new AlertController();
